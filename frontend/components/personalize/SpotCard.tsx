"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Check, CornerDownLeft, Undo2 } from "lucide-react";
import { forwardRef, useState } from "react";
import type { Spot } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  spot: Spot;
  index: number;
  active: boolean;
  filled?: string;
  skipped?: boolean;
  stale?: boolean;
  onInsert: (answer: string) => void;
  onSkip: (skip: boolean) => void;
  onFocus: () => void;
}

/** One generic spot: the prompt, an answer box, and Insert / Skip. */
export const SpotCard = forwardRef<HTMLDivElement, Props>(function SpotCard(
  { spot, index, active, filled, skipped, stale, onInsert, onSkip, onFocus },
  ref,
) {
  const reduce = useReducedMotion();
  const [answer, setAnswer] = useState(spot.starter);
  const done = filled != null;
  const canInsert = answer.trim().length > 0 && answer.trim() !== spot.starter.trim() && !stale;

  return (
    <motion.div
      ref={ref}
      initial={reduce ? false : { opacity: 0, x: 24 }}
      animate={{ opacity: done || skipped ? 0.65 : 1, x: 0 }}
      transition={{ duration: 0.25, delay: reduce ? 0 : Math.min(index, 8) * 0.03 }}
      onClick={onFocus}
      role="group"
      aria-label={`Spot ${index + 1}: ${spot.label}`}
      aria-current={active || undefined}
      className={cn(
        "rounded-lg border border-l-4 bg-background p-3 text-sm transition-colors",
        active ? "border-signal border-l-signal shadow-[0_0_0_1px_var(--signal)]" : "border-rule border-l-signal/60 hover:border-foreground/30",
        done && "border-l-[var(--own-insert)]",
      )}
    >
      <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span>{spot.label}</span>
        {done && (
          <span className="ml-auto inline-flex items-center gap-1 normal-case text-[var(--own-insert)]">
            <Check className="size-3.5" /> Added
          </span>
        )}
        {skipped && <span className="ml-auto normal-case">Skipped</span>}
      </div>
      <p className="line-clamp-2 italic text-muted-foreground">“{spot.quote}”</p>
      <p className="mt-1.5">{spot.prompt}</p>

      {done ? (
        <p className="mt-2 rounded-md bg-[var(--own-insert)]/10 px-2 py-1.5">{filled}</p>
      ) : skipped ? (
        <button type="button" onClick={() => onSkip(false)} className="mt-2 inline-flex items-center gap-1 text-xs underline">
          <Undo2 className="size-3" /> Answer it after all
        </button>
      ) : stale ? (
        <p className="mt-2 text-xs text-destructive">This text was changed, so the spot can&apos;t be found any more. Check again to refresh.</p>
      ) : (
        active && (
          <form
            className="mt-2 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (canInsert) onInsert(answer);
            }}
          >
            <textarea
              autoFocus
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  if (canInsert) onInsert(answer);
                }
              }}
              rows={3}
              aria-label="Your answer"
              className="w-full resize-y rounded-md border border-input bg-card px-2 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={!canInsert}
                className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                Insert <CornerDownLeft className="size-3.5" />
              </button>
              <button type="button" onClick={() => onSkip(true)} className="rounded-md border border-rule px-3 py-1 text-sm hover:bg-secondary">
                Skip
              </button>
              <span className="ml-auto text-[11px] text-muted-foreground">Ctrl+Enter</span>
            </div>
          </form>
        )
      )}
    </motion.div>
  );
});
