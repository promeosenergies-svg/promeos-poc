/**
 * Playwright config — visual-grammar regression suite.
 *
 * Activable Phase 3 du Sprint Grammaire :
 *   npm i -D @playwright/test
 *   npx playwright test --config=frontend/tests/visual-grammar/playwright.config.ts
 *
 * Baselines : ./__snapshots__/baseline-{slug}-{viewport}.png
 * Tolérance : 0,5 % (cf. baseline.spec.ts).
 */

import { defineConfig, devices } from '@playwright/test';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';

export default defineConfig({
  testDir: '.',
  testMatch: /baseline\.spec\.ts$/,
  snapshotPathTemplate: '{testDir}/__snapshots__/{arg}{ext}',
  timeout: 60_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '.playwright-report' }]],
  use: {
    baseURL: FRONTEND_URL,
    headless: true,
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium-grammar',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
