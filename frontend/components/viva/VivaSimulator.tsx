"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, ArrowRight, Loader2, Maximize2, Timer } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ServerOfflineBanner } from "@/components/layout/ServerOfflineBanner";
import { api, type QuestionOut, type ResultOut } from "@/lib/api";
import { scoreBand, summarizeViva } from "@/lib/assess";
import { getDoc, saveDoc } from "@/lib/db";
import { jsonText } from "@/lib/offsets";
import { useSettings } from "@/lib/store";
import type { OwnDoc, VivaSession, VivaTurn } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CountdownRing } from "./CountdownRing";
import { LevelLadder } from "./LevelLadder";

const SECONDS = 60;
type Phase = "loading" | "intro" | "asking" | "question" | "grading" | "feedback" | "done" | "missing";

/** Full-screen "exam hall" viva practice (U3): adaptive questions, one at a time. */
export function VivaSimulator({ docId }: { docId: string }) {
  const reduce = useReducedMotion();
  const timed = useSettings((s) => s.vivaTimer);
  const setSettings = useSettings((s) => s.setSettings);
  const [doc, setDoc] = useState<OwnDoc | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [turns, setTurns] = useState<VivaTurn[]>([]);
  const [total, setTotal] = useState(10);
  const [q, setQ] = useState<QuestionOut | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<ResultOut | null>(null);
  const [remaining, setRemaining] = useState(SECONDS);
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef(0);
  const askedAt = useRef(0);
  const text = doc ? jsonText(doc.content) : "";

  useEffect(() => {
    getDoc(docId).then((d) => {
      if (!d) setPhase("missing");
      else {
        setDoc(d);
        setPhase("intro");
      }
    });
  }, [docId]);

  const persist = useCallback(
    async (next: VivaTurn[], finished: boolean) => {
      if (!doc) return;
      const latest = (await getDoc(doc.id)) ?? doc; // don't overwrite edits made elsewhere
      const session: VivaSession = { turns: next, startedAt: startedAt.current, timed, ...(finished ? { finishedAt: Date.now() } : {}) };
      const history = latest.assess?.vivaHistory ?? [];
      const summary = summarizeViva(next);
      const updated: OwnDoc = {
        ...latest,
        assess: {
          ...latest.assess,
          viva: session,
          vivaHistory: finished
            ? [...history, { finishedAt: Date.now(), average: Math.round(summary.average), questions: next.length }].slice(-20)
            : history,
        },
      };
      await saveDoc(updated);
      setDoc(updated);
    },
    [doc, timed],
  );

  const ask = useCallback(
    async (history: VivaTurn[]) => {
      setPhase("asking");
      setError(null);
      try {
        const r = await api.vivaNext(
          text,
          history.map((t) => ({ question: t.question, answer: t.answer, score: t.score, id: t.id ?? null, missed_concepts: t.missed_concepts })),
        );
        setTotal(r.total);
        if (r.done || !r.question) {
          setPhase("done");
          await persist(history, true);
          return;
        }
        setQ(r.question);
        setAnswer("");
        setResult(null);
        setRemaining(SECONDS);
        askedAt.current = Date.now();
        setPhase("question");
      } catch (e) {
        setError((e as Error).message);
        setPhase(history.length ? "feedback" : "intro");
      }
    },
    [text, persist],
  );

  const start = () => {
    startedAt.current = Date.now();
    setTurns([]);
    void ask([]);
  };

  const submit = useCallback(async () => {
    if (!q || phase !== "question") return;
    setPhase("grading");
    try {
      const g = await api.grade([q], [{ id: q.id, answer }], text);
      const r = g.results[0];
      setResult(r);
      const turn: VivaTurn = {
        id: q.id,
        question: q.prompt,
        difficulty: q.difficulty ?? "",
        level: q.level ?? 1,
        target_concepts: q.concepts,
        answer,
        score: r.score,
        feedback: r.feedback,
        missed_concepts: r.missed_concepts,
        covered_concepts: r.covered_concepts,
        model_answer: q.explanation,
        source_span: r.source_span,
        seconds: Math.round((Date.now() - askedAt.current) / 1000),
      };
      const next = [...turns, turn];
      setTurns(next);
      setPhase("feedback");
      await persist(next, false);
    } catch (e) {
      setError((e as Error).message);
      setPhase("question");
    }
  }, [q, phase, answer, text, turns, persist]);

  const next = useCallback(() => {
    if (turns.length >= total) {
      setPhase("done");
      void persist(turns, true);
    } else void ask(turns);
  }, [turns, total, ask, persist]);

  // countdown: at zero the current answer is submitted as it is
  const submitRef = useRef(submit);
  useEffect(() => {
    submitRef.current = submit;
  }, [submit]);
  useEffect(() => {
    if (phase !== "question" || !timed) return;
    let left = SECONDS;
    const t = setInterval(() => {
      left -= 1;
      setRemaining(Math.max(0, left));
      if (left <= 0) {
        clearInterval(t);
        void submitRef.current();
      }
    }, 1000);
    return () => clearInterval(t);
  }, [phase, timed]);

  // Enter moves on from feedback
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (phase === "feedback" && e.key === "Enter" && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        next();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, next]);

  const fade = reduce ? {} : { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -12 }, transition: { duration: 0.25 } };
  const summary = summarizeViva(turns);

  return (
    <div className="dark fixed inset-0 z-50 overflow-y-auto bg-background text-foreground">
      <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 py-6 sm:px-8">
        <header className="flex items-center gap-3 text-sm">
          <Link href={`/workspace/${docId}`} className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-4" /> Leave the exam hall
          </Link>
          <span className="ml-auto tabular text-muted-foreground">{phase !== "intro" && phase !== "loading" && `${Math.min(turns.length + (phase === "question" || phase === "asking" || phase === "grading" ? 1 : 0), total)} / ${total}`}</span>
          <button
            type="button"
            onClick={() => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.())}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            aria-label="Toggle full screen"
          >
            <Maximize2 className="size-4" />
          </button>
        </header>

        <main id="main" className="flex flex-1 flex-col justify-center py-10">
          <ServerOfflineBanner className="mb-6" />
          {error && (
            <p role="alert" className="mb-6 rounded-lg border border-destructive/60 bg-destructive/10 px-4 py-2 text-sm">
              {error}
            </p>
          )}
          <AnimatePresence mode="wait">
            {phase === "loading" && (
              <motion.p key="loading" {...fade} className="text-muted-foreground">
                Loading…
              </motion.p>
            )}
            {phase === "missing" && (
              <motion.p key="missing" {...fade}>
                Document not found in this browser.
              </motion.p>
            )}

            {phase === "intro" && doc && (
              <motion.section key="intro" {...fade} className="space-y-6">
                <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Viva Simulator · {doc.title}</p>
                <h1 className="font-display text-5xl leading-tight sm:text-6xl">The examiner will see you now.</h1>
                <p className="max-w-prose text-muted-foreground">
                  {total} questions about your own report. Answer in full sentences, as you would out loud. Good answers move you up the ladder; a
                  weak one takes you back to the definition you missed.
                </p>
                <LevelLadder level={1} />
                <label className="flex w-fit cursor-pointer items-center gap-2 text-sm">
                  <input type="checkbox" checked={timed} onChange={(e) => setSettings({ vivaTimer: e.target.checked })} className="size-4 accent-[var(--signal)]" />
                  <Timer className="size-4" /> {SECONDS}-second timer per question
                </label>
                <button type="button" onClick={start} className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 font-medium text-primary-foreground">
                  Begin <ArrowRight className="size-4" />
                </button>
              </motion.section>
            )}

            {phase === "asking" && (
              <motion.p key="asking" {...fade} className="inline-flex items-center gap-2 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> The examiner is choosing a question…
              </motion.p>
            )}

            {(phase === "question" || phase === "grading") && q && (
              <motion.section key={`q-${q.id}`} {...fade} className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <LevelLadder level={q.level ?? 1} />
                  {timed && <CountdownRing total={SECONDS} remaining={remaining} />}
                </div>
                <h2 className="font-display text-4xl leading-tight sm:text-5xl">{q.prompt}</h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submit();
                  }}
                  className="space-y-3"
                >
                  <textarea
                    autoFocus
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        void submit();
                      }
                    }}
                    disabled={phase === "grading"}
                    rows={6}
                    aria-label="Your answer"
                    placeholder="Answer as you would out loud…"
                    className="w-full resize-y rounded-xl border border-input bg-card p-4 text-lg leading-relaxed focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <button type="submit" disabled={phase === "grading"} className="rounded-md bg-primary px-5 py-2 font-medium text-primary-foreground disabled:opacity-60">
                      {phase === "grading" ? "Marking…" : "Submit answer"}
                    </button>
                    <span className="text-xs text-muted-foreground">Ctrl+Enter</span>
                    <button
                      type="button"
                      onClick={() => {
                        setAnswer("");
                        void submit();
                      }}
                      disabled={phase === "grading"}
                      className="ml-auto text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
                    >
                      I don&apos;t know
                    </button>
                  </div>
                </form>
              </motion.section>
            )}

            {phase === "feedback" && q && result && (
              <motion.section key={`f-${q.id}`} {...fade} className="space-y-6">
                <LevelLadder level={q.level ?? 1} />
                <p className="font-display text-2xl leading-snug text-muted-foreground">{q.prompt}</p>
                <div className="flex items-baseline gap-4">
                  <span className={cn("tabular text-6xl", scoreBand(result.score).tone === "good" ? "text-[var(--own-insert)]" : scoreBand(result.score).tone === "mid" ? "text-foreground" : "text-signal")}>
                    {Math.round(result.score)}
                  </span>
                  <span className="text-lg">{scoreBand(result.score).label}</span>
                </div>
                <p>{result.feedback}</p>
                {result.covered_concepts.length > 0 && (
                  <ul className="flex flex-wrap gap-1.5" aria-label="Ideas you covered">
                    {result.covered_concepts.map((c) => (
                      <li key={c} className="rounded-full bg-[var(--own-insert)]/20 px-2.5 py-0.5 text-sm">
                        {c}
                      </li>
                    ))}
                    {result.missed_concepts.map((c) => (
                      <li key={c} className="rounded-full border border-dashed border-signal/70 px-2.5 py-0.5 text-sm text-muted-foreground">
                        {c}
                      </li>
                    ))}
                  </ul>
                )}
                <blockquote className="border-l-2 border-signal/70 pl-4 text-muted-foreground">
                  <p className="mb-1 text-[11px] uppercase tracking-[0.16em]">From your report</p>
                  {q.explanation}
                </blockquote>
                <button type="button" onClick={next} className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 font-medium text-primary-foreground">
                  {turns.length >= total ? "See results" : "Next question"} <ArrowRight className="size-4" />
                </button>
                <span className="ml-3 text-xs text-muted-foreground">Enter</span>
              </motion.section>
            )}

            {phase === "done" && (
              <motion.section key="done" {...fade} className="space-y-6">
                <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Session complete</p>
                <p className="font-display text-5xl">
                  <span className="tabular">{Math.round(summary.average)}</span>
                  <span className="text-2xl text-muted-foreground"> average over {summary.answered} questions</span>
                </p>
                <ul className="grid gap-2 sm:grid-cols-4">
                  {summary.byLevel.map((l) => (
                    <li key={l.level} className="rounded-lg border border-rule p-3">
                      <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{l.name}</p>
                      <p className="tabular text-2xl">{l.average == null ? "-" : Math.round(l.average)}</p>
                      <p className="text-xs text-muted-foreground">{l.count} question{l.count === 1 ? "" : "s"}</p>
                    </li>
                  ))}
                </ul>
                {summary.weak.length > 0 && (
                  <div>
                    <p className="text-sm">Concepts to revise before the real viva:</p>
                    <ul className="mt-2 flex flex-wrap gap-1.5">
                      {summary.weak.slice(0, 10).map((w) => (
                        <li key={w.concept} className="rounded-full border border-dashed border-signal/70 px-2.5 py-0.5 text-sm">
                          {w.concept}
                          {w.missed > 1 && <span className="tabular ml-1 text-muted-foreground">×{w.missed}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={start} className="rounded-md bg-primary px-5 py-2 font-medium text-primary-foreground">
                    Practise again
                  </button>
                  <Link href={`/workspace/${docId}`} className="rounded-md border border-rule px-5 py-2">
                    Back to your document
                  </Link>
                  {summary.weak.length > 0 && (
                    <Link href="/deck" className="rounded-md border border-rule px-5 py-2">
                      Revise them in the Deck
                    </Link>
                  )}
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
