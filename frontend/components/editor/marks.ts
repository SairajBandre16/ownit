/**
 * Custom TipTap extensions:
 *  - `origin` mark (ai | engine | student_edit | student_insert) for ownership tracking (U2)
 *  - `Highlights` plugin: decoration layers for issues, protected spans, engine changes and
 *    "make it yours" spots. Decorations map through edits until the next analysis.
 */
import { Extension, Mark, mergeAttributes } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Mapping } from "@tiptap/pm/transform";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { MarkType, Node as PMNode } from "@tiptap/pm/model";
import type { Origin } from "@/lib/types";

// ------------------------------------------------------------------ origin mark

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    origin: {
      setOrigin: (origin: Origin) => ReturnType;
    };
    highlights: {
      setHighlights: (input: HighlightInput) => ReturnType;
    };
  }
}

export const OriginMark = Mark.create({
  name: "origin",
  inclusive: true,
  addAttributes() {
    return {
      origin: {
        default: "ai",
        parseHTML: (el) => el.getAttribute("data-origin"),
        renderHTML: (attrs) => ({ "data-origin": attrs.origin }),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span[data-origin]" }];
  },
  renderHTML({ HTMLAttributes }) {
    return ["span", mergeAttributes(HTMLAttributes, { class: "mark-origin" }), 0];
  },
  addCommands() {
    return {
      setOrigin:
        (origin) =>
        ({ commands }) =>
          commands.setMark(this.name, { origin }),
    };
  },
});

/** Transaction meta key: set by programmatic edits that already carry the right origin. */
export const ORIGIN_META = "ownit-origin";

/** Origin of the character just before `pos` (same paragraph), if any. */
function originBefore(doc: PMNode, pos: number, markType: MarkType): Origin | null {
  const $pos = doc.resolve(pos);
  if ($pos.parentOffset === 0) return null;
  const node = $pos.nodeBefore;
  const m = node?.marks.find((mk) => mk.type === markType);
  return (m?.attrs.origin as Origin) ?? null;
}

/**
 * Decide the origin of text the student typed or pasted at [from, to) (§9.2):
 *  - continuing their own text keeps its origin;
 *  - typing inside a sentence of AI/engine text is a `student_edit`;
 *  - typing at a new position (empty paragraph, paragraph start, or after a finished
 *    sentence) is a `student_insert`.
 */
export function classifyInsertion(doc: PMNode, from: number, markType: MarkType): Origin {
  const $from = doc.resolve(from);
  const before = originBefore(doc, from, markType);
  if (before === "student_edit" || before === "student_insert") return before;
  const para = $from.parent;
  if (!para.textContent.trim() || $from.parentOffset === 0) return "student_insert";
  const textBefore = para.textBetween(0, $from.parentOffset);
  if (/[.!?]["”)]?\s*$/.test(textBefore)) return "student_insert";
  return "student_edit";
}

/**
 * Tags typed/pasted text with an origin. Programmatic edits (engine changes, "Make it yours"
 * insertions, document loads) set ORIGIN_META and are left alone.
 *
 * Pasted or dropped text (§9.2: "pasted text → ai") keeps the origin it already carries when
 * it was copied inside the editor; text from elsewhere is tagged `ai`, because the tool can't
 * know who wrote it (the score must never be inflated).
 */
export const OriginTracker = Extension.create({
  name: "originTracker",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("originTracker"),
        appendTransaction(trs, _oldState, state) {
          const markType = state.schema.marks.origin;
          if (!markType) return null;
          const ranges: [number, number, boolean][] = [];
          trs.forEach((t, j) => {
            if (!t.docChanged || t.getMeta(ORIGIN_META)) return;
            const ui = t.getMeta("uiEvent");
            const pasted = ui === "paste" || ui === "drop";
            // mapping from this transaction's doc to the final state's doc
            const after = new Mapping();
            for (let k = j + 1; k < trs.length; k++) after.appendMapping(trs[k].mapping);
            t.steps.forEach((step, i) => {
              const rest = new Mapping(t.mapping.maps.slice(i + 1));
              step.getMap().forEach((_os, _oe, ns, ne) => {
                if (ne <= ns) return;
                const from = after.map(rest.map(ns, -1), -1);
                const to = after.map(rest.map(ne, 1), 1);
                if (to > from) ranges.push([from, to, pasted]);
              });
            });
          });
          if (!ranges.length) return null;
          const tr = state.tr;
          for (const [from, to, pasted] of ranges) {
            if (pasted) {
              state.doc.nodesBetween(from, to, (node, pos) => {
                if (!node.isText || markType.isInSet(node.marks)) return;
                tr.addMark(Math.max(from, pos), Math.min(to, pos + node.nodeSize), markType.create({ origin: "ai" }));
              });
              continue;
            }
            // classify by what is immediately before the inserted text
            const origin = classifyInsertion(state.doc, from, markType);
            tr.removeMark(from, to, markType);
            tr.addMark(from, to, markType.create({ origin }));
          }
          tr.setMeta(ORIGIN_META, true);
          tr.setMeta("addToHistory", false);
          return tr;
        },
      }),
    ];
  },
});

