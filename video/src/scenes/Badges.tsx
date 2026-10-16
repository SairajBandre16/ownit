import React from "react";
import { AbsoluteFill } from "remotion";
import { prog, useLocal } from "../anim";
import { Paper } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, monoLabel } from "../theme";

type Card = { cue: string; bg: string; fg: string; dark?: boolean; label: string; big: React.ReactNode };

const CARDS: Card[] = [
  {
    cue: "b1",
    bg: C.dark,
    fg: C.darkText,
    dark: true,
    label: "Rule-based NLP",
    big: (
      <>
        <span style={{ fontFamily: F.mono, color: C.signal, fontSize: 300, letterSpacing: "-0.06em", marginRight: 40 }}>0</span>AI models
      </>
    ),
  },
  {
    cue: "b2",
    bg: C.signal,
    fg: C.ink,
    label: "No third-party calls",
    big: (
      <>
        <span style={{ fontFamily: F.mono, fontSize: 300, letterSpacing: "-0.06em", marginRight: 40 }}>0</span>external APIs
      </>
    ),
  },
  {
    cue: "b3",
    bg: C.paper,
    fg: C.ink,
    label: "Explainable by design",
    big: (
      <>
        Every change <em style={{ color: C.signal }}>explained.</em>
      </>
    ),
  },
  {
    cue: "b4",
    bg: C.dark,
    fg: C.darkText,
    dark: true,
    label: "",
    big: <em style={{ color: C.signal }}>Yours.</em>,
  },
];

export const Badges: React.FC = () => {
  const f = useLocal();
  const gap = cue("badges", "gap");
  if (f >= gap) return <AbsoluteFill style={{ background: C.dark }} />;
  let i = 0;
  CARDS.forEach((c, k) => {
    if (f >= cue("badges", c.cue)) i = k;
  });
  const card = CARDS[i];
  const t = f - cue("badges", card.cue);
  const punch = prog(t, 0, 8);
  return (
    <AbsoluteFill>
      {card.bg === C.signal ? <AbsoluteFill style={{ background: C.signal }} /> : <Paper dark={card.dark} />}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", transform: `scale(${1.1 - 0.1 * punch})` }}>
        <div style={{ ...monoLabel, fontSize: 22, color: card.dark ? C.darkMuted : card.bg === C.signal ? "rgba(26,26,26,0.7)" : C.muted, marginBottom: 20, opacity: punch }}>
          {card.label}
        </div>
        <div
          style={{
            fontFamily: F.serif,
            fontSize: 170,
            lineHeight: 1,
            letterSpacing: "-0.04em",
            color: card.fg,
            display: "flex",
            alignItems: "baseline",
            transform: `translateY(${(1 - punch) * 30}px)`,
            whiteSpace: "nowrap",
          }}
        >
          <span>{card.big}</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
