/**
 * PROMEOS — Playwright config (Sprint infra-stabilisation 2026-05-29).
 *
 * 2 projects :
 *   - `setup`   : tourne UNE fois en début de run, exécute `auth.setup.spec.js`
 *                 et persiste `storageState` dans `.auth/promeos-user.json`.
 *   - `chromium`: tous les autres tests, dépend du `setup` et restaure le
 *                 storageState → AUCUN test ne refait de login UI ni d'appel
 *                 API login → plus de rate-limit consécutif.
 *
 * Tradeoff : `setup` ne tourne qu'une fois par invocation Playwright ; si
 * le token expire pendant un long run (TTL ~25 min), les tests ultérieurs
 * échoueront 401. Le smoke postmerge tourne en < 1 min, donc safe.
 */
import { defineConfig } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STORAGE_STATE = path.join(__dirname, '.auth', 'promeos-user.json');

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.js',
  timeout: 30_000,
  retries: 1,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    // 1. Setup : login one-shot, sauvegarde storageState.
    {
      name: 'setup',
      testMatch: /auth\.setup\.spec\.js/,
    },
    // 2. Tests applicatifs : héritent du storageState produit par setup.
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        storageState: STORAGE_STATE,
      },
      dependencies: ['setup'],
      testIgnore: /auth\.setup\.spec\.js/,
    },
  ],
});
