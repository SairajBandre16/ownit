"use client";

import { motion, useReducedMotion } from "framer-motion";

export function VoiceMatchMeter({ value, before, words }: { value: number; before?: number | null; words?: number }) {
  const reduce = useReducedMotion();
  const v = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">Voice Match</span>
        <span className="tabular text-2xl">
          {before != null && Math.round(before) !== Math.round(v) && (
            <span className="mr-2 text-base text-muted-foreground line-through">{Math.round(before)}%</span>
          )}
          {Math.round(v)}%
        </span>
      </div>
      <div className="relative mt-2 h-2 overflow-hidden rounded-full bg-rule" role="meter" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100} aria-label="Voice Match">
        {before != null && <div className="absolute inset-y-0 left-0 bg-muted-foreground/30" style={{ width: `${before}%` }} />}
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-[var(--hl-voice)]"
          initial={{ width: `${before ?? 0}%` }}
          animate={{ width: `${v}%` }}
          transition={{ duration: reduce ? 0 : 0.9, ease: "easeOut" }}
        />
      </div>
      {words != null && words < 200 && (
        <p className="mt-1 text-[11px] text-muted-foreground">Short texts give rough estimates ({words} words).</p>
      )}
    </div>
  );
}
