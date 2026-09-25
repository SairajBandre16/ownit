"use client";

import { cn } from "@/lib/utils";

/** Circular countdown; turns signal orange in the last 10 seconds. */
export function CountdownRing({ total, remaining, size = 72 }: { total: number; remaining: number; size?: number }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const frac = Math.max(0, Math.min(1, remaining / total));
  const low = remaining <= 10;
  return (
    <div className="relative" style={{ width: size, height: size }} role="timer" aria-label={`${remaining} seconds left`}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--rule)" strokeWidth={4} opacity={0.35} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={low ? "var(--signal)" : "currentColor"}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - frac)}
          className="transition-[stroke-dashoffset] duration-1000 ease-linear"
        />
      </svg>
      <span className={cn("tabular absolute inset-0 flex items-center justify-center text-lg", low && "text-signal")}>{remaining}</span>
    </div>
  );
}
