"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { wordCount } from "@/lib/assess";
import { useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";

const MIN_WORDS = 40;

/** Teach-back: explain the whole document in your own words; graded by concept coverage. */
export function TeachbackPanel({ threshold }: { threshold: number }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const tb = doc.assess?.teachback;
  const [draft, setDraft] = useState(tb?.explanation ?? "");
  const words = wordCount(draft);

  const run = useMutation({
    mutationFn: (explanation: string) => api.teachback(text, explanation).then((r) => ({ r, explanation })),
    onSuccess: ({ r, explanation }) =>
      patchDoc((d) => ({
        assess: {
          ...d.assess,
          teachback: {
            explanation,
            coverage: r.coverage,
            covered: r.covered,
            missed: r.missed,
            similarity: r.similarity,
            score: r.score,
            feedback: r.feedback,
            copied: r.copied,
            missedSources: r.missed_sources.map((m) => ({ concept: m.concept, start: m.span.start, end: m.span.end })),
            text,
          },
        },
      })),
    onError: (e: Error) => toast.error(e.message),
  });

  const passed = tb != null && tb.coverage >= threshold;

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="teachback" className="font-display text-2xl">
          Explain it to a friend
        </label>
        <p className="mt-1 text-sm text-muted-foreground">
          Without looking at the text, explain what the work was about, how it was done, what was found and why it matters, as if to a classmate who
          hasn&apos;t read it. Use your own words: copying sentences doesn&apos;t count.
        </p>
      </div>
      <textarea
        id="teachback"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={9}
        className="w-full resize-y rounded-xl border border-input bg-card p-4 text-[15px] leading-relaxed focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        placeholder="In this project, I…"
      />
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => run.mutate(draft)}
          disabled={run.isPending || words < 5}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {run.isPending ? "Checking…" : tb ? "Check again" : "Check my explanation"}
        </button>
        <span className={cn("tabular text-xs", words < MIN_WORDS ? "text-muted-foreground" : "text-[var(--own-insert)]")}>
          {words} words{words < MIN_WORDS ? ` · aim for ${MIN_WORDS}+` : ""}
        </span>
      </div>

      {tb && (
        <section
          aria-label="Teach-back result"
          className={cn("rounded-xl border p-4", passed ? "border-[var(--own-insert)]/60" : "border-signal/50")}
        >
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="tabular text-3xl">{Math.round(tb.coverage)}%</span>
            <span className="text-sm">of the key ideas covered {passed ? `(passed, ${threshold}% needed)` : `(${threshold}% needed)`}</span>
            {tb.score != null && (
              <span className="tabular ml-auto text-xs text-muted-foreground">
                score {Math.round(tb.score)} · closeness {Math.round(tb.similarity * 100)}%
              </span>
            )}
          </div>
          {tb.feedback && <p className="mt-2 text-sm">{tb.feedback}</p>}
          {tb.copied && <p className="mt-1 text-sm text-destructive">Parts of this are copied from the text. Rewrite them in your own words.</p>}
          {tb.covered.length > 0 && (
            <div className="mt-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">You explained</p>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {tb.covered.map((c) => (
                  <li key={c} className="rounded-full bg-[var(--own-insert)]/15 px-2.5 py-0.5 text-sm">
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {tb.missed.length > 0 && (
            <div className="mt-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Not mentioned yet: reread these</p>
              <ul className="mt-1 space-y-1.5">
                {tb.missed.map((c) => {
                  const src = tb.missedSources?.find((m) => m.concept === c);
                  const sentence = src && tb.text ? tb.text.slice(src.start, src.end).trim() : null;
                  return (
                    <li key={c} className="text-sm">
                      <span className="rounded-full bg-signal/15 px-2.5 py-0.5">{c}</span>
                      {sentence && <span className="ml-2 text-muted-foreground">“{sentence}”</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
