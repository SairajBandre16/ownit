"use client";

import type { JSONContent } from "@tiptap/core";
import { EditorContent, useEditor, type Editor as TEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect, useRef, useState } from "react";
import { docText, offsetMapper } from "@/lib/offsets";
import { cn } from "@/lib/utils";
import { Highlights, OriginMark, OriginTracker, type HighlightSpan } from "./marks";

/** A highlight in character offsets relative to `OffsetLayers.text`. */
export interface OffsetSpan {
  start: number;
  end: number;
  id: string;
  kind: HighlightSpan["kind"];
  category?: string;
  label?: string;
  rule?: string;
}

export interface OffsetLayers {
  /** the text the offsets refer to; ignored if it no longer matches the editor */
  text: string;
  spans: OffsetSpan[];
}

interface Props {
  content: JSONContent;
  onChange?: (text: string, json: JSONContent) => void;
  onReady?: (editor: TEditor) => void;
  /** named decoration layers; each is applied when its `text` matches the editor */
  layers?: Record<string, OffsetLayers | undefined>;
  activeId?: string | null;
  onHighlightClick?: (id: string, kind: string) => void;
  renderHover?: (id: string, kind: string) => React.ReactNode | null;
  editable?: boolean;
  heatmap?: boolean;
  className?: string;
  ariaLabel?: string;
}

export function Editor({
  content,
  onChange,
  onReady,
  layers,
  activeId,
  onHighlightClick,
  renderHover,
  editable = true,
  heatmap = false,
  className,
  ariaLabel = "Document editor",
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ id: string; kind: string; x: number; y: number } | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: false,
        bold: false,
        italic: false,
        strike: false,
        code: false,
        codeBlock: false,
        blockquote: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        listKeymap: false,
        horizontalRule: false,
        hardBreak: false,
        link: false,
        underline: false,
      }),
      OriginMark,
      OriginTracker,
      Highlights,
    ],
    content,
    editable,
    editorProps: {
      attributes: {
        "aria-label": ariaLabel,
        role: "textbox",
        "aria-multiline": "true",
        spellcheck: "false",
      },
    },
    onUpdate: ({ editor: e }) => {
      onChangeRef.current?.(docText(e.state.doc), e.getJSON());
    },
  });

  useEffect(() => {
    if (editor && onReady) onReady(editor);
  }, [editor, onReady]);

  useEffect(() => {
    editor?.setEditable(editable);
  }, [editor, editable]);

  // push each layer when it refers to the current text; otherwise existing decorations keep
  // mapping through edits until fresh offsets arrive
  useEffect(() => {
    if (!editor || !layers) return;
    const current = docText(editor.state.doc);
    const m = offsetMapper(current);
    for (const [name, layer] of Object.entries(layers)) {
      if (!layer) {
        editor.commands.clearHighlights(name);
        continue;
      }
      if (layer.text !== current) continue;
      const spans: HighlightSpan[] = layer.spans.map((sp) => ({
        from: m.toPos(sp.start),
        to: m.toPos(sp.end),
        id: sp.id,
        kind: sp.kind,
        category: sp.category,
        label: sp.label,
        rule: sp.rule,
      }));
      editor.commands.setHighlights({ layer: name, spans });
    }
  }, [editor, layers]);

  // hover cards for highlights
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || !renderHover) return;
    const over = (ev: MouseEvent) => {
      const target = (ev.target as HTMLElement).closest<HTMLElement>("[data-hl-id]");
      if (!target) return;
      if (hideTimer.current) clearTimeout(hideTimer.current);
      const rect = target.getBoundingClientRect();
      const host = el.getBoundingClientRect();
      setHover({
        id: target.dataset.hlId!,
        kind: target.dataset.hlKind ?? "",
        x: Math.min(rect.left - host.left, host.width - 320),
        y: rect.bottom - host.top + 6,
      });
    };
    const out = (ev: MouseEvent) => {
      const to = ev.relatedTarget as HTMLElement | null;
      if (to && (to.closest("[data-hover-card]") || to.closest("[data-hl-id]"))) return;
      hideTimer.current = setTimeout(() => setHover(null), 220);
    };
    const click = (ev: MouseEvent) => {
      const target = (ev.target as HTMLElement).closest<HTMLElement>("[data-hl-id]");
      if (target && onHighlightClick) onHighlightClick(target.dataset.hlId!, target.dataset.hlKind ?? "");
    };
    el.addEventListener("mouseover", over);
    el.addEventListener("mouseout", out);
    el.addEventListener("click", click);
    return () => {
      el.removeEventListener("mouseover", over);
      el.removeEventListener("mouseout", out);
      el.removeEventListener("click", click);
    };
  }, [renderHover, onHighlightClick]);

  const card = hover && renderHover ? renderHover(hover.id, hover.kind) : null;
  const activeCss = activeId
    ? `[data-hl-id="${CSS.escape(activeId)}"]{outline:2px solid var(--signal);outline-offset:1px;border-radius:2px}`
    : "";

  return (
    <div ref={wrapRef} className={cn("ownit-editor relative", heatmap && "heatmap-on", className)}>
      {activeCss && <style>{activeCss}</style>}
      <EditorContent editor={editor} />
      {card && hover && (
        <div
          data-hover-card
          role="tooltip"
          onMouseEnter={() => hideTimer.current && clearTimeout(hideTimer.current)}
          onMouseLeave={() => setHover(null)}
          className="absolute z-30 w-80 rounded-lg border border-rule bg-popover p-3 text-sm text-popover-foreground shadow-lg animate-in fade-in-0 zoom-in-95"
          style={{ left: Math.max(0, hover.x), top: hover.y }}
        >
          {card}
        </div>
      )}
    </div>
  );
}
