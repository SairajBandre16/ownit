import { describe, expect, it } from "vitest";
import { computeGate } from "./gate";
import { DEFAULT_SETTINGS, type OwnDoc } from "./types";

const settings = { gateEnabled: true, quizThreshold: 70, teachbackThreshold: 60, walkthroughThreshold: 80 };

function doc(partial: Partial<OwnDoc>): OwnDoc {
  return {
    id: "d",
    title: "t",
    createdAt: 0,
    updatedAt: 0,
    originalText: "",
    content: { type: "doc" },
    step: "prove",
    settings: DEFAULT_SETTINGS,
    ...partial,
  };
}

const walkthrough = (reviewed: number, total: number) => ({
  text: "",
  data: { paragraphs: Array.from({ length: total }, () => ({})) },
  marks: Object.fromEntries(Array.from({ length: reviewed }, (_, i) => [i, "got" as const])),
});

describe("understanding gate", () => {
  it("passes when all thresholds are met", () => {
    const g = computeGate(
      doc({
        walkthrough: walkthrough(4, 5),
        assess: {
          quiz: { questions: [], answers: {}, results: [], total: 70 },
          teachback: { explanation: "", coverage: 60, covered: [], missed: [], similarity: 0.5 },
        },
      }),
      settings,
    );
    expect(g.passed).toBe(true);
  });

  it("fails when the quiz is below 70 %", () => {
    const g = computeGate(
      doc({
        walkthrough: walkthrough(5, 5),
        assess: {
          quiz: { questions: [], answers: {}, results: [], total: 69 },
          teachback: { explanation: "", coverage: 90, covered: [], missed: [], similarity: 0.5 },
        },
      }),
      settings,
    );
    expect(g.quizOk).toBe(false);
    expect(g.passed).toBe(false);
  });

  it("fails when too few paragraphs were reviewed", () => {
    const g = computeGate(
      doc({
        walkthrough: walkthrough(3, 5),
        assess: {
          quiz: { questions: [], answers: {}, results: [], total: 100 },
          teachback: { explanation: "", coverage: 100, covered: [], missed: [], similarity: 1 },
        },
      }),
      settings,
    );
    expect(g.walkthroughOk).toBe(false);
    expect(g.passed).toBe(false);
  });

  it("fails with no attempts", () => {
    expect(computeGate(doc({}), settings).passed).toBe(false);
  });

  it("always passes when switched off", () => {
    expect(computeGate(doc({}), { ...settings, gateEnabled: false }).passed).toBe(true);
  });
});
