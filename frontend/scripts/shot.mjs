// Dev helper: screenshot pages of the running app.
//   node scripts/shot.mjs <outDir> [flow]
// flows: landing | workspace | humanize
import { chromium } from "@playwright/test";

const out = process.argv[2] ?? ".";
const flow = process.argv[3] ?? "landing";
const base = process.env.BASE_URL ?? "http://localhost:3000";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.on("console", (m) => m.type() === "error" && console.log("console:", m.text()));
page.on("pageerror", (e) => console.log("pageerror:", e.message));

async function newSampleDoc() {
  await page.goto(`${base}/workspace`);
  await page.getByRole("button", { name: "New document" }).click();
  await page.getByText("Use a sample draft").click();
  await page.getByRole("button", { name: "Start" }).click();
  await page.waitForURL(/workspace\/.+/);
  await page.waitForTimeout(Number(process.env.WAIT ?? 6000));
}

if (flow === "landing") {
  await page.goto(base);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/landing.png`, fullPage: true });
} else if (flow === "workspace") {
  await newSampleDoc();
  await page.screenshot({ path: `${out}/workspace.png` });
  if (process.env.HOVER) {
    await page.locator(".mark-issue").first().hover();
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${out}/hover.png` });
  }
} else if (flow === "voice") {
  const fs = await import("node:fs");
  const stu = fs.readFileSync("../backend/tests/eval/paragraphs_student.txt", "utf8").split(/\r?\n/).filter(Boolean);
  const ai = fs.readFileSync("../backend/tests/eval/paragraphs_ai.txt", "utf8").split(/\r?\n/).filter(Boolean);
  await page.goto(`${base}/voice`);
  await page.getByLabel("Sample 1").fill(stu.slice(0, 8).join(" "));
  await page.getByRole("button", { name: /Build my fingerprint|Rebuild fingerprint/ }).click();
  await page.waitForSelector("text=Your fingerprint", { timeout: 60000 });
  await page.getByLabel("Text to compare").fill(ai.slice(0, 3).join(" "));
  await page.getByRole("button", { name: "Compare with my voice" }).click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${out}/voice.png`, fullPage: true });
} else if (flow === "humanize") {
  await newSampleDoc();
  await page.getByRole("button", { name: "Suggest rewrites" }).click();
  await page.waitForSelector(".mark-change", { timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/humanize-1.png` });
  await page.mouse.click(5, 500);
  for (const k of ["a", "a", "r", "a"]) {
    await page.keyboard.press(k);
    await page.waitForTimeout(300);
  }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${out}/humanize-2.png` });
  await page.getByRole("button", { name: "Accept all" }).click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${out}/humanize-3.png` });
  await page.reload();
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${out}/humanize-reload.png` });
}
await browser.close();
