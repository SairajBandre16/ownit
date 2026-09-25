"use client";

import { Check, Lock } from "lucide-react";
import { STEPS, type StepId } from "@/lib/types";
import { cn } from "@/lib/utils";

export function Stepper({
  current,
  done,
  locked,
  onSelect,
}: {
  current: StepId;
  done: Partial<Record<StepId, boolean>>;
  locked?: Partial<Record<StepId, string>>;
  onSelect: (s: StepId) => void;
}) {
  return (
    <nav aria-label="Steps">
      <ol className="flex gap-1 overflow-x-auto lg:flex-col lg:gap-0">
        {STEPS.map((s, i) => {
          const active = s.id === current;
          const isDone = done[s.id];
          const lock = locked?.[s.id];
          return (
            <li key={s.id} className="relative shrink-0 lg:shrink">
              {i < STEPS.length - 1 && (
                <span className="absolute top-9 left-[1.15rem] hidden h-[calc(100%-1.5rem)] w-px bg-rule lg:block" aria-hidden />
              )}
              <button
                type="button"
                onClick={() => onSelect(s.id)}
                aria-current={active ? "step" : undefined}
                title={lock}
                className={cn(
                  "flex w-full items-start gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-secondary",
                  active && "bg-secondary",
                )}
              >
                <span
                  className={cn(
                    "tabular relative z-10 mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border text-xs",
                    active ? "border-signal bg-signal text-[#1a1a1a]" : isDone ? "border-foreground bg-foreground text-background" : "border-rule bg-background text-muted-foreground",
                  )}
                >
                  {isDone && !active ? <Check className="size-3.5" /> : lock ? <Lock className="size-3" /> : s.n}
                </span>
                <span className="hidden min-w-0 lg:block">
                  <span className={cn("block text-sm font-medium", !active && "text-muted-foreground")}>{s.label}</span>
                  <span className="block text-xs text-muted-foreground">{s.short}</span>
                </span>
                <span className="text-sm lg:hidden">{s.label}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
