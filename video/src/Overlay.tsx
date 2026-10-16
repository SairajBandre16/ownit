import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { EASE_IN_OUT, prog, range } from "./anim";
import { LogoMark } from "./components/primitives";
import { C, F, monoLabel } from "./theme";
import { FPS, SceneId, cue, scene, sceneAt } from "./timeline";

const DARK: SceneId[] = ["brand", "viva"];
const STEPS: Array<{ id: SceneId; label: string }> = [
  { id: "humanize", label: "Humanize" },
  { id: "walkthrough", label: "Walkthrough" },
  { id: "mine", label: "Make it yours" },
  { id: "viva", label: "Prove it" },
  { id: "export", label: "Export" },
];

/** Notebook chrome: crop marks, a wordmark, a timecode, and the five-step rail. */
export const Overlay: React.FC = () => {
  const g = useCurrentFrame();
  const id = sceneAt(g);
  const hidden =
    id === "badges" ||
    (id === "hook" && g >= cue("hook", "blackout")) ||
    (id === "end" && g < scene("end").start + 6);
  if (hidden) return null;
  const dark = DARK.includes(id);
  const ink = dark ? C.darkText : C.ink;
  const faint = dark ? "rgba(237,235,230,0.35)" : "rgba(26,26,26,0.35)";
  const muted = dark ? C.darkMuted : C.muted;

  const sec = Math.floor(g / FPS);
  const fr = g % FPS;
  const tc = `00:${String(sec).padStart(2, "0")}:${String(fr).padStart(2, "0")}`;

  const railFrom = scene("humanize").start;
  const railTo = scene("badges").start;
  const railIn = range(g, [railFrom, railFrom + 12], [0, 1]);
  const railOut = range(g, [railTo - 8, railTo], [1, 0]);
  const doctor = scene("doctor");
  const railDoctor = range(g, [doctor.start - 1, doctor.start + 4, doctor.start + doctor.len - 4, doctor.start + doctor.len], [1, 0.25, 0.25, 1]);
  const railOpacity = g < railFrom || g >= railTo ? 0 : railIn * railOut * railDoctor;

  const mark = (x: "left" | "right", y: "top" | "bottom") => (
    <div
      key={x + y}
      style={{
        position: "absolute",
        [x]: 48,
        [y]: 48,
        width: 28,
        height: 28,
        [`border${y === "top" ? "Top" : "Bottom"}`]: `1.5px solid ${faint}`,
        [`border${x === "left" ? "Left" : "Right"}`]: `1.5px solid ${faint}`,
      }}
    />
  );

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {mark("left", "top")}
      {mark("right", "top")}
      {mark("left", "bottom")}
      {mark("right", "bottom")}

      {id !== "hook" && id !== "brand" && id !== "end" ? (
        <div style={{ position: "absolute", left: 120, top: 76, display: "flex", alignItems: "center", gap: 12 }}>
          <LogoMark size={30} still ink={ink} muted={muted} />
          <span style={{ fontFamily: F.serif, fontSize: 30, color: ink, letterSpacing: "-0.02em" }}>
            Own<em style={{ color: dark ? C.signal : C.signalInk }}>It</em>
          </span>
        </div>
      ) : null}
      <div style={{ position: "absolute", right: 120, top: 84, display: "flex", gap: 26, ...monoLabel, fontSize: 15, color: muted }}>
        <span>0 AI models · 0 external APIs</span>
        <span style={{ color: ink }}>{tc}</span>
      </div>

      <div style={{ position: "absolute", left: 120, right: 120, bottom: 70, display: "flex", gap: 16, opacity: railOpacity }}>
        {STEPS.map((s, i) => {
          const sc = scene(s.id);
          const cur = id === s.id;
          const done = g >= sc.start + sc.len;
          const fill = cur ? prog(g, sc.start, sc.len, EASE_IN_OUT) : done ? 1 : 0;
          return (
            <div key={s.id} style={{ flex: 1 }}>
              <div style={{ ...monoLabel, fontSize: 14, color: cur ? ink : muted, marginBottom: 10, display: "flex", gap: 10 }}>
                <span style={{ color: cur ? (dark ? C.signal : C.signalInk) : muted }}>0{i + 1}</span>
                {s.label}
              </div>
              <div style={{ height: 3, background: dark ? C.darkRule : C.rule, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${fill * 100}%`, background: cur ? C.signal : ink, opacity: cur ? 1 : 0.7 }} />
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
