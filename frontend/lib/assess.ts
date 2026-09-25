import type { OwnDoc, VivaTurn } from "./types";

/** Texts of the paragraphs the student marked "Confusing" in the walkthrough. */
export function confusingParagraphs(doc: OwnDoc): string[] {
  const wt = doc.walkthrough;
  if (!wt) return [];
  return wt.data.paragraphs.filter((p) => wt.marks[p.index] === "confusing").map((p) => wt.text.slice(p.start, p.end));
}

export const LEVELS = [
  { level: 1, name: "Define" },
  { level: 2, name: "Explain how" },
  { level: 3, name: "Explain why" },
  { level: 4, name: "Compare and evaluate" },
] as const;

export interface VivaSummary {
  answered: number;
  average: number; // 0-100
  byLevel: { level: number; name: string; count: number; average: number | null }[];
  /** concepts missed most often, most first */
  weak: { concept: string; missed: number }[];
  /** concepts covered and never missed */
  strong: string[];
  highestLevel: number;
}

export function summarizeViva(turns: VivaTurn[]): VivaSummary {
  const answered = turns.length;
  const average = answered ? turns.reduce((n, t) => n + t.score, 0) / answered : 0;
  const byLevel = LEVELS.map(({ level, name }) => {
    const ts = turns.filter((t) => (t.level ?? 1) === level);
    return { level, name, count: ts.length, average: ts.length ? ts.reduce((n, t) => n + t.score, 0) / ts.length : null };
  });
  const missed = new Map<string, number>();
  const covered = new Set<string>();
  for (const t of turns) {
    for (const c of t.missed_concepts) missed.set(c, (missed.get(c) ?? 0) + 1);
    for (const c of t.covered_concepts ?? []) covered.add(c);
  }
  const weak = [...missed.entries()].map(([concept, n]) => ({ concept, missed: n })).sort((a, b) => b.missed - a.missed || a.concept.localeCompare(b.concept));
  const strong = [...covered].filter((c) => !missed.has(c));
  const highestLevel = turns.filter((t) => t.score >= 70).reduce((m, t) => Math.max(m, t.level ?? 1), 0);
  return { answered, average, byLevel, weak, strong, highestLevel };
}

/** Plain-language band for a 0-100 score. */
export function scoreBand(score: number): { label: string; tone: "good" | "mid" | "low" } {
  if (score >= 70) return { label: "Strong", tone: "good" };
  if (score >= 40) return { label: "Partial", tone: "mid" };
  return { label: "Needs work", tone: "low" };
}

export const wordCount = (s: string) => (s.trim() ? s.trim().split(/\s+/).length : 0);
