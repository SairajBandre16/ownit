"use client";

import type { Change } from "@/lib/api";
import type { Decision } from "@/lib/types";

export function BulkActions({
  changes,
  decisions,
  stale,
  onBulk,
}: {
  changes: Change[];
  decisions: Record<string, Decision>;
  stale: Set<string>;
  onBulk: (ids: string[], d: Decision) => void;
}) {
  const pending = changes.filter((c) => !decisions[c.id] && !stale.has(c.id));
  const confident = pending.filter((c) => c.confidence >= 0.8);
  const accepted = changes.filter((c) => decisions[c.id] === "accepted").length;
  const rejected = changes.filter((c) => decisions[c.id] === "rejected").length;
  const btn = "rounded-md border border-rule px-2 py-1 text-xs hover:bg-secondary disabled:opacity-40";
  return (
    <div className="mb-3 space-y-2">
      <div className="tabular flex gap-3 text-xs text-muted-foreground">
        <span>{changes.length} offered</span>
        <span className="text-[var(--own-insert)]">{accepted} accepted</span>
        <span>{rejected} rejected</span>
        <span>{pending.length} to review</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <button type="button" className={btn} disabled={!pending.length} onClick={() => onBulk(pending.map((c) => c.id), "accepted")}>
          Accept all
        </button>
        <button type="button" className={btn} disabled={!confident.length} onClick={() => onBulk(confident.map((c) => c.id), "accepted")}>
          Accept confident ({confident.length})
        </button>
        <button type="button" className={btn} disabled={!pending.length} onClick={() => onBulk(pending.map((c) => c.id), "rejected")}>
          Reject all
        </button>
      </div>
    </div>
  );
}
