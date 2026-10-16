import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN, EASE_IN_OUT, pop, prog, useLocal } from "../anim";
import { Check, MaskReveal, Paper, StepTitle } from "../components/primitives";
import { BEAT, cue, scene } from "../timeline";
import { C, F, cardStyle, monoLabel } from "../theme";

const GATES = [
  { cue: "gate1", label: "Quiz", value: 84, min: 70 },
  { cue: "gate2", label: "Teach-back", value: 71, min: 60 },
  { cue: "gate3", label: "Walkthrough", value: 100, min: 80 },
];

const Lock: React.FC<{ open: number; size: number }> = ({ open, size }) => {
  const color = open > 0.5 ? C.signal : C.ink;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" style={{ overflow: "visible" }}>
      <g style={{ transform: `translate(${open * 10}px, ${-open * 9}px) rotate(${open * 22}deg)`, transformOrigin: "44px 30px" }}>
        <path d="M20 30V20a12 12 0 0 1 24 0v10" stroke={color} strokeWidth={5} strokeLinecap="round" />
      </g>
      <rect x={12} y={29} width={40} height={30} rx={6} fill={color} />
      <circle cx={32} cy={42} r={4} fill={C.paper} />
      <rect x={30.5} y={43} width={3} height={8} rx={1.5} fill={C.paper} />
    </svg>
  );
};

const Doc: React.FC<{ name: string; sub: string; at: number; x: number; rot: number }> = ({ name, sub, at, x, rot }) => {
  const f = useLocal();
  const s = pop(f, at, 180, 16);
  return (
    <div
      style={{
        ...cardStyle,
        position: "absolute",
        left: x,
        top: 0,
        width: 260,
        height: 320,
        padding: 24,
        background: "#fff",
        transform: `translateY(${(1 - s) * 260}px) rotate(${rot * s}deg)`,
        opacity: Math.min(1, s * 2),
      }}
    >
      <div style={{ ...monoLabel, fontSize: 13, color: C.signalInk }}>.docx</div>
      {[0.9, 0.75, 0.85, 0.6, 0.8, 0.7, 0.5].map((w, i) => (
        <div key={i} style={{ height: 8, width: `${w * 100}%`, background: i === 0 ? C.ink : C.rule, borderRadius: 4, marginTop: i === 0 ? 18 : 12 }} />
      ))}
      <div style={{ position: "absolute", left: 24, right: 24, bottom: 22 }}>
        <div style={{ fontFamily: F.sans, fontSize: 21, fontWeight: 600, color: C.ink, lineHeight: 1.2 }}>{name}</div>
        <div style={{ fontFamily: F.sans, fontSize: 16, color: C.muted, marginTop: 4 }}>{sub}</div>
      </div>
    </div>
  );
};

export const Export: React.FC = () => {
  const f = useLocal();
  const unlock = cue("export", "unlock");
  const files = cue("export", "files");
  const open = prog(f, unlock, 8, EASE_IN_OUT);
  const burst = prog(f, unlock, 14);
  const out = prog(f, scene("export").len - BEAT / 2, BEAT / 2, EASE_IN);
  return (
    <AbsoluteFill style={{ transform: `scale(${1 + out * 0.18})`, filter: `blur(${out * 10}px)`, opacity: 1 - out * 0.3 }}>
      <Paper />
      <StepTitle n="05" title={<MaskReveal at={0}>Export</MaskReveal>} caption="A clean .docx and an Understanding Report, unlocked once you can explain your work." />
      <div style={{ ...cardStyle, position: "absolute", left: 800, top: 170, width: 600, padding: "30px 36px" }}>
        <div style={{ ...monoLabel, fontSize: 15, color: C.muted, marginBottom: 8 }}>Understanding gate</div>
        {GATES.map((g) => {
          const at = cue("export", g.cue);
          const fill = prog(f, at - 6, 8, EASE_IN_OUT);
          return (
            <div key={g.cue} style={{ marginTop: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: F.sans, fontSize: 27, color: C.ink }}>{g.label}</span>
                <span style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span style={{ fontFamily: F.mono, fontSize: 26, color: C.ink }}>{Math.round(g.value * fill)}%</span>
                  <span style={{ width: 30, height: 30, display: "inline-flex" }}>{f >= at ? <Check at={at} size={30} /> : null}</span>
                </span>
              </div>
              <div style={{ position: "relative", height: 10, borderRadius: 5, background: C.rule, marginTop: 10 }}>
                <div style={{ height: "100%", width: `${g.value * fill}%`, background: C.ink, borderRadius: 5 }} />
                <div style={{ position: "absolute", left: `${g.min}%`, top: -6, width: 2, height: 22, background: C.signal }} />
              </div>
            </div>
          );
        })}
        <div style={{ fontFamily: F.mono, fontSize: 15, color: C.muted, marginTop: 20 }}>orange tick = pass mark</div>
      </div>
      <div style={{ position: "absolute", left: 1440, top: 190, width: 360, height: 320, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            position: "absolute",
            width: 300,
            height: 300,
            borderRadius: 150,
            border: `3px solid ${C.signal}`,
            transform: `scale(${0.5 + burst * 0.8})`,
            opacity: f >= unlock ? 1 - burst : 0,
          }}
        />
        <div style={{ transform: `scale(${1 + 0.15 * Math.sin(Math.PI * prog(f, unlock, 8))})` }}>
          <Lock open={open} size={190} />
        </div>
        <div style={{ position: "absolute", bottom: -6, ...monoLabel, fontSize: 16, color: f >= unlock ? C.signalInk : C.muted }}>
          {f >= unlock ? "Export unlocked" : "Locked"}
        </div>
      </div>
      <div style={{ position: "absolute", left: 980, top: 600, width: 800, height: 340 }}>
        <Doc name="Strain gauge report" sub="Your final report" at={files} x={60} rot={-5} />
        <Doc name="Understanding Report" sub="Viva Q&A, glossary, weak concepts" at={files + 3} x={360} rot={4} />
      </div>
    </AbsoluteFill>
  );
};
