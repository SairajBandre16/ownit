"use client";

import { Trash2 } from "lucide-react";
import type { StyleProfile } from "@/lib/api";

function pct(x: number | undefined) {
  return `${Math.round((x ?? 0) * 100)}%`;
}

export function VoiceProfileSummary({
  profile,
  createdAt,
  onDelete,
}: {
  profile: StyleProfile;
  createdAt: number;
  onDelete: () => void;
}) {
  const f = profile.features;
  const favourites = Object.entries(f)
    .filter(([k]) => k.startsWith("trans:"))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([k]) => k.slice(6));
  const topFunction = Object.entries(profile.function_word_freqs)
    .filter(([w]) => !["the", "of", "and", "to", "a", "in"].includes(w))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([w]) => w);
  const rows: [string, string][] = [
    ["Average sentence", `${(f.sentence_length_mean ?? 0).toFixed(1)} words (± ${(f.sentence_length_sd ?? 0).toFixed(1)})`],
    ["Average word", `${(f.word_length_mean ?? 0).toFixed(2)} letters`],
    ["Commas", `${(f.commas_per_sentence ?? 0).toFixed(2)} per sentence`],
    ["Contractions", `${(f.contractions_per_sentence ?? 0).toFixed(2)} per sentence`],
    ["Passive voice", `${pct(f.passive_ratio)} of sentences`],
    ["“I / we”", `${Math.round(f.first_person_per_1000 ?? 0)} per 1,000 words`],
    ["Everyday words", `${pct(f.zipf_gt5)} of words`],
  ];
  return (
    <div className="rounded-xl border border-rule bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="tabular text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Your fingerprint</p>
          <p className="text-xs text-muted-foreground">
            From {profile.sample_word_count} words · {new Date(createdAt).toLocaleDateString()}
          </p>
        </div>
        <button type="button" onClick={onDelete} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive">
          <Trash2 className="size-3" /> Delete
        </button>
      </div>
      <dl className="mt-4 grid grid-cols-1 gap-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2 border-b border-dashed border-rule pb-1">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="tabular text-right">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 text-sm">
        <p className="text-muted-foreground">Linking words you use</p>
        <p className="tabular mt-1">{favourites.length ? favourites.join(" · ") : "you rarely start sentences with linking words"}</p>
        <p className="mt-3 text-muted-foreground">Function words you lean on</p>
        <p className="tabular mt-1">{topFunction.join(" · ")}</p>
      </div>
    </div>
  );
}
