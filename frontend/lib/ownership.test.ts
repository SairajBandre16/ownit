import type { JSONContent } from "@tiptap/core";
import { describe, expect, it } from "vitest";
import type { Change, WalkthroughResponse } from "./api";
import { computeOwnership, contributions, originCounts } from "./ownership";
import { DEFAULT_SETTINGS, type OwnDoc, type Spot } from "./types";

const t = (text: string, origin?: string): JSONContent => ({
  type: "text",
  text,
  ...(origin ? { marks: [{ type: "origin", attrs: { origin } }] } : {}),
});
const content = (...nodes: JSONContent[]): JSONContent => ({ type: "doc", content: [{ type: "paragraph", content: nodes }] });

function doc(partial: Partial<OwnDoc>): OwnDoc {
  return {
    id: "d",
    title: "t",
    createdAt: 0,
    updatedAt: 0,
    originalText: "",
    content: content(t("aaaa", "ai")),
    step: "personalize",
    settings: DEFAULT_SETTINGS,
    ...partial,
  };
}

const change = (id: string): Change => ({
  id,
  orig_start: 0,
  orig_end: 1,
  new_start: 0,
  new_end: 1,
  original: "a",
  replacement: "b",
  transform: "synonym",
  category: "vocabulary",
  reason: "",
  confidence: 1,
});

const humanize = (n: number, decided: number) => ({
  baseText: "",
  resultText: "",
  changes: Array.from({ length: n }, (_, i) => change(`c${i}`)),
  protected: [],
  scoreBefore: 0,
  scoreAfter: 0,
  decisions: Object.fromEntries(Array.from({ length: decided }, (_, i) => [`c${i}`, "accepted" as const])),
});

const spot = (id: string): Spot => ({ id, start: 0, end: 1, insert_at: 1, pattern: "p", label: "", prompt: "", starter: "", quote: "a" });

describe("originCounts", () => {
  it("counts non-whitespace characters per origin; untagged text is AI", () => {
    const c = originCounts(content(t("ab cd", "ai"), t(" ef ", "student_insert"), t("gh", "engine"), t("ij")));
    expect(c).toEqual({ ai: 6, engine: 2, student_edit: 0, student_insert: 2 });
  });
});

describe("computeOwnership", () => {
  it("is 0 for an untouched AI paste", () => {
    const b = computeOwnership(doc({}), "aaaa");
    expect(b.score).toBe(0);
    expect(b.studentShare).toBe(0);
  });

  it("applies the §9.2 weights when every step has run", () => {
    const d = doc({
      content: content(t("aaaaaa", "ai"), t("bb", "student_edit"), t("cc", "student_insert")), // 40 % student
      humanize: humanize(10, 5), // 50 % decided
      personalize: { text: "", spots: [spot("s1"), spot("s2")], filled: { s1: "Mine." }, skipped: {} }, // 1 of 2 still present
      assess: {
        quiz: { text: "", seed: 0, questions: [], answers: {}, results: [], total: 90 },
        teachback: { explanation: "", coverage: 60, covered: [], missed: [], similarity: 0 },
      },
      walkthrough: {
        text: "",
        data: { paragraphs: [{ index: 0 }, { index: 2 }], concept_map: { nodes: [], edges: [] } } as unknown as WalkthroughResponse,
        marks: { 0: "got", 2: "confusing" }, // 50 % got it
      },
    });
    const b = computeOwnership(d, "text with Mine. inside");
    // understanding = (0.5 + 0.9 + 0.6) / 3
    const expected = 0.45 * 0.4 + 0.2 * 0.5 + 0.2 * ((0.5 + 0.9 + 0.6) / 3) + 0.15 * 0.5;
    expect(b.score).toBe(Math.round(expected * 100));
    const c = contributions(b);
    expect(Object.values(c).reduce((n: number, x) => n + (x ?? 0), 0)).toBeCloseTo(expected * 100, 5);
  });

  it("counts steps not done as 0 but drops steps with nothing to offer", () => {
    const allMine = content(t("abcd", "student_insert"));
    const notDone = computeOwnership(doc({ content: allMine }), "abcd");
    expect(notDone.score).toBe(45);
    const nothingOffered = computeOwnership(
      doc({ content: allMine, humanize: humanize(0, 0), personalize: { text: "", spots: [], filled: {}, skipped: {} } }),
      "abcd",
    );
    // authorship 1.0 and understanding 0 over weights .45 + .20
    expect(nothingOffered.score).toBe(Math.round((0.45 / 0.65) * 100));
    expect(nothingOffered.parts.find((p) => p.key === "decisions")?.value).toBeNull();
  });

  it("does not count a filled spot whose answer was deleted", () => {
    const d = doc({ personalize: { text: "", spots: [spot("s1")], filled: { s1: "My example." }, skipped: {} } });
    expect(computeOwnership(d, "My example. here").parts.find((p) => p.key === "personalization")?.value).toBe(1);
    expect(computeOwnership(d, "deleted").parts.find((p) => p.key === "personalization")?.value).toBe(0);
  });

  it("counts decisions from earlier humanize runs", () => {
    const d = doc({ humanize: humanize(4, 0), decisionHistory: { offered: 6, decided: 6 } });
    expect(computeOwnership(d, "").parts.find((p) => p.key === "decisions")?.value).toBeCloseTo(0.6);
  });

  it("never exceeds 100", () => {
    const d = doc({
      content: content(t("abcd", "student_insert")),
      humanize: humanize(2, 2),
      personalize: { text: "", spots: [spot("s")], filled: { s: "x" }, skipped: {} },
      assess: {
        quiz: { text: "", seed: 0, questions: [], answers: {}, results: [], total: 100 },
        teachback: { explanation: "", coverage: 100, covered: [], missed: [], similarity: 1 },
      },
      walkthrough: {
        text: "",
        data: { paragraphs: [{ index: 0 }], concept_map: { nodes: [], edges: [] } } as unknown as WalkthroughResponse,
        marks: { 0: "got" },
      },
    });
    expect(computeOwnership(d, "x").score).toBe(100);
  });
});
