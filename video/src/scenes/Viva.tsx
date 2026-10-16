import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN_OUT, lerp, pop, prog, useLocal } from "../anim";
import { Caret, Check, Cross, MaskReveal, Paper, StepTitle, typed } from "../components/primitives";
import { BEAT, cue } from "../timeline";
import { C, F, monoLabel } from "../theme";

const QUESTION = "Why did you choose a strain gauge over a load cell?";
const ANSWER = "It is more sensitive at small strains, it is cheaper, and it mounts straight onto the shaft.";
const LEVELS = ["Definition", "How", "Why", "Compare"];
const CONCEPTS = [
  { label: "sensitivity", ok: true },
  { label: "cost", ok: true },
  { label: "shaft mounting", ok: true },
  { label: "temperature drift", ok: false },
];

const Ring: React.FC<{ size: number; frame: number }> = ({ size, frame }) => {
  const remaining = 44 - frame / BEAT;
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={C.darkRule} strokeWidth={6} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={C.darkText}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - remaining / 60)}
        />
      </svg>
      <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.mono, fontSize: 36, color: C.darkText }}>
        {Math.ceil(remaining)}
      </span>
    </div>
  );
};

export const Viva: React.FC = () => {
  const f = useLocal();
  const q = cue("viva", "question");
  const ans = cue("viva", "answer");
  const cov = cue("viva", "coverage");
  const lvl = cue("viva", "level");
  const coverage = Math.round(lerp(0, 78, prog(f, cov, 14, EASE_IN_OUT)));
  const panel = prog(f, -4, 14);
  const level = f >= lvl ? 3 : 2;

  return (
    <AbsoluteFill>
      <Paper dark />
      <StepTitle
        n="04"
        dark
        title={<MaskReveal at={-2}>Prove it</MaskReveal>}
        caption="A quiz, a teach-back and a Viva Simulator that gets harder as you get it right."
        at={-2}
        kicker="Exam hall mode"
      />
      <div
        style={{
          position: "absolute",
          left: 800,
          top: 170,
          width: 1000,
          borderRadius: 18,
          background: C.darkCard,
          border: `1px solid ${C.darkRule}`,
          padding: "34px 48px",
          opacity: panel,
          transform: `translateY(${(1 - panel) * 40}px)`,
          boxShadow: "0 50px 100px -40px rgba(0,0,0,0.8)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 10 }}>
            {LEVELS.map((l, i) => {
              const active = i === level;
              const done = i < level;
              const s = active && i === 3 ? 1 + 0.12 * (1 - prog(f, lvl, 10)) : 1;
              return (
                <span
                  key={l}
                  style={{
                    ...monoLabel,
                    fontSize: 15,
                    padding: "8px 14px 7px",
                    borderRadius: 999,
                    border: `1.5px solid ${active ? C.signal : C.darkRule}`,
                    color: active ? C.signal : done ? C.darkText : C.darkMuted,
                    background: active ? "rgba(255,90,31,0.1)" : "transparent",
                    transform: `scale(${s})`,
                    display: "inline-block",
                  }}
                >
                  {done ? "✓ " : ""}
                  {l}
                </span>
              );
            })}
          </div>
          <Ring size={104} frame={f} />
        </div>
        <div style={{ ...monoLabel, fontSize: 15, color: C.darkMuted, marginTop: 34 }}>Question 6 of 10</div>
        <div style={{ fontFamily: F.serif, fontSize: 58, lineHeight: 1.2, letterSpacing: "-0.02em", color: C.darkText, marginTop: 14, minHeight: 140 }}>
          {typed(QUESTION, f, q, 3.4)}
          {f >= q && f < ans ? <Caret color={C.signal} /> : null}
        </div>
        <div style={{ marginTop: 26, display: "flex", gap: 18, alignItems: "flex-start", clipPath: `inset(0 ${(1 - prog(f, ans, 12)) * 100}% 0 0)` }}>
          <span style={{ ...monoLabel, fontSize: 14, color: C.darkMuted, paddingTop: 8, width: 120, flexShrink: 0 }}>Your answer</span>
          <span style={{ fontFamily: F.sans, fontSize: 27, lineHeight: 1.4, color: C.darkMuted, borderLeft: `2px solid ${C.darkRule}`, paddingLeft: 18 }}>{ANSWER}</span>
        </div>
        <div style={{ marginTop: 36, opacity: prog(f, cov - 3, 8) }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span style={{ ...monoLabel, fontSize: 15, color: C.darkMuted }}>Concept coverage of your answer</span>
            <span style={{ fontFamily: F.mono, fontSize: 44, color: C.darkText }}>{coverage}%</span>
          </div>
          <div style={{ height: 12, borderRadius: 6, background: C.darkRule, marginTop: 12, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${coverage}%`, background: C.signal, borderRadius: 6 }} />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginTop: 26 }}>
            {CONCEPTS.map((c, i) => {
              const at = cov + 3 + i * 5;
              const s = pop(f, at, 260, 15);
              return (
                <span
                  key={c.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 16px 8px 10px",
                    borderRadius: 999,
                    border: `1.5px solid ${c.ok ? "rgba(74,222,128,0.4)" : "rgba(255,90,31,0.5)"}`,
                    fontFamily: F.sans,
                    fontSize: 23,
                    color: c.ok ? C.darkText : C.signal,
                    transform: `scale(${s})`,
                  }}
                >
                  {c.ok ? <Check at={at} size={26} color="#16A34A" /> : <Cross at={at} size={26} />}
                  {c.label}
                </span>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
