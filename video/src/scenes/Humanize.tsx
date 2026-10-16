import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_IN_OUT, lerp, pop, prog, useLocal } from "../anim";
import { Check, Chip, MaskReveal, Paper, StepTitle, typed } from "../components/primitives";
import { cue } from "../timeline";
import { C, F, cardStyle, monoLabel } from "../theme";

type Seg = string | { from: string; to: string; cue: string } | { protect: string };

const SENTENCE: Seg[] = [
  { from: "In order to", to: "To", cue: "change1" },
  " measure the torque, ",
  { from: "it is important to note that ", to: "", cue: "change2" },
  "we ",
  { from: "utilized", to: "used", cue: "change3" },
  " a strain gauge. It samples the bridge at ",
  { protect: "1 kHz" },
  ".",
];

const CHANGES = [
  { cue: "change1", from: "in order to", to: "to", cat: "Clarity", color: C.clarity, reason: "Shorter, same meaning." },
  { cue: "change2", from: "it is important to note that", to: "∅", cat: "Vocabulary", color: C.vocabulary, reason: "A stock phrase that adds no information." },
  { cue: "change3", from: "utilized", to: "used", cat: "Vocabulary", color: C.vocabulary, reason: "A more common word, same meaning." },
];

const Change: React.FC<{ from: string; to: string; at: number }> = ({ from, to, at }) => {
  const f = useLocal();
  if (f < at) {
    const strike = prog(f, at - 6, 6, EASE_IN_OUT);
    return (
      <span
        style={{
          position: "relative",
          background: strike > 0 ? "rgba(217,119,6,0.14)" : undefined,
          borderRadius: 4,
          color: strike > 0 ? "rgba(26,26,26,0.55)" : undefined,
        }}
      >
        {from}
        <span style={{ position: "absolute", left: 0, top: "54%", height: 3, width: `${strike * 100}%`, background: C.signal }} />
      </span>
    );
  }
  if (!to) return null;
  const glow = 1 - prog(f, at, 24);
  return (
    <span
      style={{
        color: C.ownEngine,
        background: `rgba(59,130,246,${0.08 + 0.18 * glow})`,
        borderRadius: 4,
        boxShadow: `inset 0 -2px 0 rgba(59,130,246,0.55)`,
      }}
    >
      {typed(to, f, at, 1.2) || "​"}
    </span>
  );
};

/** Live stats under the editor: word count drops, meaning stays, no new grammar errors. */
const Footer: React.FC = () => {
  const f = useLocal();
  const done = CHANGES.filter((c) => f >= cue("humanize", c.cue)).length;
  const text = SENTENCE.map((s) => (typeof s === "string" ? s : "protect" in s ? s.protect : f >= cue("humanize", s.cue) ? s.to : s.from)).join("");
  const words = text.split(/\s+/).filter(Boolean).length;
  const meaning = ["1.00", "0.97", "0.94", "0.93"][done];
  const stat = (label: string, value: string, color: string = C.ink) => (
    <span style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
      <span style={{ ...monoLabel, fontSize: 14, color: C.muted }}>{label}</span>
      <span style={{ fontFamily: F.mono, fontSize: 22, color }}>{value}</span>
    </span>
  );
  return (
    <div style={{ display: "flex", gap: 40, borderTop: `1.5px dashed ${C.rule}`, marginTop: 22, paddingTop: 18 }}>
      {stat("Words", String(words))}
      {stat("Meaning kept", meaning)}
      {stat("New grammar errors", "0", C.ownInsert)}
    </div>
  );
};

