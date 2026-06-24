import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config for FinAlly (PLAN.md §12).
 *
 * Expects the app to already be running (e.g. via `docker compose -f
 * test/docker-compose.test.yml up` or a plain `docker compose up` from the
 * repo root) and reachable at BASE_URL. Defaults to the standard exposed
 * port (8000) on localhost.
 */
const BASE_URL = process.env.BASE_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
