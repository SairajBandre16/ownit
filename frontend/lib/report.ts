/**
 * Data for the Understanding Report (§9.7): everything comes from the student's own work in the
 * app — ownership, the three checks, viva answers, quiz misses, teach-back and the glossary.
 */
import type { Schemas } from "./api";
import { summarizeViva } from "./assess";
import type { GateStatus } from "./gate";
import type { OwnershipBreakdown } from "./ownership";
import type { OwnDoc } from "./types";

type ReportRequest = Schemas["UnderstandingReportRequest"];

/** Case-insensitive de-duplication that keeps the first spelling. */
function unique(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const i of items) {
    const k = i.trim().toLowerCase();
    if (k && !seen.has(k)) {
      seen.add(k);
      out.push(i.trim());
    }
  }
  return out;
}

/** Concepts to revise (weak) and concepts shown to be understood (mastered). */
export function conceptLists(doc: OwnDoc): { mastered: string[]; weak: string[] } {
  const weakCount = new Map<string, { name: string; n: number }>();
  const addWeak = (c: string, n = 1) => {
    const k = c.trim().toLowerCase();
    if (!k) return;
    const cur = weakCount.get(k);
    weakCount.set(k, { name: cur?.name ?? c.trim(), n: (cur?.n ?? 0) + n });
  };
  const strong: string[] = [];

  const viva = doc.assess?.viva?.turns ?? [];
  const vs = summarizeViva(viva);
  vs.weak.forEach((w) => addWeak(w.concept, w.missed));
  strong.push(...vs.strong);

  const tb = doc.assess?.teachback;
  tb?.missed.forEach((c) => addWeak(c));
  strong.push(...(tb?.covered ?? []));

  for (const r of doc.assess?.quiz?.results ?? []) {
    if (r.correct === false) r.missed_concepts.forEach((c) => addWeak(c));
    else strong.push(...r.covered_concepts);
  }

  const wt = doc.walkthrough;
  if (wt) {
    for (const p of wt.data.paragraphs) if (wt.marks[p.index] === "confusing") p.key_terms.forEach((t) => addWeak(t.term));
  }

  const weak = [...weakCount.values()].sort((a, b) => b.n - a.n).map((w) => w.name);
  const weakSet = new Set(weak.map((w) => w.toLowerCase()));
  const mastered = unique(strong).filter((c) => !weakSet.has(c.toLowerCase()));
  return { mastered, weak: unique(weak) };
}

/** Glossary: every key term once, with the student's own definition when there is one. */
export function glossary(doc: OwnDoc): Schemas["GlossaryRow"][] {
  const wt = doc.walkthrough;
  if (!wt) return [];
  const rows = new Map<string, Schemas["GlossaryRow"]>();
  for (const p of wt.data.paragraphs) {
    for (const t of p.key_terms) {
      const key = t.term.toLowerCase();
      if (rows.has(key)) continue;
      const own = wt.ownDefs?.[key];
      rows.set(key, { term: t.term, definition: own ?? t.definition ?? null, source: own ? "yours" : (t.source ?? null) });
    }
  }
  return [...rows.values()];
}

export function buildReportData(doc: OwnDoc, gate: GateStatus, own: OwnershipBreakdown, date = new Date()): ReportRequest {
  const { mastered, weak } = conceptLists(doc);
  const quiz = doc.assess?.quiz;
  const tb = doc.assess?.teachback;
  const quizById = new Map((quiz?.questions ?? []).map((q) => [q.id, q]));
  return {
    title: doc.title,
    author: doc.author ?? null,
    date: date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }),
    ownership_score: own.score,
    student_share: own.studentShare,
    ownership_parts: own.parts.map((p) => ({ label: p.label, weight: p.weight, value: p.value, detail: p.detail })),
    gate: [
      { label: "Walkthrough reviewed", value: Math.round(gate.walkthroughPct * 100), required: gate.thresholds.walkthrough, passed: gate.walkthroughOk },
      { label: "Quiz", value: gate.quizScore, required: gate.thresholds.quiz, passed: gate.quizOk },
      { label: "Teach-back coverage", value: gate.teachbackCoverage, required: gate.thresholds.teachback, passed: gate.teachbackOk },
    ],
    gate_passed: gate.quizOk && gate.teachbackOk && gate.walkthroughOk,
    mastered,
    weak,
    glossary: glossary(doc),
    viva: (doc.assess?.viva?.turns ?? []).map((t) => ({
      question: t.question,
      difficulty: t.difficulty,
      answer: t.answer,
      score: t.score,
      feedback: t.feedback,
      missed_concepts: t.missed_concepts,
    })),
    quiz_total: quiz?.total ?? null,
    quiz_missed: (quiz?.results ?? [])
      .filter((r) => r.correct === false)
      .map((r) => {
        const q = quizById.get(r.id);
        return { prompt: q?.prompt ?? "", answer_key: q?.answer_key ?? "", your_answer: quiz?.answers[r.id] ?? "" };
      }),
    teachback_coverage: tb?.coverage ?? null,
    teachback_explanation: tb?.explanation ?? null,
    teachback_missed: tb?.missed ?? [],
  };
}

/** A safe file-name stem for a title. */
export function fileStem(title: string): string {
  return title.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "document";
}
