import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { EASE_IN, EASE_IN_OUT, GlobalFrame, LocalFrame, range } from "./anim";
import { Grain } from "./components/primitives";
import { Overlay } from "./Overlay";
import { Badges } from "./scenes/Badges";
import { Brand } from "./scenes/Brand";
import { Doctor } from "./scenes/Doctor";
import { End } from "./scenes/End";
import { Export } from "./scenes/Export";
import { Hook } from "./scenes/Hook";
import { Humanize } from "./scenes/Humanize";
import { MakeItYours } from "./scenes/MakeItYours";
import { Viva } from "./scenes/Viva";
import { Walkthrough } from "./scenes/Walkthrough";
import { C } from "./theme";
import { BEAT, SceneId, WIDTH, scene } from "./timeline";

type ShotProps = {
  id: SceneId;
  /** frames rendered before the cut (a transition brings the scene in) */
  pre?: number;
  /** frames rendered after the next cut (a transition takes the scene out) */
  post?: number;
  /** extra style per composition frame, for transitions */
  fx?: (g: number) => React.CSSProperties;
  children: React.ReactNode;
};

const ShotInner: React.FC<Omit<ShotProps, "id" | "post"> & { start: number }> = ({ pre = 0, start, fx, children }) => {
  const local = useCurrentFrame() - pre;
  const g = start + local;
  return (
    <GlobalFrame.Provider value={g}>
      <LocalFrame.Provider value={local}>
        <AbsoluteFill style={fx?.(g)}>{children}</AbsoluteFill>
      </LocalFrame.Provider>
    </GlobalFrame.Provider>
  );
};

/** A scene on the beat grid. Its local frame 0 is always the cut, whatever the transition. */
const Shot: React.FC<ShotProps> = ({ id, pre = 0, post = 0, fx, children }) => {
  const { start, len } = scene(id);
  return (
    <Sequence from={start - pre} durationInFrames={len + pre + post} name={id}>
      <ShotInner pre={pre} start={start} fx={fx}>
        {children}
      </ShotInner>
    </Sequence>
  );
};

// Whip pan: both scenes move together, fastest on the downbeat, with a little motion blur.
const PUSH = BEAT / 2;
function pushOut(cut: number) {
  return (g: number): React.CSSProperties => {
    const p = range(g, [cut - PUSH, cut + PUSH], [0, 1], EASE_IN_OUT);
    return { transform: `translateX(${-p * WIDTH}px)`, filter: `blur(${Math.sin(Math.PI * p) * 10}px)` };
  };
}
function pushIn(cut: number) {
  return (g: number): React.CSSProperties => {
    const p = range(g, [cut - PUSH, cut + PUSH], [0, 1], EASE_IN_OUT);
    return { transform: `translateX(${(1 - p) * WIDTH}px)`, filter: `blur(${Math.sin(Math.PI * p) * 10}px)` };
  };
}

// Iris: the dark exam hall opens from the centre and is fully open on the downbeat.
const IRIS = BEAT / 2;
function irisIn(cut: number) {
  return (g: number): React.CSSProperties => {
    const r = range(g, [cut - IRIS, cut], [0, 120], EASE_IN);
    return g >= cut ? {} : { clipPath: `circle(${r}% at 50% 50%)` };
  };
}

/** Signal-orange panel that sweeps across and fully covers the frame on the cut. */
const Wipe: React.FC<{ cut: number }> = ({ cut }) => {
  const g = useCurrentFrame();
  const h = BEAT / 2;
  if (g < cut - h || g > cut + h) return null;
  const x = g < cut ? range(g, [cut - h, cut], [-130, 0], EASE_IN) : range(g, [cut, cut + h], [0, 130]);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill
        style={{
          background: C.signal,
          borderLeft: `14px solid ${C.ink}`,
          borderRight: `14px solid ${C.ink}`,
          transform: `translateX(${x}%) skewX(-10deg) scaleX(1.25)`,
        }}
      />
    </AbsoluteFill>
  );
};

export const Intro: React.FC = () => {
  const walk = scene("walkthrough").start;
  const viva = scene("viva").start;
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Shot id="hook">
        <Hook />
      </Shot>
      <Shot id="brand">
        <Brand />
      </Shot>
      <Shot id="humanize" post={PUSH} fx={pushOut(walk)}>
        <Humanize />
      </Shot>
      <Shot id="walkthrough" pre={PUSH} fx={pushIn(walk)}>
        <Walkthrough />
      </Shot>
      <Shot id="mine">
        <MakeItYours />
      </Shot>
      <Shot id="viva" pre={IRIS} fx={irisIn(viva)}>
        <Viva />
      </Shot>
      <Shot id="doctor">
        <Doctor />
      </Shot>
      <Shot id="export">
        <Export />
      </Shot>
      <Shot id="badges">
        <Badges />
      </Shot>
      <Shot id="end">
        <End />
      </Shot>
      <Wipe cut={scene("humanize").start} />
      <Overlay />
      <Grain />
      <Html5Audio src={staticFile("soundtrack.wav")} />
    </AbsoluteFill>
  );
};
