// Render a few frames as PNGs for a quick visual check: node scripts/stills.mjs 60 150 230 ...
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frames = process.argv.slice(2).map(Number);
const serveUrl = await bundle({ entryPoint: path.join(root, "src/index.ts") });
const browser = await openBrowser("chrome");
const composition = await selectComposition({ serveUrl, id: "OwnItIntro", puppeteerInstance: browser });
for (const frame of frames) {
  const output = path.join(root, "out/stills", `f${String(frame).padStart(3, "0")}.png`);
  await renderStill({ composition, serveUrl, frame, output, puppeteerInstance: browser, scale: 0.5 });
  console.log(output);
}
await browser.close({ silent: true });
