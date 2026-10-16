import data from "./timeline.json";

/**
 * One beat grid for picture and sound. scripts/make_soundtrack.py reads the same JSON, so a cue
 * moved here moves its sound effect too. Cue times are in beats, relative to the scene's cut.
 */
export const FPS = data.fps;
export const WIDTH = data.width;
export const HEIGHT = data.height;
export const BEAT = data.beatFrames;
export const DURATION = data.durationBeats * BEAT;

export type SceneId = (typeof data.scenes)[number]["id"];

export function scene(id: SceneId): { start: number; len: number } {
  const s = data.scenes.find((x) => x.id === id);
  if (!s) throw new Error(`unknown scene ${id}`);
  return { start: s.start * BEAT, len: s.beats * BEAT };
}

/** A cue's frame, relative to the start of its scene. */
export function cue(id: SceneId, name: string): number {
  const cues = (data.cues as unknown as Record<string, Record<string, [number, string | null]>>)[id];
  const c = cues?.[name];
  if (!c) throw new Error(`unknown cue ${id}.${name}`);
  return Math.round(c[0] * BEAT);
}

export const beats = (n: number) => Math.round(n * BEAT);

export const SCENE_ORDER = data.scenes.map((s) => s.id as SceneId);

export function sceneAt(frame: number): SceneId {
  let current = SCENE_ORDER[0];
  for (const id of SCENE_ORDER) if (frame >= scene(id).start) current = id;
  return current;
}
