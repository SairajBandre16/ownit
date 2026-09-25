"use client";

import type { Editor as TEditor, JSONContent } from "@tiptap/core";
import { useCallback, useMemo } from "react";
import { useWorkspace } from "@/lib/store";
import { Editor, type OffsetLayers } from "./Editor";

/** The workspace editor bound to the current document (content + ownership marks persist). */
export function DocEditor({
  layers,
  activeId,
  onHighlightClick,
  renderHover,
  editable = true,
}: {
  layers?: Record<string, OffsetLayers | undefined>;
  activeId?: string | null;
  onHighlightClick?: (id: string, kind: string) => void;
  renderHover?: (id: string, kind: string) => React.ReactNode | null;
  editable?: boolean;
}) {
  const doc = useWorkspace((s) => s.doc);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const setText = useWorkspace((s) => s.setText);
  const setEditor = useWorkspace((s) => s.setEditor);
  const heatmap = useWorkspace((s) => s.heatmap);
  // the editor owns its content after mount; only the initial JSON is passed in
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const initial = useMemo(() => doc?.content ?? { type: "doc", content: [] }, [doc?.id]);

  const onChange = useCallback(
    (text: string, json: JSONContent) => {
      setText(text);
      patchDoc({ content: json });
    },
    [patchDoc, setText],
  );
  const onReady = useCallback((e: TEditor) => setEditor(e), [setEditor]);

  if (!doc) return null;
  return (
    <div className="relative rounded-xl border border-rule bg-card">
      <div className="grid-paper pointer-events-none absolute inset-y-0 left-0 w-10 rounded-l-xl border-r border-rule opacity-80" aria-hidden />
      <Editor
        key={doc.id}
        content={initial}
        onChange={onChange}
        onReady={onReady}
        layers={layers}
        activeId={activeId}
        onHighlightClick={onHighlightClick}
        renderHover={renderHover}
        editable={editable}
        heatmap={heatmap}
        className="py-8 pr-6 pl-16 sm:pr-10"
      />
    </div>
  );
}
