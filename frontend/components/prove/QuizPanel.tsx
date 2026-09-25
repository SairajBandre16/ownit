"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, RefreshCw, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { confusingParagraphs } from "@/lib/assess";
import { useWorkspace } from "@/lib/store";
import type { QuizResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { QuestionCard } from "./QuestionCard";

/** The quiz: cloze, multiple-choice and true/false questions from the student's own text. */
export function QuizPanel({ threshold }: { threshold: number }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const quiz = doc.assess?.quiz;
  const autoRan = useRef(false);

  const setQuiz = (q: QuizResult) => patchDoc((d) => ({ assess: { ...d.assess, quiz: q } }));

  const make = useMutation({
    mutationFn: (seed: number) =>
      api.generateQuestions(text, confusingParagraphs(doc), seed).then((r) => ({ r, seed })),
    onSuccess: ({ r, seed }) => {
      const questions = r.questions.filter((q) => q.type !== "viva");
      if (!questions.length) toast("This text is too short to make a quiz from.");
      setQuiz({ text, seed, questions, answers: {}, results: null, total: null });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const check = useMutation({
    mutationFn: (q: QuizResult) =>
      api.grade(
        q.questions,
        q.questions.map((x) => ({ id: x.id, answer: q.answers[x.id] ?? "" })),
        q.text,
      ),
    onSuccess: (g) => {
      const cur = useWorkspace.getState().doc?.assess?.quiz;
      if (cur) setQuiz({ ...cur, results: g.results, total: g.total });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  useEffect(() => {
    if (autoRan.current || quiz || !text.trim()) return;
    autoRan.current = true;
    make.mutate(0);
  }, [quiz, text, make]);

  if (!quiz) {
    return (
      <div className="space-y-3" aria-busy="true">
        <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Writing questions from your text…
        </p>
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl border border-rule bg-card" />
        ))}
      </div>
    );
  }

  const answered = quiz.questions.filter((q) => (quiz.answers[q.id] ?? "").trim()).length;
  const graded = quiz.results != null;
  const resultById = new Map((quiz.results ?? []).map((r) => [r.id, r]));
  const stale = quiz.text !== text;
  const passed = quiz.total != null && quiz.total >= threshold;

  return (
    <div className="space-y-4">
      {stale && (
        <p role="status" className="rounded-lg border border-signal/50 bg-signal/10 px-4 py-2 text-sm">
          Your text changed since this quiz was made. Make a new quiz to test the current version.
        </p>
      )}
      {graded && (
        <div
          className={cn(
            "flex flex-wrap items-center gap-3 rounded-xl border p-4",
            passed ? "border-[var(--own-insert)]/60 bg-[var(--own-insert)]/10" : "border-signal/50 bg-signal/10",
          )}
          role="status"
        >
          <span className="tabular text-3xl">{Math.round(quiz.total ?? 0)}%</span>
          <span className="text-sm">
            {passed
              ? `Quiz passed (${threshold}% needed).`
              : `${threshold}% needed to pass. Read the feedback, reread those paragraphs and try again.`}
          </span>
        </div>
      )}
      <ol className="space-y-3">
        {quiz.questions.map((q, i) => (
          <QuestionCard
            key={q.id}
            q={q}
            n={i + 1}
            answer={quiz.answers[q.id] ?? ""}
            result={resultById.get(q.id)}
            onAnswer={(a) =>
              patchDoc((d) =>
                d.assess?.quiz ? { assess: { ...d.assess, quiz: { ...d.assess.quiz, answers: { ...d.assess.quiz.answers, [q.id]: a } } } } : {},
              )
            }
          />
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-2">
        {!graded ? (
          <button
            type="button"
            onClick={() => check.mutate(quiz)}
            disabled={check.isPending || answered === 0}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {check.isPending ? "Checking…" : `Check answers (${answered}/${quiz.questions.length})`}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setQuiz({ ...quiz, answers: {}, results: null, total: null })}
            className="inline-flex items-center gap-1 rounded-md border border-rule px-4 py-2 text-sm hover:bg-secondary"
          >
            <RotateCcw className="size-4" /> Try again
          </button>
        )}
        <button
          type="button"
          onClick={() => make.mutate(quiz.seed + 1)}
          disabled={make.isPending}
          className="inline-flex items-center gap-1 rounded-md border border-rule px-4 py-2 text-sm hover:bg-secondary disabled:opacity-50"
        >
          <RefreshCw className={cn("size-4", make.isPending && "animate-spin")} /> New quiz
        </button>
        {confusingParagraphs(doc).length > 0 && (
          <span className="text-xs text-muted-foreground">Includes extra questions on the paragraphs you marked confusing.</span>
        )}
      </div>
    </div>
  );
}
