/**
 * SM-2 spaced repetition (CLAUDE.md §9.6, U6).
 *
 * Grades 1-4 (keys 1-4) map to SM-2 quality: 1 Again → 1, 2 Hard → 3, 3 Good → 4, 4 Easy → 5.
 * A failed card (Again) is shown again in 10 minutes and its interval restarts; a passed card
 * gets 1 day, then 6 days, then interval × ease. Ease starts at 2.5, never below 1.3.
 */
export type Grade = 1 | 2 | 3 | 4;
export type CardSource = "glossary" | "quiz" | "viva" | "writing";

export interface Card {
  id: string;
  front: string;
  back: string;
  source: CardSource;
  docId: string;
  docTitle: string;
  created: number;
  ease: number;
  interval: number; // days
  reps: number; // successful reviews in a row
  lapses: number;
  due: number; // timestamp
  lastReviewed?: number;
}

export interface Review {
  at: number;
  cardId: string;
  grade: Grade;
}

export const DAY = 24 * 60 * 60 * 1000;
export const RELEARN_MS = 10 * 60 * 1000;
export const MIN_EASE = 1.3;
const QUALITY: Record<Grade, number> = { 1: 1, 2: 3, 3: 4, 4: 5 };
export const GRADE_LABEL: Record<Grade, string> = { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" };

export function newCard(fields: Omit<Card, "ease" | "interval" | "reps" | "lapses" | "due" | "created">, now = Date.now()): Card {
  return { ...fields, created: now, ease: 2.5, interval: 0, reps: 0, lapses: 0, due: now };
}

/** The card after a review at `now` with `grade`. */
export function review(card: Card, grade: Grade, now = Date.now()): Card {
  const q = QUALITY[grade];
  const ease = Math.max(MIN_EASE, card.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
  if (q < 3) {
    return { ...card, ease, reps: 0, interval: 0, lapses: card.lapses + 1, due: now + RELEARN_MS, lastReviewed: now };
  }
  const reps = card.reps + 1;
  const interval = reps === 1 ? 1 : reps === 2 ? 6 : Math.round(card.interval * ease);
  return { ...card, ease, reps, interval, due: now + interval * DAY, lastReviewed: now };
}

/** Human label of the next interval a grade would give ("10 min", "1 d", "2 mo"). */
export function nextIntervalLabel(card: Card, grade: Grade, now = Date.now()): string {
  const ms = review(card, grade, now).due - now;
  if (ms < DAY) return `${Math.round(ms / 60000)} min`;
  const days = Math.round(ms / DAY);
  if (days < 30) return `${days} d`;
  if (days < 365) return `${Math.round(days / 30)} mo`;
  return `${(days / 365).toFixed(1)} y`;
}

export function dueCards(cards: Card[], now = Date.now()): Card[] {
  return cards.filter((c) => c.due <= now).sort((a, b) => a.due - b.due);
}

/** Consecutive days (ending today or yesterday) with at least one review. */
export function streak(reviews: Review[], now = Date.now()): number {
  const days = new Set(reviews.map((r) => localDay(r.at)));
  let d = localDay(now);
  if (!days.has(d)) d -= 1; // today's review not done yet: the streak is still alive
  let n = 0;
  while (days.has(d)) {
    n += 1;
    d -= 1;
  }
  return n;
}

/** Day number of a timestamp in the user's time zone (consecutive days differ by 1). */
export function localDay(t: number): number {
  return Math.floor((t - new Date(t).getTimezoneOffset() * 60000) / DAY);
}
