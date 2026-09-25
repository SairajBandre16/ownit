import type { Editor } from "@tiptap/core";
import { ORIGIN_META, findHighlight } from "@/components/editor/marks";
import type { Origin } from "./types";

/**
 * Replace [from, to) with `text`, tagging the new text with `origin`.
 * When text is deleted at a sentence start, the next word is capitalised.
 */
export function replaceRange(editor: Editor, from: number, to: number, text: string, origin: Origin): boolean {
  const { state } = editor;
  const markType = state.schema.marks.origin;
  const tr = state.tr;
  const before = state.doc.textBetween(Math.max(0, from - 3), from, "\n", "\n");
  const atSentenceStart = from <= 1 || /(^|[.!?]\s|\n)\s*$/.test(before) || state.doc.resolve(from).parentOffset === 0;
  let insert = text;
  if (!insert && to < state.doc.content.size) {
    // deleting a phrase: drop one adjacent space so we don't leave "a  b"
    const after = state.doc.textBetween(to, Math.min(to + 1, state.doc.content.size));
    const prev = state.doc.textBetween(Math.max(0, from - 1), from);
    if (after === " " && (prev === " " || atSentenceStart)) to += 1;
    else if (after === "," && atSentenceStart) to += 1;
    if (atSentenceStart) {
      const next = state.doc.textBetween(to, Math.min(to + 1, state.doc.content.size));
      if (next && next !== next.toUpperCase()) {
        tr.insertText(next.toUpperCase(), to, to + 1);
      }
    }
  } else if (atSentenceStart && insert) {
    insert = insert[0].toUpperCase() + insert.slice(1);
  }
  if (insert) {
    tr.insertText(insert, from, to);
    if (markType) {
      tr.removeMark(from, from + insert.length, markType);
      tr.addMark(from, from + insert.length, markType.create({ origin }));
    }
  } else {
    tr.delete(from, to);
  }
  tr.setMeta(ORIGIN_META, true);
  editor.view.dispatch(tr);
  return true;
}

/** Replace the text under a highlight decoration (by id). Returns false if it's gone. */
export function replaceHighlight(editor: Editor, id: string, text: string, origin: Origin): boolean {
  const range = findHighlight(editor.state, id);
  if (!range) return false;
  return replaceRange(editor, range.from, range.to, text, origin);
}

/** Insert text at a position with an origin (e.g. "Make it yours" answers). */
export function insertAt(editor: Editor, pos: number, text: string, origin: Origin) {
  const tr = editor.state.tr.insertText(text, pos);
  const markType = editor.state.schema.marks.origin;
  if (markType) tr.addMark(pos, pos + text.length, markType.create({ origin }));
  tr.setMeta(ORIGIN_META, true);
  editor.view.dispatch(tr);
}

export function scrollToHighlight(editor: Editor, id: string) {
  const range = findHighlight(editor.state, id);
  if (!range) return;
  const dom = editor.view.domAtPos(range.from);
  const el = (dom.node.nodeType === 1 ? dom.node : dom.node.parentElement) as HTMLElement | null;
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
}
