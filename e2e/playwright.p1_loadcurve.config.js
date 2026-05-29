/**
 * PROMEOS — Config Playwright Sprint P1.S3a (Courbe de charge).
 */
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /p1_loadcurve\.spec\.js$/,
  timeout: 60_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5175',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
