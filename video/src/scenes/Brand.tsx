import React from "react";
import { AbsoluteFill } from "remotion";
import { prog, shake, useLocal } from "../anim";
import { LogoMark, MaskReveal, Paper, Words } from "../components/primitives";
import { cue } from "../timeline";
import { C, F } from "../theme";

export const Brand: React.FC = () => {
  const f = useLocal();
  const hit = cue("brand", "logo");
  const sub = cue("brand", "subline");
  const s = shake(f, hit, 12, 9);
  const flash = 1 - prog(f, hit, 8);
  const zoom = 1.12 - 0.12 * prog(f, hit, 16) + 0.02 * prog(f, hit + 16, 40);

  return (
    <AbsoluteFill>
      <Paper dark />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 46%, rgba(255,90,31,${0.35 * flash}) 0%, transparent 55%)`,
        }}
      />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", transform: `translate(${s.x}px, ${s.y}px) scale(${zoom})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 34 }}>
          <LogoMark size={190} at={hit} ink={C.darkText} muted={C.darkMuted} />
          <div style={{ fontFamily: F.serif, fontSize: 210, lineHeight: 1, letterSpacing: "-0.045em", color: C.darkText }}>
            <MaskReveal at={hit + 2} dur={10}>
              Own
            </MaskReveal>
            <MaskReveal at={hit + 5} dur={10}>
              <em style={{ color: C.signal }}>It</em>
            </MaskReveal>
          </div>
        </div>
        <div style={{ fontFamily: F.sans, fontSize: 40, color: C.darkMuted, marginTop: 46, letterSpacing: "-0.005em" }}>
          <Words text="Five steps from AI draft to defensible." at={sub} stagger={1.2} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
