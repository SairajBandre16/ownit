/**
 * Ownership Score (CLAUDE.md §9.2, U2).
 *
 *   score = 0.45 × student chars / total chars
 *         + 0.20 × decisions made / changes offered   (accepting or rejecting both count)
 *         + 0.20 × understanding score
 *         + 0.15 × personalization spots filled / spots found
 *
 * Honesty rules: a step that hasn't been done counts as 0. A part only drops out (and the other
 * weights are scaled up) when the step ran and had nothing to offer, e.g. no generic spots
 * were found. Characters are counted without whitespace; untagged text counts as AI.
 */
import type { JSONContent } from "@tiptap/core";
import { decisionStats } from "./changes";
import type { Origin, OwnDoc } from "./types";

export const ORIGINS: Origin[] = ["ai", "engine", "student_edit", "student_insert"];
export const ORIGIN_LABEL: Record<Origin, string> = {
  ai: "AI draft",
  engine: "Accepted rewrites",
  student_edit: "Your edits",
  student_insert: "Your additions",
};

export type OriginCounts = Record<Origin, number>;

export const WEIGHTS = { authorship: 0.45, decisions: 0.2, understanding: 0.2, personalization: 0.15 } as const;
export type PartKey = keyof typeof WEIGHTS;

export interface OwnershipPart {
  key: PartKey;
  label: string;
  weight: number;
  /** 0-1, or null when the part doesn't apply (the step had nothing to offer) */
  value: number | null;
  detail: string;
}

export interface OwnershipBreakdown {
  score: number; // 0-100
  studentShare: number; // 0-1
  counts: OriginCounts;
  total: number;
  parts: OwnershipPart[];
}

const nonSpace = (s: string) => s.replace(/\s+/g, "").length;

/** Non-whitespace characters per origin in TipTap JSON (untagged text counts as AI). */
export function originCounts(content: JSONContent | null | undefined): OriginCounts {
  const counts: OriginCounts = { ai: 0, engine: 0, student_edit: 0, student_insert: 0 };
  const walk = (node: JSONContent) => {
    if (node.type === "text" && node.text) {
      const mark = node.marks?.find((m) => m.type === "origin");
      const origin = (mark?.attrs?.origin as Origin | undefined) ?? "ai";
      counts[ORIGINS.includes(origin) ? origin : "ai"] += nonSpace(node.text);
    }
    node.content?.forEach(walk);
  };
  if (content) walk(content);
  return counts;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

function decisionsPart(doc: OwnDoc): OwnershipPart {
  const base = { key: "decisions" as const, label: "Decisions on suggested rewrites", weight: WEIGHTS.decisions };
  const hist = doc.decisionHistory;
  if (!doc.humanize && !hist) return { ...base, value: 0, detail: "Rewrites not requested yet" };
  const cur = decisionStats(doc.humanize);
  const offered = (hist?.offered ?? 0) + cur.offered;
  const decided = (hist?.decided ?? 0) + cur.decided;
  if (offered === 0) return { ...base, value: null, detail: "No rewrites were offered, so this part doesn't apply" };
  return { ...base, value: Math.min(1, decided / offered), detail: `${decided} of ${offered} changes accepted or rejected` };
}

/** Understanding (0-1): mean of walkthrough "Got it" share, quiz score and teach-back coverage. */
export function understandingScore(doc: OwnDoc): { value: number; detail: string } {
  const wt = doc.walkthrough;
  const paras = wt?.data?.paragraphs ?? [];
  const got = paras.length && wt ? paras.filter((p) => wt.marks[p.index] === "got").length / paras.length : 0;
  const quiz = (doc.assess?.quiz?.total ?? 0) / 100;
  const teach = (doc.assess?.teachback?.coverage ?? 0) / 100;
  const value = (got + quiz + teach) / 3;
  return {
    value,
    detail: `Walkthrough "Got it" ${pct(got)} · quiz ${pct(quiz)} · teach-back ${pct(teach)} (averaged)`,
  };
}

/** Spots whose inserted answer is still in the text (deleting an answer un-fills the spot). */
export function filledSpots(doc: OwnDoc, text: string): number {
  const p = doc.personalize;
  if (!p) return 0;
  const ids = new Set(p.spots.map((s) => s.id));
  return Object.entries(p.filled).filter(([id, answer]) => ids.has(id) && answer.trim() && text.includes(answer.trim())).length;
}

function personalizationPart(doc: OwnDoc, text: string): OwnershipPart {
  const base = { key: "personalization" as const, label: "Generic spots made your own", weight: WEIGHTS.personalization };
  const p = doc.personalize;
  if (!p) return { ...base, value: 0, detail: "Generic spots not checked yet" };
  if (!p.spots.length) return { ...base, value: null, detail: "No generic spots were found, so this part doesn't apply" };
  const filled = filledSpots(doc, text);
  return { ...base, value: filled / p.spots.length, detail: `${filled} of ${p.spots.length} spots filled` };
}

export function computeOwnership(doc: OwnDoc, text: string): OwnershipBreakdown {
  const counts = originCounts(doc.content);
  const total = ORIGINS.reduce((n, o) => n + counts[o], 0);
  const student = counts.student_edit + counts.student_insert;
  const studentShare = total ? student / total : 0;
  const u = understandingScore(doc);
  const parts: OwnershipPart[] = [
    {
      key: "authorship",
      label: "Text you wrote",
      weight: WEIGHTS.authorship,
      value: studentShare,
      detail: `${student.toLocaleString()} of ${total.toLocaleString()} characters are yours`,
    },
    decisionsPart(doc),
    { key: "understanding", label: "Understanding checks", weight: WEIGHTS.understanding, value: u.value, detail: u.detail },
    personalizationPart(doc, text),
  ];
  const applicable = parts.filter((p) => p.value != null);
  const weightSum = applicable.reduce((n, p) => n + p.weight, 0);
  const raw = weightSum ? applicable.reduce((n, p) => n + p.weight * (p.value as number), 0) / weightSum : 0;
  return { score: Math.round(Math.min(1, Math.max(0, raw)) * 100), studentShare, counts, total, parts };
}

/** Points each part adds to the score (after scaling for parts that don't apply). */
export function contributions(b: OwnershipBreakdown): Record<PartKey, number | null> {
  const weightSum = b.parts.filter((p) => p.value != null).reduce((n, p) => n + p.weight, 0) || 1;
  return Object.fromEntries(
    b.parts.map((p) => [p.key, p.value == null ? null : (100 * p.weight * p.value) / weightSum]),
  ) as Record<PartKey, number | null>;
}
