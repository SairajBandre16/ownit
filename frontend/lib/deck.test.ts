import { describe, expect, it } from "vitest";
import type { AnalyzeResponse, Issue, QuestionOut, WalkthroughResponse } from "./api";
import { addReview, cardsFromDoc, hash, loadCards, loadReviews, saveCards, syncCards } from "./deck";
import { review } from "./srs";
import { DEFAULT_SETTINGS, type OwnDoc } from "./types";

const issue = (rule: string, start: number, end: number): Issue => ({
  id: `${rule}-${start}`,
  start,
  end,
  category: "clarity",
  rule,
  severity: "warn",
  message: "Shorter: 'to'.",
  suggestion: "to",
  lesson_slug: "concision",
});
const text = "We did it in order to test. We ran it in order to check.";
const quizQ: QuestionOut = {
  id: "q1",
  type: "tf",
  prompt: "The valve switches the pump.",
  answer_key: "false",
  source_span: { start: 0, end: 1 },
  concepts: [],
  accepted: [],
  explanation: "The relay switches the pump.",
};

function doc(id = "d1"): OwnDoc {
  return {
    id,
    title: "Pump report",
    createdAt: 0,
    updatedAt: 0,
    originalText: text,
    content: { type: "doc" },
    step: "prove",
    settings: DEFAULT_SETTINGS,
    analysisText: text,
    analysis: { issues: [issue("wordy_phrase", 10, 21), issue("wordy_phrase", 38, 49), issue("long_sentence", 0, 5)] } as unknown as AnalyzeResponse,
    walkthrough: {
      text: "",
      data: {
        paragraphs: [
          {
            index: 0,
            key_terms: [
              { term: "relay", start: 0, end: 5, definition: "an electrically operated switch", source: "wordnet" },
              { term: "duty cycle", start: 0, end: 5, definition: null, source: null },
            ],
          },
        ],
        concept_map: { nodes: [], edges: [] },
      } as unknown as WalkthroughResponse,
      marks: {},
      ownDefs: { relay: "a switch the ESP32 turns on" },
    },
    assess: {
      quiz: { text: "", seed: 0, questions: [quizQ], answers: { q1: "true" }, results: [{ id: "q1", correct: false, score: 0, feedback: "", missed_concepts: [], covered_concepts: [], source_span: { start: 0, end: 1 } }], total: 0 },
      viva: {
        startedAt: 0,
        timed: false,
        turns: [
          { question: "Why a relay?", difficulty: "", target_concepts: [], answer: "", score: 20, feedback: "", missed_concepts: ["isolation"], model_answer: "The relay isolates the pump circuit." },
          { question: "What is a PLC?", difficulty: "", target_concepts: [], answer: "", score: 90, feedback: "", missed_concepts: [] },
        ],
      },
    },
  };
}

describe("cardsFromDoc", () => {
  it("makes cards from the glossary, quiz misses, weak viva answers and recurring writing issues", () => {
    const cards = cardsFromDoc(doc(), 1000);
    const bySource = (s: string) => cards.filter((c) => c.source === s);
    expect(bySource("glossary").map((c) => c.front)).toEqual(["Define: relay"]); // terms without a definition are skipped
    expect(bySource("glossary")[0].back).toContain("a switch the ESP32 turns on");
    expect(bySource("quiz")[0].front).toContain("True or false?");
    expect(bySource("quiz")[0].back).toMatch(/^False\./);
    expect(bySource("viva").map((c) => c.front)).toEqual(["Why a relay?"]); // 90 is not weak
    expect(bySource("viva")[0].back).toContain("isolation");
    const writing = bySource("writing");
    expect(writing).toHaveLength(1); // long_sentence occurs once only
    expect(writing[0].front).toContain("“in order to”");
    expect(writing[0].back).toContain("Fix: “to”");
    expect(cards.every((c) => c.due === 1000)).toBe(true);
  });
});

describe("syncCards", () => {
  it("adds only new cards and keeps the schedule of existing ones", () => {
    const first = syncCards([], [doc()], 1000);
    expect(first.added).toBe(first.cards.length);
    const reviewed = first.cards.map((c) => (c.source === "glossary" ? review(c, 3, 2000) : c));
    const again = syncCards(reviewed, [{ ...doc(), title: "Renamed" }], 3000);
    expect(again.added).toBe(0);
    const g = again.cards.find((c) => c.source === "glossary")!;
    expect(g.reps).toBe(1);
    expect(g.docTitle).toBe("Renamed");
    expect(syncCards(again.cards, [doc(), doc("d2")], 4000).added).toBe(first.cards.length);
  });

  it("uses stable ids", () => {
    expect(hash("Why a relay?")).toBe(hash("Why a relay?"));
    expect(hash("a")).not.toBe(hash("b"));
  });
});

describe("persistence", () => {
  it("stores cards and reviews in IndexedDB", async () => {
    const { cards } = syncCards([], [doc()], 1000);
    await saveCards(cards);
    expect((await loadCards()).length).toBe(cards.length);
    await addReview({ at: 5, cardId: cards[0].id, grade: 3 });
    expect((await loadReviews()).at(-1)).toEqual({ at: 5, cardId: cards[0].id, grade: 3 });
  });
});
