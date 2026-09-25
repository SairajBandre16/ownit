"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { AnalyzeResponse } from "@/lib/api";

const ROWS: { key: keyof AnalyzeResponse["subscores"]; label: string; color: string; hint: string }[] = [
  { key: "clarity", label: "Clarity", color: "var(--hl-clarity)", hint: "Readability, long sentences, wordy phrases" },
  { key: "rhythm", label: "Rhythm", color: "var(--hl-rhythm)", hint: "Sentence-length variety and openers" },
  { key: "vocabulary", label: "Vocabulary", color: "var(--hl-vocabulary)", hint: "Diversity, repetition, stock phrases" },
  { key: "voice", label: "Voice", color: "var(--hl-voice)", hint: "Passive voice, hedges, fillers, weak verbs" },
  { key: "correctness", label: "Correctness", color: "var(--hl-grammar)", hint: "Grammar and spelling (LanguageTool)" },
];

const METRIC_LABELS: Record<string, string> = {
  grade_excess: "grade above target",
  long_sentence_pct: "% long sentences",
  nominalizations_per_100w: "nominalizations /100w",
  wordy_per_100w: "wordy phrases /100w",
  sentence_length_sd: "sentence length SD",
  opener_entropy: "opener variety",
  monotone_runs_per_10s: "monotone runs /10 sent.",
  mtld: "MTLD diversity",
  repeats_per_100w: "near repeats /100w",
  stock_per_100w: "stock phrases /100w",
  cliche_per_100w: "clichés /100w",
  passive_ratio: "passive ratio",
  hedges_per_100w: "hedges /100w",
  fillers_per_100w: "fillers /100w",
  weak_verbs_per_100w: "weak verbs /100w",
  lt_errors_per_100w: "errors /100w",
};

export function SubScoreBars({
  analysis,
  previous,
}: {
  analysis: AnalyzeResponse;
  previous?: AnalyzeResponse | null;
}) {
  const reduce = useReducedMotion();
  return (
    <ul className="space-y-3">
      {ROWS.map((r) => {
        const v = analysis.subscores[r.key];
        const prev = previous?.subscores[r.key];
        const details = analysis.details[r.key] ?? {};
        return (
          <li key={r.key}>
            <details className="group">
              <summary className="cursor-pointer list-none">
                <div className="flex items-baseline justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="size-2 rounded-full" style={{ background: r.color }} aria-hidden />
                    {r.label}
                  </span>
                  <span className="tabular text-xs">
                    {v == null ? (
                      <span className="text-muted-foreground">offline</span>
                    ) : (
                      <>
                        {prev != null && prev !== v && (
                          <span className="mr-1.5 text-muted-foreground line-through">{Math.round(prev)}</span>
                        )}
                        {Math.round(v)}
                      </>
                    )}
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-rule" role="progressbar" aria-valuenow={v ?? 0} aria-valuemin={0} aria-valuemax={100} aria-label={r.label}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: r.color }}
                    initial={{ width: `${prev ?? 0}%` }}
                    animate={{ width: `${v ?? 0}%` }}
                    transition={{ duration: reduce ? 0 : 0.8, ease: "easeOut" }}
                  />
                </div>
              </summary>
              <div className="mt-2 rounded-md bg-secondary/60 p-2 text-xs">
                <p className="mb-1 text-muted-foreground">{r.hint}</p>
                <table className="w-full">
                  <tbody>
                    {Object.entries(details).map(([k, d]) => (
                      <tr key={k}>
                        <td className="py-0.5 text-muted-foreground">{METRIC_LABELS[k] ?? k}</td>
                        <td className="tabular py-0.5 text-right">{d.value}</td>
                        <td className="tabular w-10 py-0.5 text-right">{Math.round(d.score)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </li>
        );
      })}
    </ul>
  );
}