// ------------------------------------------------------------------ highlight layers

export interface HighlightSpan {
  from: number; // ProseMirror positions
  to: number;
  id: string;
  kind: "issue" | "protected" | "change" | "spot" | "anchor" | "engineering" | "heading" | "focus";
  category?: string;
  label?: string;
  rule?: string;
}

/** Named, independent decoration layers ("analysis", "changes", "spots", "doctor", ...). */
export interface HighlightInput {
  layer: string;
  spans: HighlightSpan[];
}

type LayerState = Record<string, DecorationSet>;
type HighlightMeta = { set?: HighlightInput; remove?: { layer?: string; id: string }; clear?: string };

export const highlightsKey = new PluginKey<LayerState>("ownitHighlights");

const CLASS: Record<HighlightSpan["kind"], string> = {
  issue: "mark-issue",
  engineering: "mark-issue",
  protected: "mark-protected",
  change: "mark-change",
  spot: "spot-marker",
  heading: "mark-heading",
  focus: "mark-focus",
  // invisible: marks where a "Make it yours" answer goes, so the point maps through edits
  anchor: "spot-anchor",
};

function build(doc: PMNode, input: HighlightInput): DecorationSet {
  const decos: Decoration[] = [];
  const max = doc.content.size;
  for (const s of input.spans) {
    const from = Math.max(0, Math.min(s.from, max));
    const to = Math.max(from, Math.min(s.to, max));
    const attrs: Record<string, string> = {
      class: CLASS[s.kind],
      "data-hl-id": s.id,
      "data-hl-kind": s.kind,
      "data-category": s.kind === "engineering" ? "engineering" : (s.category ?? ""),
      ...(s.rule ? { "data-rule": s.rule } : {}),
      ...(s.kind === "protected" ? { title: `Protected: ${s.label ?? ""}` } : {}),
    };
    const spec = { id: s.id, kind: s.kind, layer: input.layer };
    if (to > from) {
      decos.push(Decoration.inline(from, to, attrs, spec));
    } else {
      // zero-width change (a pure deletion point): show a thin caret widget
      const render = () => {
        const span = document.createElement("span");
        Object.entries(attrs).forEach(([k, v]) => span.setAttribute(k, v));
        span.classList.add("mark-caret");
        span.textContent = "\u200b";
        return span;
      };
      decos.push(Decoration.widget(from, render, { ...spec, side: 1 }));
    }
  }
  return DecorationSet.create(doc, decos);
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    highlightLayers: {
      removeHighlight: (id: string, layer?: string) => ReturnType;
      clearHighlights: (layer: string) => ReturnType;
    };
  }
}

export const Highlights = Extension.create({
  name: "highlights",
  addCommands() {
    return {
      setHighlights:
        (input) =>
        ({ tr, dispatch }) => {
          if (dispatch) tr.setMeta(highlightsKey, { set: input } satisfies HighlightMeta);
          return true;
        },
      removeHighlight:
        (id, layer) =>
        ({ tr, dispatch }) => {
          if (dispatch) tr.setMeta(highlightsKey, { remove: { id, layer } } satisfies HighlightMeta);
          return true;
        },
      clearHighlights:
        (layer) =>
        ({ tr, dispatch }) => {
          if (dispatch) tr.setMeta(highlightsKey, { clear: layer } satisfies HighlightMeta);
          return true;
        },
    };
  },
  addProseMirrorPlugins() {
    return [
      new Plugin<LayerState>({
        key: highlightsKey,
        state: {
          init: () => ({}),
          apply(tr, layers) {
            const meta = tr.getMeta(highlightsKey) as HighlightMeta | undefined;
            let next: LayerState = {};
            for (const [name, set] of Object.entries(layers)) next[name] = set.map(tr.mapping, tr.doc);
            if (meta?.set) next = { ...next, [meta.set.layer]: build(tr.doc, meta.set) };
            if (meta?.clear) {
              const rest = { ...next };
              delete rest[meta.clear];
              next = rest;
            }
            if (meta?.remove) {
              const { id, layer } = meta.remove;
              for (const [name, set] of Object.entries(next)) {
                if (layer && name !== layer) continue;
                const found = set.find(undefined, undefined, (spec) => spec.id === id);
                if (found.length) next[name] = set.remove(found);
              }
            }
            return next;
          },
        },
        props: {
          decorations(state) {
            const layers = highlightsKey.getState(state) ?? {};
            const all = Object.values(layers).flatMap((set) => set.find());
            return DecorationSet.create(state.doc, all);
          },
        },
      }),
    ];
  },
});

/** Current (mapped) range of a decoration by id, if it still exists. */
export function findHighlight(state: import("@tiptap/pm/state").EditorState, id: string, layer?: string) {
  const layers = highlightsKey.getState(state) ?? {};
  for (const [name, set] of Object.entries(layers)) {
    if (layer && name !== layer) continue;
    const found = set.find(undefined, undefined, (spec) => spec.id === id);
    if (found.length) return { from: found[0].from, to: found[0].to };
  }
  return null;
}
