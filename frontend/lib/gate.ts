"use client";

import { useSettings } from "./store";
import type { OwnDoc } from "./types";

export interface GateStatus {
  enabled: boolean;
  quizScore: number | null;
  teachbackCoverage: number | null;
  walkthroughPct: number; // 0-1
  quizOk: boolean;
  teachbackOk: boolean;
  walkthroughOk: boolean;
  passed: boolean;
  thresholds: { quiz: number; teachback: number; walkthrough: number };
}

export function walkthroughProgress(doc: OwnDoc | null): number {
  const wt = doc?.walkthrough;
  if (!wt) return 0;
  const paras = (wt.data as { paragraphs?: unknown[] } | null)?.paragraphs?.length ?? 0;
  if (!paras) return 0;
  return Object.keys(wt.marks).length / paras;
}

/** Pure gate computation (§9.7): quiz ≥ 70 %, teach-back ≥ 60 %, walkthrough ≥ 80 % reviewed. */
export function computeGate(
  doc: OwnDoc | null,
  s: { gateEnabled: boolean; quizThreshold: number; teachbackThreshold: number; walkthroughThreshold: number },
): GateStatus {
  const quizScore = doc?.assess?.quiz?.total ?? null;
  const teachbackCoverage = doc?.assess?.teachback?.coverage ?? null;
  const walkthroughPct = walkthroughProgress(doc);
  const quizOk = quizScore != null && quizScore >= s.quizThreshold;
  const teachbackOk = teachbackCoverage != null && teachbackCoverage >= s.teachbackThreshold;
  const walkthroughOk = walkthroughPct * 100 >= s.walkthroughThreshold;
  return {
    enabled: s.gateEnabled,
    quizScore,
    teachbackCoverage,
    walkthroughPct,
    quizOk,
    teachbackOk,
    walkthroughOk,
    passed: !s.gateEnabled || (quizOk && teachbackOk && walkthroughOk),
    thresholds: { quiz: s.quizThreshold, teachback: s.teachbackThreshold, walkthrough: s.walkthroughThreshold },
  };
}

export function useGate(doc: OwnDoc | null): GateStatus {
  const s = useSettings();
  return computeGate(doc, s);
}
