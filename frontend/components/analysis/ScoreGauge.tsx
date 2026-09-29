"use client";

import { animate, useMotionValue, useReducedMotion, useTransform, motion } from "framer-motion";
import { useEffect, useState } from "react";

interface Props {
  /** score to count up from (e.g. the "before" score) */
  from?: number | null;
  value: number | null;
  label?: string;
  size?: number;
  caption?: string;
}

const R = 52;
const ARC = Math.PI * R; // half circle

export function ScoreGauge({ from, value, label = "Writing score", size = 180, caption }: Props) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(from ?? value ?? 0);
  const [shown, setShown] = useState(Math.round(from ?? value ?? 0));
  const dash = useTransform(mv, (v) => `${(Math.max(0, Math.min(100, v)) / 100) * ARC} ${ARC}`);

  useEffect(() => {
    if (value == null) return;
    const start = from ?? mv.get();
    mv.set(start);
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration: 1.4, ease: [0.22, 1, 0.36, 1] });
    return () => controls.stop();
  }, [value, from, reduce, mv]);

  useEffect(() => mv.on("change", (v) => setShown(Math.round(v))), [mv]);

  const delta = from != null && value != null ? Math.round(value - from) : null;
  const tone = value == null ? "var(--muted-foreground)" : value >= 75 ? "var(--own-insert)" : value >= 55 ? "var(--hl-clarity)" : "var(--hl-grammar)";

  return (
    <figure className="flex flex-col items-center" aria-label={`${label}: ${value ?? "not scored"} out of 100`}>
      <svg width={size} height={size * 0.62} viewBox="0 0 128 76" role="img" aria-hidden>
        <path d="M12 68 A52 52 0 0 1 116 68" fill="none" stroke="var(--rule)" strokeWidth="10" strokeLinecap="round" />
        <motion.path
          d="M12 68 A52 52 0 0 1 116 68"
          fill="none"
          stroke={tone}
          strokeWidth="10"
          strokeLinecap="round"
          style={{ strokeDasharray: dash }}
        />
        {Array.from({ length: 11 }, (_, i) => {
          const a = Math.PI - (i / 10) * Math.PI;
          const x1 = 64 + Math.cos(a) * 40;
          const y1 = 68 - Math.sin(a) * 40;
          const x2 = 64 + Math.cos(a) * 36;
          const y2 = 68 - Math.sin(a) * 36;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--muted-foreground)" strokeWidth="0.8" opacity="0.5" />;
        })}
      </svg>
      <div className="-mt-12 flex items-baseline gap-1">
        <span className="tabular text-4xl font-medium" aria-live="polite">
          {value == null ? "-" : shown}
        </span>
        <span className="tabular text-sm text-muted-foreground">/100</span>
      </div>
      <figcaption className="mt-1 text-center text-xs text-muted-foreground">
        {label}
        {delta != null && delta !== 0 && (
          <span className={`tabular ml-2 ${delta > 0 ? "text-[var(--own-insert)]" : "text-destructive"}`}>
            {delta > 0 ? "+" : ""}
            {delta}
          </span>
        )}
        {caption && <span className="block">{caption}</span>}
      </figcaption>
    </figure>
  );
}
