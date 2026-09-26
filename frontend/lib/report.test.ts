import { describe, expect, it } from "vitest";
import type { QuestionOut, ResultOut, WalkthroughResponse } from "./api";
import { computeGate } from "./gate";
import { computeOwnership } from "./ownership";
import { buildReportData, conceptLists, fileStem, glossary } from "./report";
import { DEFAULT_SETTINGS, type OwnDoc } from "./types";

const q = (id: string, prompt: string, key: string): QuestionOut => ({
  id,
  type: "cloze",
  prompt,
  answer_key: key,
  source_span: { start: 0, end: 1 },
  concepts: [key],
  accepted: [],
  explanation: "",
});
const r = (id: string, correct: boolean, concept: string): ResultOut => ({
  id,
  correct,
  score: correct ? 100 : 0,
  feedback: "",
  missed_concepts: correct ? [] : [concept],
  covered_concepts: correct ? [concept] : [],
  source_span: { start: 0, end: 1 },
});

const doc: OwnDoc = {
  id: "d",
  title: "Solar Tracker",
  author: "A. Student",
  createdAt: 0,
  updatedAt: 0,
  originalText: "",
  content: { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "abc", marks: [{ type: "origin", attrs: { origin: "student_insert" } }] }] }] },
  step: "export",
  settings: DEFAULT_SETTINGS,
  walkthrough: {
    text: "",
    data: {
      paragraphs: [
        { index: 0, key_terms: [{ term: "PLC", start: 0, end: 3, definition: "programmable logic controller", source: "abbreviation" }] },
        {
          index: 2,
          key_terms: [
            { term: "duty cycle", start: 0, end: 10, definition: null, source: null },
            { term: "plc", start: 0, end: 3, definition: "dup", source: "document" },
          ],
        },
      ],
      concept_map: { nodes: [], edges: [] },
    } as unknown as WalkthroughResponse,
    marks: { 0: "got", 2: "confusing" },
    ownDefs: { "duty cycle": "the share of time the signal is on" },
  },
  assess: {
    quiz: {
      text: "",
      seed: 0,
      questions: [q("q1", "The _____ switches the pump.", "relay"), q("q2", "The _____ reads the sensor.", "PLC")],
      answers: { q1: "valve", q2: "PLC" },
      results: [r("q1", false, "relay"), r("q2", true, "PLC")],
      total: 50,
    },
    teachback: { explanation: "We built it.", coverage: 62.5, covered: ["servo motor"], missed: ["relay", "LDR"], similarity: 0.5 },
    viva: {
      startedAt: 0,
      timed: false,
      turns: [
        { question: "What is a PLC?", difficulty: "Define", level: 1, target_concepts: [], answer: "A computer.", score: 80, feedback: "Good.", missed_concepts: [], covered_concepts: ["industrial computer"] },
        { question: "Why a relay?", difficulty: "Explain why", level: 3, target_concepts: [], answer: "", score: 0, feedback: "Not yet.", missed_concepts: ["relay"] },
      ],
    },
  },
};

describe("conceptLists", () => {
  it("ranks weak concepts by how often they came up and keeps them out of mastered", () => {
    const { mastered, weak } = conceptLists(doc);
    expect(weak[0]).toBe("relay"); // viva + teach-back + quiz
    expect(weak).toEqual(expect.arrayContaining(["LDR", "duty cycle"]));
    expect(mastered).toEqual(expect.arrayContaining(["industrial computer", "servo motor"]));
    expect(mastered).not.toContain("relay");
    // answered correctly in the quiz, but it is a key term of a paragraph marked confusing
    expect(mastered).not.toContain("PLC");
    expect(weak.map((w) => w.toLowerCase())).toContain("plc");
  });
});

describe("glossary", () => {
  it("lists each term once and prefers the student's own definition", () => {
    expect(glossary(doc)).toEqual([
      { term: "PLC", definition: "programmable logic controller", source: "abbreviation" },
      { term: "duty cycle", definition: "the share of time the signal is on", source: "yours" },
    ]);
  });
});

describe("buildReportData", () => {
  it("collects every part of the report", () => {
    const settings = { gateEnabled: true, quizThreshold: 70, teachbackThreshold: 60, walkthroughThreshold: 80 };
    const gate = computeGate(doc, settings);
    const data = buildReportData(doc, gate, computeOwnership(doc, "abc"), new Date(2026, 8, 26));
    expect(data.title).toBe("Solar Tracker");
    expect(data.date).toBe("26 September 2026");
    expect(data.gate.map((g) => g.passed)).toEqual([true, false, true]);
    expect(data.gate_passed).toBe(false);
    expect(data.quiz_missed).toEqual([{ prompt: "The _____ switches the pump.", answer_key: "relay", your_answer: "valve" }]);
    expect(data.viva).toHaveLength(2);
    expect(data.teachback_missed).toEqual(["relay", "LDR"]);
    expect(data.ownership_parts).toHaveLength(4);
  });
});

describe("fileStem", () => {
  it("makes a safe file name", () => {
    expect(fileStem("Solar Tracker: Report!")).toBe("Solar-Tracker-Report");
    expect(fileStem("***")).toBe("document");
  });
});
