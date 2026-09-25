"use client";

import { Check, Lock, Unlock } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import type { GateStatus } from "@/lib/gate";
import { useSettings } from "@/lib/store";
import { cn } from "@/lib/utils";

/** The understanding gate (§9.7): what export needs and where the student stands. */
export function GatePanel({ gate }: { gate: GateStatus }) {
  const setSettings = useSettings((s) => s.setSettings);
  const rows = [
    { label: "Walkthrough reviewed", value: Math.round(gate.walkthroughPct * 100), need: gate.thresholds.walkthrough, ok: gate.walkthroughOk },
    { label: "Quiz", value: gate.quizScore == null ? null : Math.round(gate.quizScore), need: gate.thresholds.quiz, ok: gate.quizOk },
    {
      label: "Teach-back coverage",
      value: gate.teachbackCoverage == null ? null : Math.round(gate.teachbackCoverage),
      need: gate.thresholds.teachback,
      ok: gate.teachbackOk,
    },
  ];
  return (
    <div>
      <p className={cn("flex items-center gap-2 text-sm font-medium", gate.passed ? "text-[var(--own-insert)]" : "text-foreground")}>
        {gate.passed ? <Unlock className="size-4" /> : <Lock className="size-4" />}
        {gate.passed ? (gate.enabled ? "Export unlocked" : "Gate switched off: export is open") : "Export unlocks when all three are met"}
      </p>
      <ul className="mt-3 space-y-2.5">
        {rows.map((r) => (
          <li key={r.label}>
            <div className="flex items-baseline justify-between text-sm">
              <span className="inline-flex items-center gap-1.5">
                {r.ok ? <Check className="size-3.5 text-[var(--own-insert)]" aria-label="met" /> : <span className="size-3.5" aria-hidden />}
                {r.label}
              </span>
              <span className="tabular text-xs text-muted-foreground">
                {r.value == null ? "not done" : `${r.value}%`} / {r.need}%
              </span>
            </div>
            <div className="relative mt-1 h-1.5 overflow-hidden rounded-full bg-secondary">
              <div
                className={cn("h-full rounded-full transition-[width] duration-500", r.ok ? "bg-[var(--own-insert)]" : "bg-foreground/60")}
                style={{ width: `${Math.min(100, r.value ?? 0)}%` }}
              />
              <span className="absolute inset-y-0 w-px bg-foreground/70" style={{ left: `${r.need}%` }} aria-hidden />
            </div>
          </li>
        ))}
      </ul>
      <label className="mt-4 flex items-center justify-between gap-3 border-t border-rule pt-3 text-xs text-muted-foreground">
        <span>Require these checks before export</span>
        <Switch checked={gate.enabled} onCheckedChange={(v) => setSettings({ gateEnabled: v })} aria-label="Understanding gate" />
      </label>
    </div>
  );
}
