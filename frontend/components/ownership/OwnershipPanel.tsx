"use client";

import { Info } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ORIGINS, ORIGIN_LABEL, contributions, type OwnershipBreakdown } from "@/lib/ownership";
import { useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";

export const ORIGIN_COLOR = {
  ai: "var(--own-ai)",
  engine: "var(--own-engine)",
  student_edit: "var(--own-edit)",
  student_insert: "var(--own-insert)",
} as const;

const pct = (x: number) => `${Math.round(x * 100)}%`;

/** Ownership Score with its honest breakdown, origin shares and the heatmap toggle (U2). */
export function OwnershipPanel({ b }: { b: OwnershipBreakdown }) {
  const heatmap = useWorkspace((s) => s.heatmap);
  const setHeatmap = useWorkspace((s) => s.setHeatmap);
  const pts = contributions(b);

  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <span className="tabular text-5xl leading-none" aria-label={`Ownership score ${b.score} out of 100`}>
            {b.score}
          </span>
          <span className="tabular ml-1 text-sm text-muted-foreground">/100</span>
        </div>
        <Popover>
          <PopoverTrigger className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground">
            <Info className="size-3.5" /> How it&apos;s calculated
          </PopoverTrigger>
          <PopoverContent className="w-80" align="end">
            <p className="font-medium">Ownership Score</p>
            <p className="tabular text-xs leading-relaxed">
              0.45 × your characters / all characters
              <br />+ 0.20 × decisions made / rewrites offered
              <br />+ 0.20 × understanding (walkthrough, quiz, teach-back)
              <br />+ 0.15 × generic spots filled / spots found
            </p>
            <p className="text-xs text-muted-foreground">
              Steps you haven&apos;t done count as 0. A part is left out only when its step ran and found nothing to offer, and the other
              weights are scaled up. Pasted text counts as AI. Deleting an answer you added removes it from the score.
            </p>
          </PopoverContent>
        </Popover>
      </div>
      <p className="mt-2 text-sm">
        You wrote <b>{pct(b.studentShare)}</b> of this text.
      </p>

      {/* origin shares */}
      <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-secondary" role="img" aria-label="Share of text by origin">
        {ORIGINS.map((o) =>
          b.total && b.counts[o] ? (
            <span key={o} className="h-full transition-[width] duration-500" style={{ width: `${(100 * b.counts[o]) / b.total}%`, background: ORIGIN_COLOR[o] }} />
          ) : null,
        )}
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        {ORIGINS.map((o) => (
          <li key={o} className="flex items-center gap-1.5">
            <span className="size-2.5 shrink-0 rounded-sm" style={{ background: ORIGIN_COLOR[o] }} aria-hidden />
            <span className="text-muted-foreground">{ORIGIN_LABEL[o]}</span>
            <span className="tabular ml-auto">{b.total ? pct(b.counts[o] / b.total) : "0%"}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        aria-pressed={heatmap}
        onClick={() => setHeatmap(!heatmap)}
        className={cn(
          "mt-3 w-full rounded-md border px-3 py-1.5 text-sm transition-colors",
          heatmap ? "border-[var(--own-insert)] bg-[var(--own-insert)]/15" : "border-rule hover:bg-secondary",
        )}
      >
        {heatmap ? "Hide" : "Show"} ownership heatmap
      </button>

      {/* breakdown */}
      <ul className="mt-4 space-y-3 border-t border-rule pt-3">
        {b.parts.map((p) => (
          <li key={p.key}>
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span>{p.label}</span>
              <span className="tabular text-xs text-muted-foreground">
                {p.value == null ? "n/a" : `${pct(p.value)} · +${(pts[p.key] ?? 0).toFixed(1)}`}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-foreground/70 transition-[width] duration-500"
                style={{ width: p.value == null ? 0 : `${p.value * 100}%` }}
              />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              weight {p.weight.toFixed(2)} · {p.detail}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
