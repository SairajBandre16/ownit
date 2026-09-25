"use client";

import { Check, X } from "lucide-react";
import type { QuestionOut, ResultOut } from "@/lib/api";
import { cn } from "@/lib/utils";

const BLANK = "_____";
const TYPE_LABEL: Record<string, string> = {
  cloze: "Fill in the blank",
  mcq: "Multiple choice",
  tf: "True or false",
};

interface Props {
  q: QuestionOut;
  n: number;
  answer: string;
  result?: ResultOut | null;
  onAnswer: (a: string) => void;
}

/** One quiz question (cloze / MCQ / true-false) with its result once graded. */
export function QuestionCard({ q, n, answer, result, onAnswer }: Props) {
  const graded = result != null;
  const [before, after] = q.prompt.includes(BLANK) ? q.prompt.split(BLANK, 2) : [q.prompt, ""];
  const inputId = `ans-${q.id}`;

  return (
    <li
      className={cn(
        "rounded-xl border bg-card p-4 sm:p-5",
        graded ? (result.correct ? "border-[var(--own-insert)]/60" : "border-destructive/50") : "border-rule",
      )}
    >
      <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        <span className="tabular">Q{String(n).padStart(2, "0")}</span>
        <span aria-hidden>·</span>
        <span>{TYPE_LABEL[q.type] ?? q.type}</span>
        {graded && (
          <span className={cn("ml-auto inline-flex items-center gap-1 normal-case tracking-normal", result.correct ? "text-[var(--own-insert)]" : "text-destructive")}>
            {result.correct ? <Check className="size-4" /> : <X className="size-4" />}
            {result.correct ? "Correct" : "Not quite"}
          </span>
        )}
      </div>

      {q.type === "cloze" && (
        <p className="leading-relaxed">
          <label htmlFor={inputId} className="sr-only">
            Missing term
          </label>
          {before}
          <input
            id={inputId}
            value={answer}
            onChange={(e) => onAnswer(e.target.value)}
            disabled={graded}
            autoComplete="off"
            spellCheck={false}
            placeholder="term"
            className="mx-1 inline-block w-48 max-w-full rounded-md border border-input bg-background px-2 py-0.5 align-baseline text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-80"
          />
          {after}
        </p>
      )}

      {q.type === "mcq" && (
        <>
          <p className="leading-relaxed">
            {before}
            <span className="tabular mx-1 rounded bg-secondary px-2 text-muted-foreground">?</span>
            {after}
          </p>
          <div role="radiogroup" aria-label={`Answer to question ${n}`} className="mt-3 grid gap-2 sm:grid-cols-2">
            {(q.options ?? []).map((o) => {
              const chosen = answer === o;
              const isKey = graded && o === q.answer_key;
              return (
                <button
                  key={o}
                  type="button"
                  role="radio"
                  aria-checked={chosen}
                  disabled={graded}
                  onClick={() => onAnswer(o)}
                  className={cn(
                    "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                    chosen ? "border-foreground/70 bg-secondary" : "border-rule hover:bg-secondary/60",
                    isKey && "border-[var(--own-insert)] bg-[var(--own-insert)]/10",
                    graded && chosen && !isKey && "border-destructive/60 bg-destructive/5",
                  )}
                >
                  {o}
                </button>
              );
            })}
          </div>
        </>
      )}

      {q.type === "tf" && (
        <>
          <p className="leading-relaxed">“{q.prompt}”</p>
          <div role="radiogroup" aria-label={`Answer to question ${n}`} className="mt-3 flex gap-2">
            {(["true", "false"] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={answer === v}
                disabled={graded}
                onClick={() => onAnswer(v)}
                className={cn(
                  "min-w-24 rounded-md border px-4 py-1.5 text-sm capitalize transition-colors",
                  answer === v ? "border-foreground/70 bg-secondary" : "border-rule hover:bg-secondary/60",
                  graded && v === q.answer_key && "border-[var(--own-insert)] bg-[var(--own-insert)]/10",
                )}
              >
                {v}
              </button>
            ))}
          </div>
        </>
      )}

      {graded && !result.correct && <p className="mt-3 text-sm text-muted-foreground">{result.feedback}</p>}
      {graded && result.correct && q.type === "tf" && <p className="mt-3 text-sm text-muted-foreground">{result.feedback}</p>}
    </li>
  );
}
