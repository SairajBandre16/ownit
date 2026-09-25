import { describe, expect, it } from "vitest";
import type { KeyTerm, WalkthroughResponse } from "./api";
import { nodesForParagraph, remapMarks, termDefinition, termPieces } from "./walkthrough";

const term = (t: string, start: number, definition: string | null = null): KeyTerm => ({
  term: t,
  start,
  end: start + t.length,
  definition,
  source: definition ? "document" : null,
});

function data(text: string, paras: string[]): WalkthroughResponse {
  return {
    paragraphs: paras.map((p, i) => {
      const start = text.indexOf(p);
      return {
        index: i * 2,
        start,
        end: start + p.length,
        section: "body",
        gist: "",
        key_terms: [],
        simplified: p,
        grade_before: 0,
        grade_after: 0,
      };
    }),
    concept_map: {
      nodes: [
        { id: "plc", label: "PLC", weight: 1, paragraphs: [0, 2], x: 0, y: 0 },
        { id: "valve", label: "valve", weight: 0.5, paragraphs: [2], x: 1, y: 1 },
      ],
      edges: [],
    },
  };
}

describe("termPieces", () => {
  const text = "Intro\nThe PLC drives the valve.";
  const para = { start: 6, end: text.length, key_terms: [term("PLC", 10), term("valve", 25)] };

  it("splits text around terms and keeps every character", () => {
    const pieces = termPieces(text, para);
    expect(pieces.map((p) => p.text).join("")).toBe(text.slice(6));
    expect(pieces.filter((p) => p.term).map((p) => p.text)).toEqual(["PLC", "valve"]);
  });

  it("drops overlapping and out-of-range terms", () => {
    const pieces = termPieces(text, { ...para, key_terms: [term("PLC drives", 10), term("PLC", 10), term("Intro", 0)] });
    expect(pieces.filter((p) => p.term).map((p) => p.text)).toEqual(["PLC drives"]);
    expect(pieces.map((p) => p.text).join("")).toBe(text.slice(6));
  });

  it("returns the whole paragraph when there are no terms", () => {
    expect(termPieces(text, { ...para, key_terms: [] })).toEqual([{ text: text.slice(6) }]);
  });
});

describe("remapMarks", () => {
  const oldText = "First para here.\n\nSecond para here.";
  const old = { data: data(oldText, ["First para here.", "Second para here."]), text: oldText, marks: { 0: "got" as const, 2: "confusing" as const } };

  it("keeps marks for unchanged paragraphs even when indices shift", () => {
    const newText = "New para.\n\nFirst para here.\n\nSecond para edited.";
    const next = data(newText, ["New para.", "First para here.", "Second para edited."]);
    expect(remapMarks(old, next, newText)).toEqual({ 2: "got" });
  });

  it("returns no marks without a previous walkthrough", () => {
    expect(remapMarks(undefined, old.data, oldText)).toEqual({});
  });
});

describe("termDefinition", () => {
  it("prefers the student's own definition", () => {
    expect(termDefinition(term("PLC", 0, "a controller"), { plc: "my words" })).toEqual({ text: "my words", own: true });
    expect(termDefinition(term("PLC", 0, "a controller"), {})).toEqual({ text: "a controller", own: false });
    expect(termDefinition(term("PLC", 0), undefined)).toEqual({ text: null, own: false });
  });
});

describe("nodesForParagraph", () => {
  it("lists the concept nodes that occur in a paragraph", () => {
    const d = data("a\n\nb", ["a", "b"]);
    expect(nodesForParagraph(d, 2)).toEqual(["plc", "valve"]);
    expect(nodesForParagraph(d, 0)).toEqual(["plc"]);
    expect(nodesForParagraph(d, null)).toEqual([]);
  });
});
