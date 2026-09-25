import { describe, expect, it } from "vitest";
import { formatAnswer, insertionText, locateSpots, mergeSpots, sentenceEndAfter } from "./personalize";
import type { PersonalizeState, Spot } from "./types";

const text = "Intro\nRobotics plays a vital role in industry. It is used a lot.";

function spot(quote: string, id = `sp-${quote}`): Spot {
  const start = text.indexOf(quote);
  return {
    id,
    start,
    end: start + quote.length,
    insert_at: sentenceEndAfter(text, start + quote.length),
    pattern: "abstract_claim",
    label: "Claim with no example",
    prompt: "?",
    starter: "For example, ",
    quote,
  };
}

const state = (spots: Spot[], extra: Partial<PersonalizeState> = {}): PersonalizeState => ({
  text,
  spots,
  filled: {},
  skipped: {},
  ...extra,
});

describe("sentenceEndAfter", () => {
  it("finds the end of the sentence and stays on the line", () => {
    expect(text.slice(0, sentenceEndAfter(text, text.indexOf("plays")))).toMatch(/industry\.$/);
    expect(sentenceEndAfter("No stop here\nnext.", 0)).toBe("No stop here".length);
  });
});

describe("locateSpots", () => {
  it("uses the offsets directly when the text is unchanged", () => {
    const s = spot("plays a vital role in");
    const { located } = locateSpots(text, state([s]));
    expect(located[0]).toMatchObject({ start: s.start, end: s.end, insertAt: s.insert_at });
  });

  it("finds a spot again after an edit earlier in the text", () => {
    const s = spot("plays a vital role in");
    const edited = text.replace("Robotics", "Industrial robotics");
    const { located, stale } = locateSpots(edited, state([s]));
    expect(stale).toEqual([]);
    expect(edited.slice(located[0].start, located[0].end)).toBe("plays a vital role in");
    expect(edited.slice(0, located[0].insertAt)).toMatch(/industry\.$/);
  });

  it("reports spots whose words were rewritten as stale", () => {
    const s = spot("plays a vital role in");
    const { located, stale } = locateSpots(text.replace("plays a vital role in", "welds cars for"), state([s]));
    expect(located).toEqual([]);
    expect(stale).toEqual([s.id]);
  });

  it("skips filled and skipped spots", () => {
    const a = spot("plays a vital role in");
    const b = spot("used a lot");
    expect(locateSpots(text, state([a, b], { filled: { [a.id]: "x" }, skipped: { [b.id]: true } })).located).toEqual([]);
  });
});

describe("formatAnswer / insertionText", () => {
  it("makes a tidy sentence", () => {
    expect(formatAnswer("  for example,  our lab   uses a KUKA arm ")).toBe("For example, our lab uses a KUKA arm.");
    expect(formatAnswer("Is it?")).toBe("Is it?");
    expect(formatAnswer("   ")).toBe("");
  });

  it("adds a separating space only when needed", () => {
    expect(insertionText("Hi.", ".")).toBe(" Hi.");
    expect(insertionText("Hi.", " ")).toBe("Hi.");
    expect(insertionText("Hi.", "")).toBe("Hi.");
  });
});

describe("mergeSpots", () => {
  it("keeps filled spots whose answer is still in the text and replaces the rest", () => {
    const a = spot("plays a vital role in", "a");
    const b = spot("used a lot", "b");
    const prev = state([a, b], { filled: { a: "In our lab we weld." }, skipped: { b: true } });
    const fresh = spot("used a lot", "c");
    const merged = mergeSpots(prev, [fresh], "new text", "… In our lab we weld. …");
    expect(merged.spots.map((s) => s.id)).toEqual(["a", "c"]);
    expect(merged.filled).toEqual({ a: "In our lab we weld." });
    expect(merged.skipped).toEqual({});
    expect(merged.text).toBe("new text");
  });

  it("drops a filled spot when its answer was deleted", () => {
    const a = spot("plays a vital role in", "a");
    const merged = mergeSpots(state([a], { filled: { a: "Gone." } }), [], "t", "nothing here");
    expect(merged.spots).toEqual([]);
    expect(merged.filled).toEqual({});
  });
});
