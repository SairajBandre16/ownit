"use client";

import { useState } from "react";

const SAMPLE =
  "In order to measure the torque, it is important to note that we utilized a strain gauge. Additionally, the sensor has the ability to record data at 1 kHz.";

const CHANGES = [
  { from: "In order to", to: "To", reason: "“in order to” says the same as “to” in fewer words." },
  { from: "it is important to note that ", to: "", reason: "A stock phrase that adds no information; the sentence is stronger without it." },
  { from: "utilized", to: "used", reason: "“utilized” → “used”: a more common word with the same meaning." },
  { from: "has the ability to", to: "can", reason: "“has the ability to” → “can”: shorter, same meaning." },
];

function applyChanges(n: number) {
  let t = SAMPLE;
  for (const c of CHANGES.slice(0, n)) t = t.replace(c.from, c.to);
  return t;
}

export function LiveDemo() {
  const [step, setStep] = useState(0);
  const text = applyChanges(step);
  return (
    <div className="relative self-center rounded-xl border border-rule bg-card p-5 shadow-[0_1px_0_var(--rule),0_20px_40px_-24px_rgba(0,0,0,0.25)]">
      <div className="mb-3 flex items-center justify-between">
        <span className="tabular text-xs uppercase tracking-widest text-muted-foreground">Mini demo</span>
        <span className="tabular text-xs text-muted-foreground">
          {step}/{CHANGES.length} changes
        </span>
      </div>
      <p className="min-h-[6.5rem] text-[1.05rem] leading-relaxed" aria-live="polite">
        {text}
      </p>
      <div className="mt-4 min-h-[5.5rem]">
        {step > 0 && (
            <div
              key={step}
              className="rounded-lg border border-rule border-l-4 border-l-[var(--own-engine)] bg-background p-3 text-sm animate-in fade-in-0 slide-in-from-right-6 duration-300"
            >
              <div className="tabular mb-1 text-xs text-muted-foreground">
                “{CHANGES[step - 1].from.trim()}” → “{CHANGES[step - 1].to || "∅"}”
              </div>
              {CHANGES[step - 1].reason}
            </div>
          )}
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => setStep((s) => Math.min(CHANGES.length, s + 1))}
          disabled={step === CHANGES.length}
          className="h-9 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          Next change
        </button>
        <button
          type="button"
          onClick={() => setStep(0)}
          className="h-9 rounded-md border border-rule px-4 text-sm"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
