"use client";

import { Check, X } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { forwardRef } from "react";
import { CATEGORY_COLORS } from "@/components/analysis/IssueList";
import type { Change } from "@/lib/api";
import { displayPair } from "@/lib/changes";
import type { Decision } from "@/lib/types";
import { cn } from "@/lib/utils";

const TRANSFORM_LABEL: Record<string, string> = {
  phrase_simplify: "Simplify phrase",
  synonym: "Plainer word",
  transition_vary: "Vary transition",
  split_long: "Split long sentence",
  merge_short: "Merge short sentences",
  passive_to_active: "Active voice",
  clause_front: "Reorder clause",
  opener_vary: "Vary opener",
  contractions: "Contraction",
  voice_fit: "Your voice",
};

interface Props {
  change: Change;
  decision?: Decision;
  active: boolean;
  stale?: boolean;
  index: number;
  onAccept: () => void;
  onReject: () => void;
  onUndo?: () => void;
  onFocus: () => void;
}

export const ChangeCard = forwardRef<HTMLDivElement, Props>(function ChangeCard(
  { change, decision, active, stale, index, onAccept, onReject, onUndo, onFocus },
  ref,
) {
  const reduce = useReducedMotion();
  const { from, to } = displayPair(change);
  return (
    <motion.div
      ref={ref}
      layout={!reduce}
      initial={reduce ? false : { opacity: 0, x: 28 }}
      animate={{ opacity: decision ? 0.6 : 1, x: 0 }}
      transition={{ duration: 0.28, delay: reduce ? 0 : Math.min(index, 8) * 0.03 }}
      onClick={onFocus}
      role="group"
      aria-label={`Change ${index + 1}: ${from || "insertion"} to ${to || "deleted"}`}
      aria-current={active || undefined}
      className={cn(
        "cursor-pointer rounded-lg border bg-background p-3 text-sm transition-colors",
        active ? "border-signal shadow-[0_0_0_1px_var(--signal)]" : "border-rule hover:border-foreground/30",
      )}
      style={{ borderLeftWidth: 4, borderLeftColor: CATEGORY_COLORS[change.category] ?? "var(--own-engine)" }}
    >
      <div className="mb-1.5 flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span>{TRANSFORM_LABEL[change.transform] ?? change.transform}</span>
        <span className="tabular ml-auto normal-case" title="Confidence">
          {Math.round(change.confidence * 100)}%
        </span>
      </div>
      <p className="tabular text-[13px] leading-snug">
        {from && <del className="rounded bg-destructive/10 px-0.5 text-destructive decoration-destructive/60">{from}</del>}
        {from && to && <span className="mx-1 text-muted-foreground">→</span>}
        {to ? (
          <ins className="rounded bg-[var(--own-edit)]/15 px-0.5 no-underline">{to}</ins>
        ) : (
          <span className="ml-1 text-xs text-muted-foreground">(removed)</span>
        )}
      </p>
      <p className="mt-1.5 text-muted-foreground">{change.reason}</p>
      {stale && <p className="mt-1 text-xs text-destructive">This text was edited, so the change can no longer be applied.</p>}
      <div className="mt-2 flex items-center gap-2">
        {decision ? (
          <>
            <span className={cn("text-xs font-medium", decision === "accepted" ? "text-[var(--own-insert)]" : "text-muted-foreground")}>
              {decision === "accepted" ? "Accepted" : "Rejected"}
            </span>
            {onUndo && decision === "rejected" && (
              <button type="button" onClick={(e) => { e.stopPropagation(); onUndo(); }} className="text-xs underline">
                Undo
              </button>
            )}
          </>
        ) : (
          <>
            <button
              type="button"
              disabled={stale}
              onClick={(e) => {
                e.stopPropagation();
                onAccept();
              }}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground disabled:opacity-40"
              aria-keyshortcuts="A"
            >
              <Check className="size-3.5" /> Accept <kbd className="tabular ml-1 opacity-60">A</kbd>
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onReject();
              }}
              className="inline-flex items-center gap-1 rounded-md border border-rule px-2.5 py-1 text-xs hover:bg-secondary"
              aria-keyshortcuts="R"
            >
              <X className="size-3.5" /> Reject <kbd className="tabular ml-1 opacity-60">R</kbd>
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
});
