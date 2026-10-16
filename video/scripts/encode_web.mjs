// Turn the master render (out/ownit-intro.mp4) into web-ready files for a portfolio page,
// using the ffmpeg that ships with Remotion (no system ffmpeg needed).
//   media/ownit-intro-1080p.mp4   H.264, fast start, for <video> everywhere
//   media/ownit-intro-720p.mp4    smaller, for phones
//   media/ownit-intro-1080p.webm  VP9 + Opus, smaller still in Chrome/Firefox
//   media/ownit-intro-poster.jpg  end card, for the poster attribute
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const master = path.join(root, "out/ownit-intro.mp4");
const tl = JSON.parse(readFileSync(path.join(root, "src/timeline.json"), "utf8"));
const posterAt = ((tl.durationBeats * tl.beatFrames) / tl.fps - 0.7).toFixed(2); // end card, fully revealed
const web = path.join(root, "media");
if (!existsSync(master)) {
  console.error("out/ownit-intro.mp4 not found. Run `npm run render` first.");
  process.exit(1);
}
if (statSync(master).mtimeMs < statSync(path.join(root, "public/soundtrack.wav")).mtimeMs) {
  console.error("out/ownit-intro.mp4 is older than the soundtrack. Run `npm run render` again first.");
  process.exit(1);
}
mkdirSync(web, { recursive: true });

function ffmpeg(args) {
  const r = spawnSync("npx", ["remotion", "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", ...args], {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

const out = (name) => path.join(web, name);

ffmpeg(["-i", master, "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
  "-c:a", "aac", "-b:a", "192k", out("ownit-intro-1080p.mp4")]);
ffmpeg(["-i", master, "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
  "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "160k", out("ownit-intro-720p.mp4")]);
ffmpeg(["-i", master, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2",
  "-c:a", "libopus", "-b:a", "128k", out("ownit-intro-1080p.webm")]);
ffmpeg(["-ss", posterAt, "-i", master, "-frames:v", "1", "-q:v", "2", out("ownit-intro-poster.jpg")]);

for (const f of ["ownit-intro-1080p.mp4", "ownit-intro-720p.mp4", "ownit-intro-1080p.webm", "ownit-intro-poster.jpg"]) {
  console.log(`${f.padEnd(26)} ${(statSync(out(f)).size / 1024 / 1024).toFixed(2)} MB`);
}
