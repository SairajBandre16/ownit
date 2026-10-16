import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN_OUT, pop, prog, useLocal } from "../anim";
import { Check, MaskReveal, Paper, StepTitle } from "../components/primitives";
import { cue, scene } from "../timeline";
import { C, F, cardStyle, monoLabel } from "../theme";

// Concept map, in the map's own coordinates (1000 x 500).
const CENTER = { x: 500, y: 250, label: "Strain gauge" };
const NODES = [
  { cue: "node1", x: 150, y: 90, label: "Torque", edge: "measures" },
  { cue: "node2", x: 770, y: 100, label: "Wheatstone bridge", edge: "sits in" },
  { cue: "node3", x: 800, y: 410, label: "Voltage", edge: "outputs" },
  { cue: "node4", x: 170, y: 410, label: "Calibration", edge: "needs" },
];

const Node: React.FC<{ x: number; y: number; label: string; at: number; main?: boolean }> = ({ x, y, label, at, main }) => {
  const f = useLocal();
  const s = pop(f, at, 260, 14);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${s})`,
        background: main ? C.ink : C.card,
        color: main ? C.paper : C.ink,
        border: `1.5px solid ${main ? C.ink : C.rule}`,
        borderRadius: 14,
        padding: main ? "18px 30px" : "14px 24px",
        fontFamily: F.sans,
        fontSize: main ? 32 : 27,
        fontWeight: 500,
        whiteSpace: "nowrap",
        boxShadow: "0 20px 40px -24px rgba(0,0,0,0.35)",
      }}
    >
      {main ? <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 6, background: C.signal, marginRight: 14, verticalAlign: "middle" }} /> : null}
      {label}
    </div>
  );
};

export const Walkthrough: React.FC = () => {
  const f = useLocal();
  const card = prog(f, -4, 14);
  const gotit = cue("walkthrough", "gotit");
  const zoom = 1 + 0.03 * prog(f, 0, scene("walkthrough").len, EASE_IN_OUT);
  return (
    <AbsoluteFill>
      <Paper />
      <StepTitle
        n="02"
        title={<MaskReveal at={-2}>Walkthrough</MaskReveal>}
        titleSize={112}
        caption="Every paragraph gets a gist, its key terms, and a concept map that follows your reading."
        at={-2}
      />
      <div
        style={{
          ...cardStyle,
          position: "absolute",
          left: 800,
          top: 170,
          width: 1000,
          padding: "26px 36px",
          opacity: card,
          transform: `translateY(${(1 - card) * 40}px)`,
          display: "flex",
          alignItems: "center",
          gap: 30,
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ ...monoLabel, fontSize: 15, color: C.muted }}>¶ 2 · gist</div>
          <div style={{ fontFamily: F.serif, fontSize: 36, lineHeight: 1.3, color: C.ink, marginTop: 10 }}>
            The gauge&apos;s resistance changes as the shaft twists; the{" "}
            <span style={{ borderBottom: `2px dotted ${C.voice}` }}>bridge</span> turns that into a voltage.
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 20px",
            borderRadius: 999,
            border: `1.5px solid ${f >= gotit ? C.ownInsert : C.rule}`,
            background: f >= gotit ? "rgba(21,128,61,0.08)" : "transparent",
            fontFamily: F.sans,
            fontSize: 24,
            color: f >= gotit ? C.ownInsert : C.muted,
            whiteSpace: "nowrap",
          }}
        >
          {f >= gotit ? <Check at={gotit} size={28} /> : null}
          Got it
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 800,
          top: 410,
          width: 1000,
          height: 500,
          borderRadius: 16,
          border: `1.5px dashed ${C.rule}`,
          backgroundImage: `radial-gradient(rgba(26,26,26,0.16) 1.4px, transparent 1.4px)`,
          backgroundSize: "26px 26px",
          overflow: "hidden",
          opacity: prog(f, -2, 10),
        }}
      >
        <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
          <svg width={1000} height={500} style={{ position: "absolute", inset: 0 }}>
            {NODES.map((n) => {
              const at = cue("walkthrough", n.cue);
              const d = prog(f, at - 2, 9);
              const len = Math.hypot(n.x - CENTER.x, n.y - CENTER.y);
              const mx = (n.x + CENTER.x) / 2;
              const my = (n.y + CENTER.y) / 2;
              return (
                <g key={n.cue}>
                  <line
                    x1={CENTER.x}
                    y1={CENTER.y}
                    x2={n.x}
                    y2={n.y}
                    stroke={C.ink}
                    strokeOpacity={0.45}
                    strokeWidth={2}
                    strokeDasharray={len}
                    strokeDashoffset={len * (1 - d)}
                  />
                  <text x={mx} y={my - 12} textAnchor="middle" fontFamily={F.mono} fontSize={17} fill={C.muted} opacity={prog(f, at + 3, 8)}>
                    {n.edge}
                  </text>
                </g>
              );
            })}
          </svg>
          <Node x={CENTER.x} y={CENTER.y} label={CENTER.label} at={-2} main />
          {NODES.map((n) => (
            <Node key={n.cue} x={n.x} y={n.y} label={n.label} at={cue("walkthrough", n.cue)} />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
