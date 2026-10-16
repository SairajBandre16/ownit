import React from "react";
import { AbsoluteFill } from "remotion";
import { EASE_OUT, pop, prog, useGlobal, useLocal } from "../anim";
import { C, F, monoLabel } from "../theme";

/** Grid-paper background that drifts slowly, so cuts between scenes feel like one notebook. */
export const Paper: React.FC<{ dark?: boolean; color?: string }> = ({ dark = false, color }) => {
  const frame = useGlobal();
  const minor = dark ? "rgba(237,235,230,0.045)" : "rgba(26,26,26,0.05)";
  const major = dark ? "rgba(237,235,230,0.075)" : "rgba(26,26,26,0.085)";
  const off = frame * 0.6;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: color ?? (dark ? C.dark : C.paper),
        backgroundImage: [
          `linear-gradient(${major} 1px, transparent 1px)`,
          `linear-gradient(90deg, ${major} 1px, transparent 1px)`,
          `linear-gradient(${minor} 1px, transparent 1px)`,
          `linear-gradient(90deg, ${minor} 1px, transparent 1px)`,
        ].join(","),
        backgroundSize: "200px 200px, 200px 200px, 40px 40px, 40px 40px",
        backgroundPosition: `${-off}px ${-off * 0.4}px`,
      }}
    >
      <AbsoluteFill
        style={{
          background: dark
            ? "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,0.45) 100%)"
            : "radial-gradient(ellipse at 50% 45%, transparent 60%, rgba(60,45,20,0.08) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

/** Static film grain over everything. */
export const Grain: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "multiply", opacity: 0.07 }}>
    <svg width="100%" height="100%">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </AbsoluteFill>
);

/**
 * The OwnIt mark: the thin grey half of the AI draft, your solid ink half, and the orange pen tip
 * where you take over the line. Both halves draw on, then the pen tip pops.
 */
export const LogoMark: React.FC<{ size: number; at?: number; ink?: string; muted?: string; still?: boolean }> = ({
  size,
  at = 0,
  ink = C.ink,
  muted = C.muted,
  still = false,
}) => {
  const f = useLocal();
  const left = still ? 1 : prog(f, at, 12);
  const right = still ? 1 : prog(f, at + 3, 12);
  const dot = still ? 1 : pop(f, at + 6, 260, 11);
  const len = 27;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" style={{ overflow: "visible" }}>
      <path
        d="M12 3.5A8.5 8.5 0 0 0 12 20.5"
        stroke={muted}
        strokeWidth={1.3}
        strokeLinecap="round"
        strokeDasharray={len}
        strokeDashoffset={len * (1 - left)}
        opacity={left > 0.01 ? 1 : 0}
      />
      <path
        d="M12 20.5A8.5 8.5 0 0 0 12 3.5"
        stroke={ink}
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeDasharray={len}
        strokeDashoffset={len * (1 - right)}
        opacity={right > 0.01 ? 1 : 0}
      />
      <circle cx={12} cy={3.5} r={2.7 * dot} fill={C.signal} />
    </svg>
  );
};

/** Line that slides up from behind a mask. */
export const MaskReveal: React.FC<{
  at: number;
  dur?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
  out?: number;
}> = ({ at, dur = 12, children, style, out }) => {
  const f = useLocal();
  const t = prog(f, at, dur);
  const o = out === undefined ? 0 : prog(f, out, 10, EASE_OUT);
  const y = (1 - t) * 115 - o * 115;
  return (
    <span style={{ display: "inline-block", overflow: "hidden", verticalAlign: "top", padding: "0.06em 0.08em 0.14em", margin: "-0.06em -0.08em -0.14em", ...style }}>
      <span style={{ display: "inline-block", transform: `translateY(${y}%)` }}>{children}</span>
    </span>
  );
};

