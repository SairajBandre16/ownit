/**
 * The Revision Deck (CLAUDE.md §9.6, U6): flashcards made from the student's own work.
 *
 * Sources: glossary terms (the student's own definition first), quiz questions they got wrong,
 * viva questions they scored under 70 on, and their most frequent writing issues (an example
 * from their own text with the fix). Cards live in IndexedDB; syncing adds new cards and never
 * resets the schedule of cards already in the deck.
 */
import { getMeta, setMeta } from "./db";
import { glossary } from "./report";
import { type Card, type Review, newCard } from "./srs";
import type { OwnDoc } from "./types";

const CARDS_KEY = "deck.cards";
const REVIEWS_KEY = "deck.reviews";
const VIVA_PASS = 70;
const MAX_WRITING_CARDS = 5;
const MAX_REVIEWS_KEPT = 5000;

/** Small stable hash for card ids (FNV-1a). */
export function hash(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36);
}

const ruleLabel = (rule: string) => rule.replace(/^lt:/, "").replace(/[._]/g, " ").toLowerCase();

export function cardsFromDoc(doc: OwnDoc, now = Date.now()): Card[] {
  const base = { docId: doc.id, docTitle: doc.title };
  const cards: Card[] = [];

  for (const g of glossary(doc)) {
    if (!g.definition) continue;
    cards.push(
      newCard(
        {
          ...base,
          id: `g:${doc.id}:${g.term.toLowerCase()}`,
          source: "glossary",
          front: `Define: ${g.term}`,
          back: g.definition + (g.source === "yours" ? "\n\n(your definition)" : ""),
        },
        now,
      ),
    );
  }

  const quiz = doc.assess?.quiz;
  const byId = new Map((quiz?.questions ?? []).map((q) => [q.id, q]));
  for (const r of quiz?.results ?? []) {
    const q = byId.get(r.id);
    if (r.correct !== false || !q) continue;
    const front =
      q.type === "tf"
        ? `True or false?\n\n“${q.prompt}”`
        : q.type === "mcq"
          ? `${q.prompt}\n\n${(q.options ?? []).join(" · ")}`
          : q.prompt;
    const back = q.type === "tf" ? `${q.answer_key === "true" ? "True" : "False"}.\n\n${q.explanation}` : `${q.answer_key}\n\n${q.explanation}`;
    cards.push(newCard({ ...base, id: `q:${doc.id}:${hash(q.prompt)}`, source: "quiz", front, back: back.trim() }, now));
  }

  for (const t of doc.assess?.viva?.turns ?? []) {
    if (t.score >= VIVA_PASS) continue;
    const missed = t.missed_concepts.length ? `\n\nKey ideas: ${t.missed_concepts.join(", ")}` : "";
    cards.push(
      newCard(
        { ...base, id: `v:${doc.id}:${hash(t.question)}`, source: "viva", front: t.question, back: `${t.model_answer ?? t.feedback}${missed}`.trim() },
        now,
      ),
    );
  }

  // the student's recurring writing issues: one card per rule, with an example from their text
  const issues = doc.analysis?.issues ?? [];
  const text = doc.analysisText ?? "";
  const byRule = new Map<string, typeof issues>();
  for (const i of issues) byRule.set(i.rule, [...(byRule.get(i.rule) ?? []), i]);
  const recurring = [...byRule.entries()].filter(([, list]) => list.length >= 2).sort((a, b) => b[1].length - a[1].length);
  for (const [rule, list] of recurring.slice(0, MAX_WRITING_CARDS)) {
    const example = list.find((i) => text && i.end > i.start && i.end - i.start < 160) ?? list[0];
    const quote = text ? text.slice(example.start, example.end).trim() : "";
    if (!quote) continue;
    const fix = example.suggestion != null ? `\n\nFix: ${example.suggestion === "" ? "delete it" : `“${example.suggestion}”`}` : "";
    cards.push(
      newCard(
        {
          ...base,
          id: `w:${doc.id}:${rule}`,
          source: "writing",
          front: `How would you improve this (${ruleLabel(rule)}, ${list.length}× in your text)?\n\n“${quote}”`,
          back: `${example.message}${fix}`,
        },
        now,
      ),
    );
  }
  return cards;
}

/** Add cards for anything new in the documents; existing cards keep their schedule. */
export function syncCards(existing: Card[], docs: OwnDoc[], now = Date.now()): { cards: Card[]; added: number } {
  const ids = new Set(existing.map((c) => c.id));
  const titles = new Map(docs.map((d) => [d.id, d.title]));
  const fresh = docs.flatMap((d) => cardsFromDoc(d, now)).filter((c) => !ids.has(c.id) && (ids.add(c.id), true));
  const kept = existing.map((c) => (titles.has(c.docId) ? { ...c, docTitle: titles.get(c.docId)! } : c));
  return { cards: [...kept, ...fresh], added: fresh.length };
}

// ---------------------------------------------------------------- persistence
export async function loadCards(): Promise<Card[]> {
  return (await getMeta<Card[]>(CARDS_KEY)) ?? [];
}

export async function saveCards(cards: Card[]): Promise<void> {
  await setMeta(CARDS_KEY, cards);
}

export async function loadReviews(): Promise<Review[]> {
  return (await getMeta<Review[]>(REVIEWS_KEY)) ?? [];
}

export async function addReview(r: Review): Promise<Review[]> {
  const all = [...(await loadReviews()), r].slice(-MAX_REVIEWS_KEPT);
  await setMeta(REVIEWS_KEY, all);
  return all;
}
