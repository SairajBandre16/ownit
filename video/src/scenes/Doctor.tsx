import React from "react";
import { AbsoluteFill } from "remotion";
import { pop, prog, useLocal } from "../anim";
import { Check, Chip, MaskReveal, Paper, StepTitle } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, cardStyle } from "../theme";

const ROWS = [
  { cue: "row1", cat: "Units", bad: "5kN", good: "5 kN", why: "Space between a number and its unit." },
  { cue: "row2", cat: "Abbreviations", bad: "PWM", good: "pulse-width modulation (PWM)", why: "Used before it was defined." },
  { cue: "row3", cat: "Claims", bad: "clearly proves", good: "add evidence", why: "Strong claim with no citation or figure." },
];

export const Doctor: React.FC = () => {
  const f = useLocal();
  return (
    <AbsoluteFill>
      <Paper />
      <StepTitle
        n="+"
        kicker="Also inside"
        title={
          <>
            <MaskReveal at={0}>Report</MaskReveal>
            <br />
            <MaskReveal at={2}>Doctor</MaskReveal>
          </>
        }
        caption="Engineering checks generic tools skip: SI units, abbreviations, figures, tense and unsupported claims."
      />
      <div style={{ position: "absolute", left: 800, top: 170, width: 1000, display: "flex", flexDirection: "column", gap: 22 }}>
        {ROWS.map((r) => {
          const at = cue("doctor", r.cue);
          const s = pop(f, at, 230, 17);
          const fix = prog(f, at + 3, 6);
          return (
            <div
              key={r.cue}
              style={{
                ...cardStyle,
                padding: "24px 34px",
                display: "flex",
                alignItems: "center",
                gap: 28,
                opacity: Math.min(1, s * 1.5),
                transform: `translateX(${(1 - s) * 160}px)`,
                borderLeft: `5px solid ${C.engineering}`,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
                  <Chip color={C.engineering}>{r.cat}</Chip>
                  <span style={{ fontFamily: F.sans, fontSize: 22, color: C.muted }}>{r.why}</span>
                </div>
                <div style={{ fontFamily: F.mono, fontSize: 36, marginTop: 14, display: "flex", alignItems: "center", gap: 18, whiteSpace: "nowrap" }}>
                  <span style={{ position: "relative", color: "rgba(26,26,26,0.5)" }}>
                    {r.bad}
                    <span style={{ position: "absolute", left: -4, right: -4, top: "52%", height: 3, background: C.signal, transform: `scaleX(${fix})`, transformOrigin: "0 50%" }} />
                  </span>
                  <span style={{ color: C.signalInk, opacity: fix }}>→</span>
                  <span style={{ color: C.ink, opacity: fix, transform: `translateX(${(1 - fix) * -14}px)` }}>{r.good}</span>
                </div>
              </div>
              <Check at={at + 5} size={44} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
