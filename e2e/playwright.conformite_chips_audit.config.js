import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /conformite_chips_audit\.spec\.js$/,
  timeout: 90_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5175',
    headless: true,
    viewport: { width: 1440, height: 2200 },
    ignoreHTTPSErrors: true,
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
