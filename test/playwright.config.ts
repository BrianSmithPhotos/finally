import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for FinAlly E2E (PLAN.md §12).
 *
 * The app under test is the fully-integrated FastAPI server that also serves the
 * Next.js static export from backend/static. Point BASE_URL at a running
 * instance (default http://localhost:8000).
 *
 * Run the app with LLM_MOCK=true and a throwaway DB so the suite starts from a
 * clean seeded state. See README in this directory and docker-compose.test.yml.
 */
const BASE_URL = process.env.BASE_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './tests',
  // SSE / async-resync scenarios need a little headroom.
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // One worker: the single-user backend has shared global state (one portfolio,
  // one watchlist), so tests must not race each other.
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'results.json' }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
