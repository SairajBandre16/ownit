"use client";

import { Loader2, Sparkles, X } from "lucide-react";
import { useState } from "react";
import type { DocSettings, Tone } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONES: { id: Tone; label: string; hint: string }[] = [
  { id: "academic", label: "Academic", hint: "Formal: no contractions, measured transitions" },
  { id: "neutral", label: "Neutral", hint: "Plain and direct" },
  { id: "casual", label: "Casual", hint: "Relaxed: contractions allowed" },
];

const INTENSITY_HINT = [
  "",
  "Gentle: only wordy phrases and repeated transitions",
  "Light: adds plainer word choices",
  "Balanced: also splits long sentences",
  "Strong: also restructures sentences (active voice, clause order)",
  "Maximum: every transform, smallest acceptable gain",
];

export function HumanizeControls({
  settings,
  onChange,
  onRun,
  running,
  hasProfile,
}: {
  settings: DocSettings;
  onChange: (p: Partial<DocSettings>) => void;
  onRun: () => void;
  running: boolean;
  hasProfile: boolean;
}) {
  const [term, setTerm] = useState("");
  const addTerm = () => {
    const t = term.trim();
    if (t && !settings.keepTerms.includes(t)) onChange({ keepTerms: [...settings.keepTerms, t] });
    setTerm("");
  };
  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="mb-1.5 text-xs font-medium">Tone</legend>
        <div className="grid grid-cols-3 gap-1 rounded-lg bg-secondary p-1" role="radiogroup" aria-label="Tone">
          {TONES.map((t) => (
            <button
              key={t.id}
              type="button"
              role="radio"
              aria-checked={settings.tone === t.id}
              title={t.hint}
              onClick={() => onChange({ tone: t.id })}
              className={cn(
                "rounded-md px-2 py-1 text-xs transition-colors",
                settings.tone === t.id ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="intensity" className="mb-1.5 flex items-baseline justify-between text-xs font-medium">
          Intensity <span className="tabular text-muted-foreground">{settings.intensity}/5</span>
        </label>
        <input
          id="intensity"
          type="range"
          min={1}
          max={5}
          step={1}
          value={settings.intensity}
          onChange={(e) => onChange({ intensity: Number(e.target.value) })}
          className="w-full accent-[var(--signal)]"
          aria-describedby="intensity-hint"
        />
        <p id="intensity-hint" className="mt-1 text-[11px] text-muted-foreground">
          {INTENSITY_HINT[settings.intensity]}
        </p>
      </div>

      <div>
        <label htmlFor="keep-term" className="mb-1.5 block text-xs font-medium">
          Keep these words unchanged
        </label>
        <div className="flex gap-1">
          <input
            id="keep-term"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTerm())}
            placeholder="e.g. heat sink"
            className="h-8 min-w-0 flex-1 rounded-md border border-input bg-background px-2 text-sm"
          />
          <button type="button" onClick={addTerm} className="rounded-md border border-rule px-2 text-xs hover:bg-secondary">
            Add
          </button>
        </div>
        {settings.keepTerms.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1">
            {settings.keepTerms.map((t) => (
              <li key={t} className="tabular inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs">
                {t}
                <button
                  type="button"
                  aria-label={`Remove ${t}`}
                  onClick={() => onChange({ keepTerms: settings.keepTerms.filter((x) => x !== t) })}
                >
                  <X className="size-3" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={settings.useVoice && hasProfile}
          disabled={!hasProfile}
          onChange={(e) => onChange({ useVoice: e.target.checked })}
          className="accent-[var(--signal)]"
        />
        Write like me (Voice Fingerprint)
        {!hasProfile && (
          <a href="/voice" className="text-signal-ink underline">
            set up
          </a>
        )}
      </label>

      <button
        type="button"
        onClick={onRun}
        disabled={running}
        className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary font-medium text-primary-foreground disabled:opacity-60"
      >
        {running ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
        {running ? "Rewriting…" : "Suggest rewrites"}
      </button>
    </div>
  );
}
