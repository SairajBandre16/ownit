import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN_OUT, lerp, pop, prog, useLocal } from "../anim";
import { Caret, MaskReveal, Paper, StepTitle, typed } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, cardStyle, monoLabel } from "../theme";

const INSERT = ", like the torque rig in our machines lab";

/** Origin tint for the ownership heatmap, faded in by `h` (0..1). */
function tint(origin: "ai" | "engine" | "insert", h: number): React.CSSProperties {
  const rgb = origin === "ai" ? "156,163,175" : origin === "engine" ? "59,130,246" : "21,128,61";
  return { background: `rgba(${rgb},${0.22 * h})`, borderRadius: 4 };
}

export const MakeItYours: React.FC = () => {
  const f = useLocal();
  const spot = cue("mine", "spot");
  const prompt = cue("mine", "prompt");
  const typing = cue("mine", "typing");
  const heat = cue("mine", "heatmap");
  const card = prog(f, 0, 12);
  const under = prog(f, spot - 2, 7);
  const bubble = pop(f, prompt, 240, 15);
  const h = prog(f, heat - 2, 10, EASE_IN_OUT);
  const own = Math.round(lerp(12, 38, prog(f, typing, heat + 8 - typing, EASE_IN_OUT)));
  const inserted = typed(INSERT, f, typing, 2);
  const typingNow = f >= typing && inserted.length < INSERT.length;

  const seg = [
    { w: 0.47, c: C.ownAi, label: "AI draft" },
    { w: 0.15, c: C.ownEngine, label: "engine" },
    { w: 0.38, c: C.ownInsert, label: "you" },
  ];
  const youW = lerp(0.12, 0.38, prog(f, typing, heat + 8 - typing, EASE_IN_OUT));

  return (
    <AbsoluteFill>
      <Paper />
      <StepTitle
        n="03"
        title={<MaskReveal at={0}>Make it yours</MaskReveal>}
        caption="OwnIt finds the generic spots and asks for your own data, examples and opinions."
      />
      <div style={{ ...cardStyle, position: "absolute", left: 800, top: 170, width: 1000, padding: "30px 44px 44px", opacity: card, transform: `translateY(${(1 - card) * 40}px)` }}>
        <div style={{ ...monoLabel, fontSize: 15, color: C.muted, display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <span>Results · ¶ 4</span>
          <span style={{ display: "flex", alignItems: "center", gap: 10, color: h > 0.5 ? C.ink : C.muted }}>
            Heatmap
            <span style={{ width: 46, height: 26, borderRadius: 13, background: h > 0.5 ? C.ink : C.rule, position: "relative", display: "inline-block" }}>
              <span style={{ position: "absolute", top: 3, left: 3 + 20 * h, width: 20, height: 20, borderRadius: 10, background: h > 0.5 ? C.signal : "#fff" }} />
            </span>
          </span>
        </div>
        <div style={{ fontFamily: F.serif, fontSize: 48, lineHeight: 1.5, color: C.ink, letterSpacing: "-0.01em" }}>
          <span style={tint("ai", h)}>Strain gauges are </span>
          <span style={tint("engine", h)}>common</span>
          <span style={tint("ai", h)}> in industry and </span>
          <span
            style={{
              ...tint("ai", h),
              backgroundImage: `linear-gradient(90deg, ${C.signal} 50%, transparent 50%)`,
              backgroundSize: "14px 3px",
              backgroundRepeat: "repeat-x",
              backgroundPosition: `0 100%`,
              paddingBottom: 2,
              clipPath: `inset(0 ${(1 - under) * 100}% 0 0)`,
            }}
          >
            have many applications
          </span>
          {inserted ? <span style={{ color: C.ownInsert, background: `rgba(21,128,61,${0.1 + 0.12 * h})`, borderRadius: 4 }}>{inserted}</span> : null}
          {typingNow ? <Caret color={C.ownInsert} /> : null}
          <span style={tint("ai", h)}>.</span>
        </div>
        <div
          style={{
            position: "absolute",
            left: 330,
            top: 268,
            transform: `scale(${bubble})`,
            transformOrigin: "20% 0%",
            background: C.ink,
            color: C.paper,
            borderRadius: 14,
            padding: "16px 22px",
            fontFamily: F.sans,
            fontSize: 25,
            boxShadow: "0 24px 48px -20px rgba(0,0,0,0.5)",
            opacity: 1 - prog(f, heat, 8),
            whiteSpace: "nowrap",
          }}
        >
          <span style={{ ...monoLabel, fontSize: 13, color: C.signal, display: "block", marginBottom: 6 }}>Generic spot</span>
          Name one you&apos;ve seen: lab, internship or project.
        </div>
      </div>
      <div style={{ ...cardStyle, position: "absolute", left: 800, top: 580, width: 1000, padding: "30px 44px", opacity: prog(f, 4, 12), transform: `translateY(${(1 - prog(f, 4, 12)) * 40}px)` }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div>
            <div style={{ ...monoLabel, fontSize: 15, color: C.muted }}>Ownership score</div>
            <div style={{ fontFamily: F.sans, fontSize: 26, color: C.ink, marginTop: 10 }}>
              An honest &ldquo;you wrote <span style={{ fontFamily: F.mono, color: C.ownInsert }}>{own}%</span> of this&rdquo;.
            </div>
          </div>
          <div style={{ fontFamily: F.mono, fontSize: 112, lineHeight: 0.9, color: C.ink, letterSpacing: "-0.04em" }}>
            {own}
            <span style={{ fontSize: 56, color: C.muted }}>%</span>
          </div>
        </div>
        <div style={{ display: "flex", height: 16, borderRadius: 8, overflow: "hidden", marginTop: 26, background: C.rule }}>
          <div style={{ width: `${(1 - 0.15 - youW) * 100}%`, background: C.ownAi }} />
          <div style={{ width: "15%", background: C.ownEngine }} />
          <div style={{ width: `${youW * 100}%`, background: C.ownInsert }} />
        </div>
        <div style={{ display: "flex", gap: 30, marginTop: 16 }}>
          {seg.map((s) => (
            <span key={s.label} style={{ ...monoLabel, fontSize: 14, color: C.muted, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: s.c }} />
              {s.label}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
