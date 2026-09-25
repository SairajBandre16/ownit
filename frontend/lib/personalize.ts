import type { PersonalizeState, Spot } from "./types";

export interface LocatedSpot {
  spot: Spot;
  start: number;
  end: number;
  /** where the answer goes (after the sentence the spot belongs to) */
  insertAt: number;
}

const SENTENCE_END = /[.!?]["”')\]]?(?=\s|$)/g;

/** End of the sentence that contains `from` (stays on the same line). */
export function sentenceEndAfter(text: string, from: number): number {
  const lineEnd = text.indexOf("\n", from);
  const limit = lineEnd < 0 ? text.length : lineEnd;
  SENTENCE_END.lastIndex = from;
  const m = SENTENCE_END.exec(text);
  return m && m.index < limit ? m.index + m[0].length : limit;
}

/**
 * Where each open spot (not filled, not skipped) sits in the *current* text. Spots whose quote
 * can no longer be found near its old place are reported as stale.
 */
export function locateSpots(current: string, p: PersonalizeState): { located: LocatedSpot[]; stale: string[] } {
  const located: LocatedSpot[] = [];
  const stale: string[] = [];
  const same = current === p.text;
  for (const spot of p.spots) {
    if (p.filled[spot.id] != null || p.skipped[spot.id]) continue;
    if (same) {
      located.push({ spot, start: spot.start, end: spot.end, insertAt: spot.insert_at });
      continue;
    }
    const lo = Math.max(0, spot.start - 400);
    const window = current.slice(lo, spot.end + 400 + Math.max(0, current.length - p.text.length));
    // the nearest occurrence of the quote to where it used to be
    let best = -1;
    for (let i = window.indexOf(spot.quote); i >= 0; i = window.indexOf(spot.quote, i + 1)) {
      if (best < 0 || Math.abs(lo + i - spot.start) < Math.abs(lo + best - spot.start)) best = i;
    }
    if (!spot.quote || best < 0) {
      stale.push(spot.id);
      continue;
    }
    const start = lo + best;
    const end = start + spot.quote.length;
    const tail = p.text.slice(spot.end, spot.insert_at);
    const insertAt = current.slice(end, end + tail.length) === tail ? end + tail.length : sentenceEndAfter(current, end);
    located.push({ spot, start, end, insertAt });
  }
  return { located, stale };
}

/** Tidy a student's answer into a sentence: trimmed, capitalised, with end punctuation. */
export function formatAnswer(answer: string): string {
  let a = answer.replace(/\s+/g, " ").trim();
  if (!a) return "";
  a = a[0].toUpperCase() + a.slice(1);
  if (!/[.!?]["”')]?$/.test(a)) a += ".";
  return a;
}

/** Text to insert after `charBefore`: a separating space unless there already is one. */
export function insertionText(formatted: string, charBefore: string): string {
  return charBefore && !/\s/.test(charBefore) ? ` ${formatted}` : formatted;
}

/** Merge a fresh detection with the previous state: filled spots are kept (they still count). */
export function mergeSpots(prev: PersonalizeState | undefined, spots: Spot[], text: string, currentText: string): PersonalizeState {
  const keep = prev ? prev.spots.filter((s) => prev.filled[s.id] != null && currentText.includes(prev.filled[s.id].trim())) : [];
  const keptIds = new Set(keep.map((s) => s.id));
  const filled = Object.fromEntries(Object.entries(prev?.filled ?? {}).filter(([id]) => keptIds.has(id)));
  return {
    text,
    spots: [...keep, ...spots.filter((s) => !keptIds.has(s.id))],
    filled,
    skipped: {},
  };
}

export const anchorId = (spotId: string) => `${spotId}:anchor`;
