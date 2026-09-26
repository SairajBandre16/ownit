import { describe, expect, it } from "vitest";
import { DAY, MIN_EASE, RELEARN_MS, type Card, dueCards, newCard, nextIntervalLabel, review, streak } from "./srs";

const T0 = new Date(2026, 8, 26, 9, 0).getTime();
const card = (): Card => newCard({ id: "c", front: "PLC", back: "programmable logic controller", source: "glossary", docId: "d", docTitle: "T" }, T0);

describe("SM-2", () => {
  it("starts due now with ease 2.5", () => {
    const c = card();
    expect(c.due).toBe(T0);
    expect(c.ease).toBe(2.5);
  });

  it("schedules 1 day, 6 days, then interval × ease for Good answers", () => {
    let c = review(card(), 3, T0);
    expect(c.interval).toBe(1);
    expect(c.due).toBe(T0 + DAY);
    c = review(c, 3, c.due);
    expect(c.interval).toBe(6);
    c = review(c, 3, c.due);
    expect(c.interval).toBe(Math.round(6 * c.ease));
    expect(c.reps).toBe(3);
  });

  it("Good keeps the ease, Easy raises it, Hard lowers it", () => {
    expect(review(card(), 3, T0).ease).toBeCloseTo(2.5);
    expect(review(card(), 4, T0).ease).toBeCloseTo(2.6);
    expect(review(card(), 2, T0).ease).toBeCloseTo(2.36);
  });

  it("Again restarts the card, shows it again in 10 minutes and counts a lapse", () => {
    let c = review(review(review(card(), 3, T0), 3, T0), 3, T0);
    c = review(c, 1, T0);
    expect(c.reps).toBe(0);
    expect(c.interval).toBe(0);
    expect(c.lapses).toBe(1);
    expect(c.due).toBe(T0 + RELEARN_MS);
    expect(review(c, 3, c.due).interval).toBe(1);
  });

  it("never lets the ease drop below 1.3", () => {
    let c = card();
    for (let i = 0; i < 20; i++) c = review(c, 1, T0);
    expect(c.ease).toBe(MIN_EASE);
  });

  it("labels the next interval for each grade", () => {
    const c = card();
    expect(nextIntervalLabel(c, 1, T0)).toBe("10 min");
    expect(nextIntervalLabel(c, 3, T0)).toBe("1 d");
    const mature = { ...c, reps: 5, interval: 40, ease: 2.5 };
    expect(nextIntervalLabel(mature, 3, T0)).toBe("3 mo");
  });
});

describe("dueCards and streak", () => {
  it("lists due cards, oldest first", () => {
    const a = { ...card(), id: "a", due: T0 - 1000 };
    const b = { ...card(), id: "b", due: T0 - 5000 };
    const later = { ...card(), id: "c", due: T0 + DAY };
    expect(dueCards([a, b, later], T0).map((c) => c.id)).toEqual(["b", "a"]);
  });

  it("counts consecutive review days, and survives until today's review", () => {
    const at = (daysAgo: number) => ({ at: T0 - daysAgo * DAY, cardId: "c", grade: 3 as const });
    expect(streak([at(0), at(1), at(2)], T0)).toBe(3);
    expect(streak([at(1), at(2)], T0)).toBe(2); // not reviewed yet today
    expect(streak([at(0), at(2)], T0)).toBe(1);
    expect(streak([], T0)).toBe(0);
  });
});
