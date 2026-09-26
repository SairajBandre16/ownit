import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end smoke test of the 5-step flow. Needs the whole stack running
 * (LanguageTool :8010, API :8000, web :3000 — see scripts/dev.ps1), then:  npm run e2e
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 60_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    acceptDownloads: true,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