/** Words that rise in one after another. */
export const Words: React.FC<{ text: string; at: number; stagger?: number; style?: React.CSSProperties; wordStyle?: (w: string, i: number) => React.CSSProperties | undefined }> = ({
  text,
  at,
  stagger = 1.5,
  style,
  wordStyle,
}) => {
  const words = text.split(" ");
  return (
    <span style={style}>
      {words.map((w, i) => (
        <React.Fragment key={i}>
          <MaskReveal at={at + i * stagger} dur={11} style={wordStyle?.(w, i)}>
            {w}
          </MaskReveal>
          {i < words.length - 1 ? " " : null}
        </React.Fragment>
      ))}
    </span>
  );
};

/** Text that types in at `cps` characters per frame. */
export function typed(text: string, frame: number, at: number, cps = 2): string {
  const n = Math.max(0, Math.floor((frame - at) * cps));
  return text.slice(0, n);
}

export const Caret: React.FC<{ color: string; height?: string }> = ({ color, height = "1em" }) => {
  const f = useLocal();
  return (
    <span
      style={{
        display: "inline-block",
        width: 3,
        height,
        marginLeft: 2,
        verticalAlign: "-0.12em",
        background: color,
        opacity: Math.floor(f / 8) % 2 === 0 ? 1 : 0.15,
      }}
    />
  );
};

/** A tick that draws itself inside a filled circle. */
export const Check: React.FC<{ at: number; size?: number; color?: string; fg?: string }> = ({ at, size = 34, color = C.ownInsert, fg = "#fff" }) => {
  const f = useLocal();
  const s = pop(f, at, 260, 12);
  const d = prog(f, at + 2, 8);
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ transform: `scale(${s})`, flexShrink: 0 }}>
      <circle cx={12} cy={12} r={12} fill={color} />
      <path d="M7 12.5l3.2 3.2L17 9" stroke={fg} strokeWidth={2.4} fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={16} strokeDashoffset={16 * (1 - d)} />
    </svg>
  );
};

export const Cross: React.FC<{ at: number; size?: number; color?: string }> = ({ at, size = 34, color = C.signal }) => {
  const f = useLocal();
  const s = pop(f, at, 260, 12);
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ transform: `scale(${s})`, flexShrink: 0 }}>
      <circle cx={12} cy={12} r={11} fill="none" stroke={color} strokeWidth={2} />
      <path d="M8.5 8.5l7 7M15.5 8.5l-7 7" stroke={color} strokeWidth={2.2} strokeLinecap="round" />
    </svg>
  );
};

export const Chip: React.FC<{ color: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ color, children, style }) => (
  <span
    style={{
      ...monoLabel,
      fontSize: 15,
      color,
      border: `1.5px solid ${color}`,
      borderRadius: 999,
      padding: "4px 12px 3px",
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {children}
  </span>
);

/** Left column of every feature scene: step number, serif title, one-line caption. */
export const StepTitle: React.FC<{
  n: string;
  title: React.ReactNode;
  caption: React.ReactNode;
  dark?: boolean;
  at?: number;
  kicker?: string;
  titleSize?: number;
}> = ({ n, title, caption, dark = false, at = 0, kicker, titleSize = 132 }) => {
  const f = useLocal();
  const line = prog(f, at, 16);
  return (
    <div style={{ position: "absolute", left: 120, top: 210, width: 600 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <MaskReveal at={at}>
          <span style={{ ...monoLabel, fontSize: 22, color: dark ? C.signal : C.signalInk }}>{n}</span>
        </MaskReveal>
        <div style={{ height: 1.5, width: 120 * line, background: dark ? C.darkRule : C.ink, opacity: dark ? 1 : 0.25 }} />
        {kicker ? (
          <MaskReveal at={at + 3}>
            <span style={{ ...monoLabel, fontSize: 16, color: dark ? C.darkMuted : C.muted }}>{kicker}</span>
          </MaskReveal>
        ) : null}
      </div>
      <div style={{ fontFamily: F.serif, fontSize: titleSize, lineHeight: 0.98, letterSpacing: "-0.035em", color: dark ? C.darkText : C.ink, marginTop: 28 }}>
        {title}
      </div>
      <div style={{ fontFamily: F.sans, fontSize: 31, lineHeight: 1.35, color: dark ? C.darkMuted : C.muted, marginTop: 34, maxWidth: 560 }}>{caption}</div>
    </div>
  );
};
