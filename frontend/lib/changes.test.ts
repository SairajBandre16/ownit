import { describe, expect, it } from "vitest";
import type { Change } from "./api";
import { decisionStats, displayPair, locatePending } from "./changes";
import type { HumanizeState } from "./types";

const base = "We utilize a pump in order to move water. It is loud.";

function change(id: string, original: string, replacement: string, at = base.indexOf(original)): Change {
  return {
    id,
    orig_start: at,
    orig_end: at + original.length,
    new_start: 0,
    new_end: 0,
    original,
    replacement,
    transform: "phrase_simplify",
    category: "clarity",
    reason: "",
    confidence: 0.9,
  };
}

function state(decisions: HumanizeState["decisions"] = {}): HumanizeState {
  return {
    baseText: base,
    resultText: "",
    changes: [change("a", "utilize", "use"), change("b", " in order", "")],
    protected: [],
    scoreBefore: 50,
    scoreAfter: 60,
    decisions,
  };
}

describe("locatePending", () => {
  it("finds pending changes in the untouched text", () => {
    const { located, stale } = locatePending(base, state());
    expect(stale).toEqual([]);
    expect(located.map((l) => base.slice(l.start, l.end))).toEqual(["utilize", " in order"]);
  });

  it("shifts offsets after accepted changes", () => {
    const current = base.replace("utilize", "use");
    const { located } = locatePending(current, state({ a: "accepted" }));
    expect(located).toHaveLength(1);
    expect(current.slice(located[0].start, located[0].end)).toBe(" in order");
  });

  it("skips rejected changes", () => {
    const { located } = locatePending(base, state({ a: "rejected" }));
    expect(located.map((l) => l.change.id)).toEqual(["b"]);
  });

  it("recovers after the student edits earlier text", () => {
    const current = "Today we utilize a pump in order to move water. It is loud.";
    const { located, stale } = locatePending(current, state());
    expect(stale).toEqual([]);
    expect(current.slice(located[0].start, located[0].end)).toBe("utilize");
  });

  it("reports changes whose text was edited away as stale", () => {
    const current = "We employ a pump in order to move water. It is loud.";
    const { stale } = locatePending(current, state());
    expect(stale).toEqual(["a"]);
  });
});

describe("decision helpers", () => {
  it("counts decisions", () => {
    expect(decisionStats(state({ a: "accepted", b: "rejected" }))).toEqual({ offered: 2, decided: 2, accepted: 1, rejected: 1 });
  });
  it("trims display text", () => {
    expect(displayPair(change("b", " in order", ""))).toEqual({ from: "in order", to: "" });
  });
});
