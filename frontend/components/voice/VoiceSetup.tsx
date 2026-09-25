"use client";

import { useMutation } from "@tanstack/react-query";
import { Fingerprint, Loader2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useStyleProfile } from "@/hooks/useStyleProfile";
import { api, type CompareResponse } from "@/lib/api";
import { countWords } from "@/lib/docs";
import { VoiceMatchMeter } from "./VoiceMatchMeter";
import { VoiceProfileSummary } from "./VoiceProfileSummary";

const MIN_WORDS = 300;

export function VoiceSetup() {
  const { stored, loading, save } = useStyleProfile();
  const [samples, setSamples] = useState<string[]>([""]);
  const [probe, setProbe] = useState("");
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const total = samples.reduce((n, s) => n + countWords(s), 0);

  const build = useMutation({
    mutationFn: () => api.fingerprint(samples.filter((s) => s.trim())),
    onSuccess: async (profile) => {
      await save({ profile, samples, createdAt: Date.now() });
      toast.success("Voice Fingerprint saved on this device.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const compare = useMutation({
    mutationFn: () => api.compareStyle(probe, stored!.profile),
    onSuccess: setComparison,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr]">
      <section>
        <p className="tabular text-xs uppercase tracking-[0.2em] text-muted-foreground">U1 · Write like me</p>
        <h1 className="font-display text-5xl">Voice Fingerprint</h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Paste one to three pieces of writing that are genuinely <em>yours</em> — an old assignment, a lab write-up, a
          long message. OwnIt measures how you write (sentence length, punctuation, favourite linking words, how often
          you say “I/we”, the 60 most common function words…) and the rewriter then moves drafts towards your voice
          instead of a generic one.
        </p>

        <div className="mt-6 space-y-4">
          {samples.map((s, i) => (
            <div key={i}>
              <div className="mb-1 flex items-center justify-between">
                <label htmlFor={`sample-${i}`} className="text-sm font-medium">
                  Sample {i + 1}
                </label>
                {samples.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setSamples(samples.filter((_, j) => j !== i))}
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="size-3" /> Remove
                  </button>
                )}
              </div>
              <textarea
                id={`sample-${i}`}
                value={s}
                onChange={(e) => setSamples(samples.map((x, j) => (j === i ? e.target.value : x)))}
                rows={7}
                placeholder="Paste something you wrote yourself…"
                className="grid-paper w-full rounded-lg border border-input bg-background p-3 text-sm leading-relaxed"
              />
              <p className="tabular mt-1 text-right text-[11px] text-muted-foreground">{countWords(s)} words</p>
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-3">
            {samples.length < 3 && (
              <button type="button" onClick={() => setSamples([...samples, ""])} className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary">
                <Plus className="size-4" /> Add sample
              </button>
            )}
            <span className={`tabular text-sm ${total >= MIN_WORDS ? "text-[var(--own-insert)]" : "text-muted-foreground"}`}>
              {total} / {MIN_WORDS}+ words
            </span>
            <button
              type="button"
              onClick={() => build.mutate()}
              disabled={total < MIN_WORDS || build.isPending}
              className="ml-auto inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 font-medium text-primary-foreground disabled:opacity-50"
            >
              {build.isPending ? <Loader2 className="size-4 animate-spin" /> : <Fingerprint className="size-4" />}
              {stored ? "Rebuild fingerprint" : "Build my fingerprint"}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Only the measurements are kept (in this browser). The samples are sent to the server once to be measured and
            are not stored there.
          </p>
        </div>
      </section>

      <section className="space-y-6">
        {loading ? null : stored ? (
          <>
            <VoiceProfileSummary profile={stored.profile} createdAt={stored.createdAt} onDelete={() => save(null)} />
            <div className="rounded-xl border border-rule bg-card p-5">
              <h2 className="font-display text-2xl">Try it: how close is a text to your voice?</h2>
              <textarea
                value={probe}
                onChange={(e) => setProbe(e.target.value)}
                rows={6}
                aria-label="Text to compare"
                placeholder="Paste any paragraph (for example an AI draft)…"
                className="mt-3 w-full rounded-lg border border-input bg-background p-3 text-sm"
              />
              <button
                type="button"
                onClick={() => compare.mutate()}
                disabled={!probe.trim() || compare.isPending}
                className="mt-2 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary disabled:opacity-50"
              >
                {compare.isPending ? "Comparing…" : "Compare with my voice"}
              </button>
              {comparison && (
                <div className="mt-4">
                  <VoiceMatchMeter value={comparison.voice_match} words={countWords(probe)} />
                  <ul className="mt-3 space-y-1.5 text-sm">
                    {comparison.differences.map((d) => (
                      <li key={d.feature} className="flex gap-2">
                        <span className="text-signal-ink">→</span>
                        {d.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="grid-paper flex h-full min-h-72 flex-col items-center justify-center rounded-xl border border-dashed border-rule p-8 text-center">
            <Fingerprint className="size-10 text-muted-foreground" />
            <p className="mt-3 font-display text-2xl">No fingerprint yet</p>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">Once built, “Write like me” appears in the Humanize step and each draft shows a Voice Match %.</p>
          </div>
        )}
      </section>
    </div>
  );
}
