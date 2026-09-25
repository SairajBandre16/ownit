import { describe, expect, it } from "vitest";
import type { WalkthroughResponse } from "./api";
import { confusingParagraphs, scoreBand, summarizeViva, wordCount } from "./assess";
import { DEFAULT_SETTINGS, type OwnDoc, type VivaTurn } from "./types";

const turn = (level: number, score: number, missed: string[] = [], covered: string[] = []): VivaTurn => ({
  question: `q${level}-${score}`,
  difficulty: "",
  level,
  target_concepts: [],
  answer: "",
  score,
  feedback: "",
  missed_concepts: missed,
  covered_concepts: covered,
});

describe("summarizeViva", () => {
  it("averages scores overall and per level", () => {
    const s = summarizeViva([turn(1, 80), turn(2, 60), turn(2, 40), turn(4, 90)]);
    expect(s.answered).toBe(4);
    expect(s.average).toBe(67.5);
    expect(s.byLevel.map((l) => l.average)).toEqual([80, 50, null, 90]);
    expect(s.highestLevel).toBe(4);
  });

  it("ranks weak concepts by how often they were missed and lists never-missed strengths", () => {
    const s = summarizeViva([turn(1, 30, ["relay", "pump"], ["sensor"]), turn(1, 20, ["relay"], ["pump"]), turn(2, 90, [], ["sensor"])]);
    expect(s.weak).toEqual([
      { concept: "relay", missed: 2 },
      { concept: "pump", missed: 1 },
    ]);
    expect(s.strong).toEqual(["sensor"]);
  });

  it("handles an empty session", () => {
    const s = summarizeViva([]);
    expect(s.average).toBe(0);
    expect(s.highestLevel).toBe(0);
  });
});

describe("confusingParagraphs", () => {
  it("returns the text of paragraphs marked confusing", () => {
    const text = "One para.\n\nTwo para.";
    const doc = {
      id: "d",
      title: "",
      createdAt: 0,
      updatedAt: 0,
      originalText: text,
      content: { type: "doc" },
      step: "prove",
      settings: DEFAULT_SETTINGS,
      walkthrough: {
        text,
        data: {
          paragraphs: [
            { index: 0, start: 0, end: 9 },
            { index: 2, start: 11, end: 20 },
          ],
          concept_map: { nodes: [], edges: [] },
        } as unknown as WalkthroughResponse,
        marks: { 0: "got", 2: "confusing" },
      },
    } satisfies OwnDoc;
    expect(confusingParagraphs(doc)).toEqual(["Two para."]);
  });
});

describe("helpers", () => {
  it("bands scores and counts words", () => {
    expect(scoreBand(70).tone).toBe("good");
    expect(scoreBand(40).tone).toBe("mid");
    expect(scoreBand(39).tone).toBe("low");
    expect(wordCount("  a b  c ")).toBe(3);
    expect(wordCount("")).toBe(0);
  });
});
