import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN, EASE_OUT, prog, range, useLocal } from "../anim";
import { MaskReveal, Paper } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, monoLabel } from "../theme";

// The draft a student pasted: three stock "AI-style" phrases get flagged on the beat.
const DRAFT: Array<string | { text: string; cue: string }> = [
  { text: "In today’s fast-paced world,", cue: "mark1" },
  " strain gauges ",
  { text: "play a crucial role", cue: "mark2" },
  " in modern engineering. This report will ",
  { text: "delve into a myriad of", cue: "mark3" },
  " techniques that seamlessly integrate sensing and control.",
];

const Flag: React.FC<{ text: string; at: number }> = ({ text, at }) => {
  const f = useLocal();
  const sweep = prog(f, at - 2, 7);
  const tag = prog(f, at, 8);
  return (
    <span
      style={{
        position: "relative",
        backgroundImage: `linear-gradient(rgba(124,58,237,0.16), rgba(124,58,237,0.16))`,
        backgroundRepeat: "no-repeat",
        backgroundSize: `${sweep * 100}% 100%`,
        boxShadow: sweep > 0.98 ? `inset 0 -3px 0 ${C.vocabulary}` : undefined,
        color: sweep > 0.5 ? C.ink : undefined,
        borderRadius: 4,
      }}
    >
      {text}
      <span
        style={{
          position: "absolute",
          left: 0,
          top: -34,
          ...monoLabel,
          fontSize: 15,
          color: C.vocabulary,
          whiteSpace: "nowrap",
          opacity: tag,
          transform: `translateY(${(1 - tag) * 10}px)`,
        }}
      >
        AI-style phrase
      </span>
    </span>
  );
};

export const Hook: React.FC = () => {
  const f = useLocal();
  const h1 = cue("hook", "headline1");
  const h2 = cue("hook", "headline2");
  const blackout = cue("hook", "blackout");

  if (f >= blackout) return <AbsoluteFill style={{ background: C.dark }} />;

  const back = prog(f, h1 - 2, 12);
  const push = range(f, [h2, blackout], [1, 1.07], EASE_IN);
  const intro = prog(f, 0, 14);
  const underline = prog(f, h2 + 6, 9);

  return (
    <AbsoluteFill style={{ transform: `scale(${push})` }}>
      <Paper />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            width: 1320,
            fontFamily: F.serif,
            fontSize: 58,
            lineHeight: 1.5,
            letterSpacing: "-0.01em",
            color: "rgba(26,26,26,0.62)",
            opacity: intro * (1 - back * 0.82),
            filter: `blur(${back * 7}px)`,
            transform: `translateY(${(1 - intro) * 30}px) scale(${1 - back * 0.08})`,
          }}
        >
          <div style={{ ...monoLabel, fontSize: 17, color: C.muted, marginBottom: 46 }}>draft.docx · pasted from a chatbot</div>
          {DRAFT.map((d, i) => (typeof d === "string" ? <span key={i}>{d}</span> : <Flag key={i} text={d.text} at={cue("hook", d.cue)} />))}
        </div>
      </AbsoluteFill>

      {f >= h1 - 2 ? (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
          <div style={{ fontFamily: F.serif, fontSize: 168, lineHeight: 1, letterSpacing: "-0.04em", color: C.ink }}>
            {f < h2 ? (
              <MaskReveal at={h1} dur={10} out={h2 - 3}>
                AI wrote the draft.
              </MaskReveal>
            ) : (
              <span style={{ position: "relative", display: "inline-block" }}>
                <MaskReveal at={h2} dur={10}>
                  Can you <em style={{ color: C.signal, fontStyle: "italic" }}>defend</em> it?
                </MaskReveal>
                <span
                  style={{
                    position: "absolute",
                    left: "37%",
                    bottom: -18,
                    height: 8,
                    width: `${underline * 46}%`,
                    background: C.signal,
                    borderRadius: 4,
                  }}
                />
              </span>
            )}
          </div>
          <div
            style={{
              ...monoLabel,
              fontSize: 22,
              color: C.muted,
              marginTop: 54,
              opacity: prog(f, h2 + 8, 8, EASE_OUT),
            }}
          >
            Viva: tomorrow, 09:00
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
