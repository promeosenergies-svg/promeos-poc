/**
 * PROMEOS — Config Playwright Sprint P2.2 cross-links transverses.
 * Réutilise auth.setup.spec.js pour storageState partagé.
 */
import { defineConfig } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STORAGE_STATE = path.join(__dirname, '.auth', 'promeos-user.json');

export default defineConfig({
  testDir: '.',
  testMatch: /(auth\.setup|p2_energy_cross_links)\.spec\.js$/,
  timeout: 60_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5175',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.spec\.js$/ },
    {
      name: 'chromium',
      use: { browserName: 'chromium', storageState: STORAGE_STATE },
      dependencies: ['setup'],
      testMatch: /p2_energy_cross_links\.spec\.js$/,
    },
  ],
});
