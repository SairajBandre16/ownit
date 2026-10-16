import React from "react";
import { Composition } from "remotion";
import { Intro } from "./Intro";
import { DURATION, FPS, HEIGHT, WIDTH } from "./timeline";

export const RemotionRoot: React.FC = () => (
  <Composition id="OwnItIntro" component={Intro} durationInFrames={DURATION} fps={FPS} width={WIDTH} height={HEIGHT} />
);
