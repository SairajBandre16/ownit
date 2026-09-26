"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { listDocs } from "@/lib/db";
import { addReview, loadCards, loadReviews, saveCards, syncCards } from "@/lib/deck";
import { type Card, type CardSource, GRADE_LABEL, type Grade, type Review, dueCards, localDay, nextIntervalLabel, review, streak } from "@/lib/srs";
import { cn } from "@/lib/utils";

const SOURCE_LABEL: Record<CardSource, string> = { glossary: "Glossary", quiz: "Quiz", viva: "Viva", writing: "Your writing" };
const GRADES: Grade[] = [1, 2, 3, 4];

/** Daily review of the Revision Deck (SM-2) with keyboard shortcuts. */
export function DeckReview() {
  const reduce = useReducedMotion();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [revealed, setRevealed] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [filter, setFilter] = useState<CardSource | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    void Promise.all([loadCards(), loadReviews()]).then(([c, r]) => {
      setCards(c);
      setReviews(r);
    });
    const t = setInterval(() => setNow(Date.now()), 60_000); // "Again" cards come back
    return () => clearInterval(t);
  }, []);

  const due = useMemo(() => (cards ? dueCards(cards, now) : []), [cards, now]);
  const current = due[0] ?? null;

  const sync = useCallback(async () => {
    setSyncing(true);
    try {
      const { cards: next, added } = syncCards(cards ?? [], await listDocs());
      await saveCards(next);
      setCards(next);
      setNow(Date.now());
      toast(added ? `${added} new card${added === 1 ? "" : "s"} from your documents.` : "No new cards: the deck is up to date.");
    } finally {
      setSyncing(false);
    }
  }, [cards]);

  const grade = useCallback(
    async (g: Grade) => {
      if (!current || !cards) return;
      const t = Date.now();
      const updated = review(current, g, t);
      const next = cards.map((c) => (c.id === current.id ? updated : c));
      setCards(next);
      setRevealed(false);
      setNow(t);
      setReviews(await addReview({ at: t, cardId: current.id, grade: g }));
      await saveCards(next);
    },
    [current, cards],
  );

  const remove = async (id: string) => {
    if (!cards) return;
    const next = cards.filter((c) => c.id !== id);
    setCards(next);
    await saveCards(next);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current || e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (!revealed && (e.key === " " || e.key === "Enter")) {
        e.preventDefault();
        setRevealed(true);
      } else if (revealed && ["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        void grade(Number(e.key) as Grade);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, revealed, grade]);

  if (cards === null) return <p className="text-muted-foreground">Loading your deck…</p>;

  const today = localDay(now);
  const reviewedToday = reviews.filter((r) => localDay(r.at) === today).length;
  const nextDue = cards.length ? Math.min(...cards.map((c) => c.due)) : null;
  const shown = cards.filter((c) => !filter || c.source === filter).sort((a, b) => a.due - b.due);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        {[
          ["Due now", due.length],
          ["Reviewed today", reviewedToday],
          ["Day streak", streak(reviews, now)],
          ["Cards", cards.length],
        ].map(([label, n]) => (
          <div key={label as string}>
            <p className="tabular text-4xl leading-none">{n}</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
          </div>
        ))}
        <button
          type="button"
          onClick={() => void sync()}
          disabled={syncing}
          className="ml-auto inline-flex items-center gap-2 rounded-md border border-rule px-4 py-2 text-sm hover:bg-secondary disabled:opacity-50"
        >
          <RefreshCw className={cn("size-4", syncing && "animate-spin")} /> Update from my documents
        </button>
      </div>

      {cards.length === 0 ? (
        <section className="rounded-xl border border-dashed border-rule p-8 text-center">
          <h2 className="font-display text-3xl">Your deck is empty</h2>
          <p className="mx-auto mt-2 max-w-prose text-muted-foreground">
            Cards come from your own work: glossary terms from the walkthrough (your definitions first), quiz questions you missed, viva
            questions you found hard, and the writing issues you make most often.
          </p>
        </section>
      ) : current ? (
        <section aria-label="Review" className="mx-auto max-w-2xl">
          <AnimatePresence mode="wait">
            <motion.div
              key={current.id + current.reps + current.lapses}
              initial={reduce ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -12 }}
              transition={{ duration: 0.2 }}
              className="rounded-2xl border border-rule bg-card p-6 shadow-sm sm:p-8"
            >
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                {SOURCE_LABEL[current.source]} · {current.docTitle}
              </p>
              <p className="mt-4 whitespace-pre-line font-display text-3xl leading-snug">{current.front}</p>
              <div aria-live="polite">
                {revealed ? (
                  <p className="mt-6 whitespace-pre-line border-t border-rule pt-6 text-lg">{current.back}</p>
                ) : (
                  <button type="button" onClick={() => setRevealed(true)} className="mt-8 rounded-md bg-primary px-5 py-2 font-medium text-primary-foreground">
                    Show answer <span className="ml-1 text-xs opacity-70">Space</span>
                  </button>
                )}
              </div>
              {revealed && (
                <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" aria-label="How well did you remember?">
                  {GRADES.map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => void grade(g)}
                      className={cn(
                        "rounded-md border px-3 py-2 text-sm transition-colors hover:bg-secondary",
                        g === 1 ? "border-signal/60" : g === 3 ? "border-foreground/40" : "border-rule",
                      )}
                    >
                      <span className="tabular mr-1 text-xs text-muted-foreground">{g}</span> {GRADE_LABEL[g]}
                      <span className="tabular block text-xs text-muted-foreground">{nextIntervalLabel(current, g, now)}</span>
                    </button>
                  ))}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
          <p className="mt-3 text-center text-xs text-muted-foreground">Keys: Space to show the answer, 1–4 to grade.</p>
        </section>
      ) : (
        <section className="rounded-xl border border-rule bg-card p-8 text-center">
          <h2 className="font-display text-3xl">All caught up</h2>
          <p className="mt-2 text-muted-foreground">
            {nextDue ? `Next card due ${new Date(nextDue).toLocaleString(undefined, { weekday: "long", hour: "2-digit", minute: "2-digit" })}.` : ""} Short daily
            reviews beat one long night before the viva.
          </p>
        </section>
      )}

      {cards.length > 0 && (
        <section aria-labelledby="all-cards">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h2 id="all-cards" className="mr-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              All cards
            </h2>
            {([null, "glossary", "quiz", "viva", "writing"] as const).map((s) => (
              <button
                key={s ?? "all"}
                type="button"
                aria-pressed={filter === s}
                onClick={() => setFilter(s)}
                className={cn("rounded-full border px-2.5 py-0.5 text-xs", filter === s ? "border-foreground" : "border-rule text-muted-foreground")}
              >
                {s ? SOURCE_LABEL[s] : "All"} {s ? cards.filter((c) => c.source === s).length : cards.length}
              </button>
            ))}
          </div>
          <ul className="divide-y divide-rule rounded-xl border border-rule bg-card">
            {shown.map((c) => (
              <li key={c.id} className="flex items-start gap-3 px-4 py-2.5 text-sm">
                <span className="line-clamp-2 flex-1">{c.front}</span>
                <span className="tabular shrink-0 text-xs text-muted-foreground">{c.due <= now ? "due" : new Date(c.due).toLocaleDateString()}</span>
                <button type="button" onClick={() => void remove(c.id)} aria-label={`Delete card: ${c.front.slice(0, 40)}`} className="text-muted-foreground hover:text-destructive">
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
