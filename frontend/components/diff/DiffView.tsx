"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Change } from "@/lib/api";
import type { Decision } from "@/lib/types";
import { BulkActions } from "./BulkActions";
import { ChangeCard } from "./ChangeCard";

function isTyping(el: EventTarget | null) {
  const node = el as HTMLElement | null;
  if (!node) return false;
  return node.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(node.tagName);
}

/**
 * Change cards with keyboard review: J / K move between cards, A accepts, R rejects.
 */
export function DiffView({
  changes,
  decisions,
  stale,
  activeId,
  onActivate,
  onDecide,
  onBulk,
}: {
  changes: Change[];
  decisions: Record<string, Decision>;
  stale: Set<string>;
  activeId: string | null;
  onActivate: (id: string | null) => void;
  onDecide: (id: string, d: Decision | null) => void;
  onBulk: (ids: string[], d: Decision) => void;
}) {
  const ordered = useMemo(() => [...changes].sort((a, b) => a.orig_start - b.orig_start), [changes]);
  const refs = useRef(new Map<string, HTMLDivElement>());

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      const key = e.key.toLowerCase();
      if (!["j", "k", "a", "r"].includes(key) || !ordered.length) return;
      e.preventDefault();
      const idx = Math.max(0, ordered.findIndex((c) => c.id === activeId));
      const pendingAfter = (from: number) => ordered.slice(from).find((c) => !decisions[c.id]) ?? ordered.find((c) => !decisions[c.id]);
      if (key === "j" || key === "k") {
        const next = key === "j" ? Math.min(ordered.length - 1, activeId ? idx + 1 : 0) : Math.max(0, idx - 1);
        onActivate(ordered[next].id);
        return;
      }
      const cur = ordered.find((c) => c.id === activeId) ?? pendingAfter(0);
      if (!cur || decisions[cur.id] || stale.has(cur.id) && key === "a") return;
      onDecide(cur.id, key === "a" ? "accepted" : "rejected");
      const nxt = pendingAfter(ordered.indexOf(cur) + 1);
      onActivate(nxt && nxt.id !== cur.id ? nxt.id : null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ordered, activeId, decisions, stale, onActivate, onDecide]);

  useEffect(() => {
    if (activeId) refs.current.get(activeId)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  if (!changes.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No rewrite passed the checks. Rule-based rewriting is conservative: sometimes the best option is to keep your sentence.
      </p>
    );
  }

  return (
    <div>
      <BulkActions changes={ordered} decisions={decisions} stale={stale} onBulk={onBulk} />
      <p className="mb-2 text-[11px] text-muted-foreground">
        <kbd className="tabular">J</kbd>/<kbd className="tabular">K</kbd> move · <kbd className="tabular">A</kbd> accept ·{" "}
        <kbd className="tabular">R</kbd> reject
      </p>
      <div className="max-h-[32rem] space-y-2 overflow-y-auto pr-1" role="list" aria-label="Suggested changes">
        {ordered.map((c, i) => (
          <div key={c.id} role="listitem">
            <ChangeCard
              ref={(el) => {
                if (el) refs.current.set(c.id, el);
                else refs.current.delete(c.id);
              }}
              change={c}
              index={i}
              decision={decisions[c.id]}
              stale={stale.has(c.id)}
              active={c.id === activeId}
              onFocus={() => onActivate(c.id)}
              onAccept={() => onDecide(c.id, "accepted")}
              onReject={() => onDecide(c.id, "rejected")}
              onUndo={() => onDecide(c.id, null)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
