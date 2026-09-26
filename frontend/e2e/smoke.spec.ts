import { expect, test } from "@playwright/test";

/**
 * Smoke test: paste a draft and go through all five steps.
 * Humanize → Walkthrough → Make it yours → Prove it → Export.
 */
test("the 5-step flow works end to end", async ({ page }) => {
  // new document from the sample draft
  await page.goto("/workspace");
  await page.getByRole("button", { name: /New document/ }).first().click();
  await page.getByText("Use a sample draft").click();
  await page.getByRole("button", { name: "Start" }).click();
  await page.waitForURL(/\/workspace\/.+/);

  // 1 · Humanize: suggest rewrites and accept them all
  await page.getByRole("button", { name: "Suggest rewrites" }).click();
  await page.getByRole("button", { name: "Accept all" }).click();
  await expect(page.locator('.ProseMirror [data-origin="engine"]').first()).toBeVisible();
  await page.getByRole("tab", { name: /Doctor/ }).click();
  await expect(page.getByRole("list", { name: "Checks" })).toBeVisible();

  // 2 · Walkthrough: mark every paragraph "Got it" with the keyboard
  await page.locator("nav[aria-label=Steps]").getByRole("button", { name: /Walkthrough/ }).click();
  const cards = page.locator("article[data-paragraph]");
  await expect(cards.first()).toBeVisible();
  const n = await cards.count();
  await cards.first().focus();
  for (let i = 0; i < n; i++) await page.keyboard.press("g");
  await expect(page.getByRole("progressbar", { name: "Paragraphs reviewed" })).toHaveAttribute("aria-valuenow", "100");

  // 3 · Make it yours: answer the first generic spot
  await page.locator("nav[aria-label=Steps]").getByRole("button", { name: /Make it yours/ }).click();
  const answer = page.getByLabel("Your answer");
  await answer.fill("For example, in our lab the drip line used 30% less water after we added the sensor");
  await page.getByRole("button", { name: /^Insert/ }).click();
  await expect(page.locator('.ProseMirror [data-origin="student_insert"]').first()).toBeVisible();

  // 4 · Prove it: answer the quiz, do a teach-back
  await page.locator("nav[aria-label=Steps]").getByRole("button", { name: /Prove it/ }).click();
  await expect(page.getByRole("button", { name: /Check answers/ })).toBeVisible();
  for (const radio of await page.getByRole("radio", { name: "true" }).all()) await radio.click();
  for (const input of await page.getByLabel("Missing term").all()) await input.fill("sensor");
  await page.getByRole("button", { name: /Check answers/ }).click();
  await expect(page.getByRole("button", { name: /Try again/ })).toBeVisible();
  await page.getByRole("tab", { name: "Teach-back" }).click();
  await page
    .getByLabel("Explain it to a friend")
    .fill(
      "We built a smart irrigation controller around an ESP32. A capacitive soil moisture sensor measures the water content, " +
        "and a relay switches the pump when the soil is dry. Water use fell compared with manual watering.",
    );
  await page.getByRole("button", { name: /Check my explanation/ }).click();
  await expect(page.getByRole("region", { name: "Teach-back result" })).toBeVisible();

  // 5 · Export: locked until the checks pass; switch the gate off for the smoke test
  await page.locator("nav[aria-label=Steps]").getByRole("button", { name: /Export/ }).click();
  await page.getByRole("switch", { name: "Understanding gate" }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Download .docx/ }).click();
  expect((await download).suggestedFilename()).toMatch(/\.docx$/);
});
