import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN_OUT, prog, shake, useLocal } from "../anim";
import { LogoMark, MaskReveal, Paper } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, monoLabel } from "../theme";

export const End: React.FC = () => {
  const f = useLocal();
  const hit = cue("end", "logo");
  const s = shake(f, hit, 9, 8);
  const flash = 1 - prog(f, hit, 10);
  const drift = 1.06 - 0.06 * prog(f, hit, 20) + 0.015 * prog(f, hit + 20, 64, EASE_IN_OUT);
  const urlAt = cue("end", "url");
  const lines: Array<{ cue: string; node: React.ReactNode }> = [
    { cue: "tagline1", node: "Humanize it." },
    { cue: "tagline2", node: "Understand it." },
    { cue: "tagline3", node: <em style={{ color: C.signalInk }}>Own it.</em> },
  ];
  return (
    <AbsoluteFill>
      <Paper />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 42%, rgba(255,90,31,${0.22 * flash}) 0%, transparent 50%)` }} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", transform: `translate(${s.x}px, ${s.y}px) scale(${drift})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 30, marginTop: -40 }}>
          <LogoMark size={170} at={hit} />
          <div style={{ fontFamily: F.serif, fontSize: 190, lineHeight: 1, letterSpacing: "-0.045em", color: C.ink }}>
            <MaskReveal at={hit + 2} dur={10}>
              Own
            </MaskReveal>
            <MaskReveal at={hit + 5} dur={10}>
              <em style={{ color: C.signalInk }}>It</em>
            </MaskReveal>
          </div>
        </div>
        <div style={{ display: "flex", gap: 30, fontFamily: F.serif, fontSize: 64, letterSpacing: "-0.02em", color: C.ink, marginTop: 40 }}>
          {lines.map((l) => (
            <MaskReveal key={l.cue} at={cue("end", l.cue)} dur={10}>
              {l.node}
            </MaskReveal>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 64, opacity: prog(f, urlAt, 10), transform: `translateY(${(1 - prog(f, urlAt, 10)) * 16}px)` }}>
          <span style={{ height: 1.5, width: 80, background: C.rule }} />
          <span style={{ ...monoLabel, fontSize: 22, color: C.ink, letterSpacing: "0.08em", textTransform: "none" }}>ownit-nine.vercel.app</span>
          <span style={{ height: 1.5, width: 80, background: C.rule }} />
        </div>
        <div style={{ ...monoLabel, fontSize: 16, color: C.muted, marginTop: 20, opacity: prog(f, urlAt + 4, 10) }}>
          A learning tool for engineering students
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
