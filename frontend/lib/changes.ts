import type { Change } from "./api";
import type { Decision, HumanizeState } from "./types";

export interface LocatedChange {
  change: Change;
  start: number;
  end: number;
}

/**
 * Where each pending engine change sits in the *current* text.
 *
 * Accepted changes shift later offsets by their length difference. If the student edited the
 * text too, we look for the original words near the expected position; changes that can't be
 * found any more are reported as stale.
 */
export function locatePending(current: string, h: HumanizeState): { located: LocatedChange[]; stale: string[] } {
  const located: LocatedChange[] = [];
  const stale: string[] = [];
  let delta = 0;
  const sorted = [...h.changes].sort((a, b) => a.orig_start - b.orig_start);
  for (const c of sorted) {
    const decision: Decision | undefined = h.decisions[c.id];
    if (decision === "accepted") {
      delta += c.replacement.length - (c.orig_end - c.orig_start);
      continue;
    }
    if (decision === "rejected") continue;
    const expected = c.orig_start + delta;
    const len = c.orig_end - c.orig_start;
    if (current.slice(expected, expected + len) === c.original) {
      located.push({ change: c, start: expected, end: expected + len });
      continue;
    }
    if (!c.original.trim()) {
      stale.push(c.id);
      continue;
    }
    // search nearby for the original words
    const lo = Math.max(0, expected - 300);
    const window = current.slice(lo, expected + len + 300);
    const idx = window.indexOf(c.original);
    if (idx >= 0) located.push({ change: c, start: lo + idx, end: lo + idx + len });
    else stale.push(c.id);
  }
  return { located, stale };
}

export function pendingCount(h: HumanizeState | undefined): number {
  if (!h) return 0;
  return h.changes.filter((c) => !h.decisions[c.id]).length;
}

export function decisionStats(h: HumanizeState | undefined) {
  const offered = h?.changes.length ?? 0;
  const decided = h ? Object.keys(h.decisions).filter((id) => h.changes.some((c) => c.id === id)).length : 0;
  const accepted = h ? Object.values(h.decisions).filter((d) => d === "accepted").length : 0;
  return { offered, decided, accepted, rejected: decided - accepted };
}

/** Trim leading/trailing spaces from a change for display ("␣in order" -> "in order"). */
export function displayPair(c: Change): { from: string; to: string } {
  return { from: c.original.trim(), to: c.replacement.trim() };
}
