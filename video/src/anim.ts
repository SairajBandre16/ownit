import { createContext, useContext } from "react";
import { Easing, interpolate, spring, useCurrentFrame } from "remotion";
import { FPS } from "./timeline";

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);
export const EASE_IN = Easing.bezier(0.7, 0, 0.84, 0);

const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0..1 progress of an animation that starts at `start` and lasts `dur` frames. */
export function prog(frame: number, start: number, dur: number, easing = EASE_OUT): number {
  return interpolate(frame, [start, start + dur], [0, 1], { ...CLAMP, easing });
}

export function range(frame: number, input: number[], output: number[], easing = EASE_OUT): number {
  return interpolate(frame, input, output, { ...CLAMP, easing });
}

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** A springy 0..1 that overshoots a little; for things that "pop" on a beat. */
export function pop(frame: number, at: number, stiffness = 220, damping = 13): number {
  if (frame < at) return 0;
  return spring({ frame: frame - at, fps: FPS, config: { stiffness, damping, mass: 0.6 } });
}

/** Decaying shake for impacts. */
export function shake(frame: number, at: number, amp = 10, dur = 10): { x: number; y: number } {
  const t = frame - at;
  if (t < 0 || t > dur) return { x: 0, y: 0 };
  const k = amp * (1 - t / dur) ** 2;
  return { x: Math.sin(t * 12.9) * k, y: Math.cos(t * 9.7) * k };
}

/** Frame relative to the current scene's cut (negative while a transition brings it in). */
export const LocalFrame = createContext<number | null>(null);

export function useLocal(): number {
  const global = useCurrentFrame();
  const local = useContext(LocalFrame);
  return local ?? global;
}

/** Composition frame, also inside scenes (keeps the paper grid drifting continuously across cuts). */
export const GlobalFrame = createContext<number | null>(null);

export function useGlobal(): number {
  const frame = useCurrentFrame();
  const global = useContext(GlobalFrame);
  return global ?? frame;
}