const Gauge: React.FC<{ at: number; countAt: number }> = ({ at, countAt }) => {
  const f = useLocal();
  const appear = prog(f, at, 12);
  const t = prog(f, countAt, 22, EASE_IN_OUT);
  const value = Math.round(lerp(54, 82, t));
  const r = 120;
  const arc = Math.PI * r;
  const bars = [
    { name: "Clarity", color: C.clarity, a: 0.48, b: 0.86 },
    { name: "Rhythm", color: C.rhythm, a: 0.55, b: 0.78 },
    { name: "Vocabulary", color: C.vocabulary, a: 0.42, b: 0.84 },
    { name: "Voice", color: C.voice, a: 0.61, b: 0.8 },
    { name: "Correctness", color: C.grammar, a: 0.82, b: 0.9 },
  ];
  return (
    <div style={{ ...cardStyle, position: "absolute", left: 1404, top: 560, width: 396, height: 368, padding: "26px 30px", opacity: appear, transform: `translateY(${(1 - appear) * 40}px)` }}>
      <div style={{ ...monoLabel, fontSize: 15, color: C.muted }}>Writing score</div>
      <svg width={336} height={150} viewBox="-150 -140 300 150" style={{ display: "block", margin: "6px auto 0" }}>
        <path d={`M ${-r} 0 A ${r} ${r} 0 0 1 ${r} 0`} stroke={C.rule} strokeWidth={14} fill="none" strokeLinecap="round" />
        <path
          d={`M ${-r} 0 A ${r} ${r} 0 0 1 ${r} 0`}
          stroke={C.signal}
          strokeWidth={14}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={arc}
          strokeDashoffset={arc * (1 - value / 100)}
        />
        <text x={0} y={-8} textAnchor="middle" fontFamily={F.mono} fontSize={72} fontWeight={500} fill={C.ink}>
          {value}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 14 }}>
        {bars.map((b, i) => {
          const bt = prog(f, countAt + 2 + i * 2, 16, EASE_IN_OUT);
          return (
            <div key={b.name} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontFamily: F.sans, fontSize: 16, color: C.muted, width: 104 }}>{b.name}</span>
              <div style={{ flex: 1, height: 7, borderRadius: 4, background: C.rule, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${lerp(b.a, b.b, bt) * 100}%`, background: b.color, borderRadius: 4 }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const DiffStack: React.FC = () => {
  const f = useLocal();
  const accept = cue("humanize", "accept");
  const shown = CHANGES.filter((c) => f >= cue("humanize", c.cue));
  return (
    <div style={{ position: "absolute", left: 800, top: 560, width: 572, height: 360 }}>
      <div style={{ ...monoLabel, fontSize: 15, color: C.muted, marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <span>Changes</span>
        <span>
          {shown.length}/3 {f >= accept ? "· accepted" : ""}
        </span>
      </div>
      {shown.map((c, i) => {
        const depth = shown.length - 1 - i;
        const at = cue("humanize", c.cue);
        const enter = pop(f, at, 240, 18);
        return (
          <div
            key={c.cue}
            style={{
              ...cardStyle,
              position: "absolute",
              left: 0,
              right: 0,
              top: 40 + depth * 22,
              padding: "22px 26px",
              borderLeft: `5px solid ${C.ownEngine}`,
              zIndex: 10 - depth,
              opacity: (depth === 0 ? 1 : 0.55 - depth * 0.15) * Math.min(1, enter * 1.4),
              transform: `translateX(${(1 - enter) * 120}px) scale(${1 - depth * 0.045})`,
              transformOrigin: "50% 0%",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: F.mono, fontSize: 21, color: C.ink }}>
                “{c.from}” <span style={{ color: C.signalInk }}>→</span> “{c.to}”
              </span>
              <Chip color={c.color}>{c.cat}</Chip>
            </div>
            <div style={{ fontFamily: F.sans, fontSize: 26, color: C.ink, marginTop: 14 }}>{c.reason}</div>
            <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 14, marginTop: 14, height: 34 }}>
              {f >= accept ? (
                <>
                  <span style={{ ...monoLabel, fontSize: 14, color: C.ownInsert }}>Accepted</span>
                  <Check at={accept + (2 - depth) * 2} size={32} />
                </>
              ) : (
                <span style={{ ...monoLabel, fontSize: 14, color: C.muted }}>A accept · R reject</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Humanize: React.FC = () => {
  const f = useLocal();
  const card = prog(f, 0, 14);
  const captionAt = cue("humanize", "caption");
  const underline = prog(f, captionAt, 10);
  const protTag = prog(f, 30, 10);
  return (
    <AbsoluteFill>
      <Paper />
      <StepTitle
        n="01"
        title={<MaskReveal at={0}>Humanize</MaskReveal>}
        caption={
          <>
            A rule-based rewrite. Every change{" "}
            <span style={{ position: "relative", color: C.ink }}>
              explained
              <span style={{ position: "absolute", left: 0, bottom: -4, height: 4, width: `${underline * 100}%`, background: C.signal, borderRadius: 2 }} />
            </span>
            , and you accept or reject each one.
          </>
        }
      />
      <div
        style={{
          ...cardStyle,
          position: "absolute",
          left: 800,
          top: 170,
          width: 1000,
          padding: "30px 44px 26px",
          opacity: card,
          transform: `translateY(${(1 - card) * 50}px)`,
        }}
      >
        <div style={{ ...monoLabel, fontSize: 15, color: C.muted, display: "flex", justifyContent: "space-between", marginBottom: 18 }}>
          <span>Editor · ¶ 1</span>
          <span style={{ color: C.ownEngine }}>engine edits in blue</span>
        </div>
        <div style={{ fontFamily: F.serif, fontSize: 46, lineHeight: 1.5, color: C.ink, letterSpacing: "-0.01em", minHeight: 207 }}>
          {SENTENCE.map((s, i) => {
            if (typeof s === "string") return <span key={i}>{s}</span>;
            if ("protect" in s)
              return (
                <span key={i} style={{ position: "relative", fontFamily: F.mono, fontSize: 38, border: `2px dashed ${C.muted}`, borderRadius: 6, padding: "0 8px", background: "rgba(26,26,26,0.04)" }}>
                  {s.protect}
                  <span style={{ position: "absolute", left: 0, top: -30, ...monoLabel, fontSize: 13, color: C.muted, opacity: protTag, whiteSpace: "nowrap" }}>
                    protected
                  </span>
                </span>
              );
            return <Change key={i} from={s.from} to={s.to} at={cue("humanize", s.cue)} />;
          })}
        </div>
        <Footer />
      </div>
      <DiffStack />
      <Gauge at={cue("humanize", "change2")} countAt={cue("humanize", "gauge")} />
    </AbsoluteFill>
  );
};
