/**
 * AUDIT — 4 chips réglementaires /conformite (dt, bacs, aper, audit-sme).
 *
 * Vérifie que chaque chip clique active le filtre `?regulation=<key>`
 * dans l'URL et que la page ne casse pas.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://127.0.0.1:5175';
const BACKEND_URL = 'http://127.0.0.1:8001';
const DEMO_USER = { email: 'promeos@promeos.io', password: 'promeos2024' };
const OUT_DIR = path.resolve(__dirname, '..', 'docs/audits/conformite_chips');

const CHIPS = [
  { key: 'dt', label: 'Décret Tertiaire' },
  { key: 'bacs', label: 'BACS' },
  { key: 'aper', label: 'APER' },
  { key: 'audit-sme', label: 'SMÉ / BEGES' },
];

let _cachedToken = null;

async function login(page) {
  if (!_cachedToken) {
    const res = await page.request.post(`${BACKEND_URL}/api/auth/login`, {
      data: DEMO_USER,
    });
    if (res.ok()) _cachedToken = (await res.json()).access_token;
  }
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded' });
  if (_cachedToken) {
    await page.evaluate((t) => localStorage.setItem('promeos_token', t), _cachedToken);
  }
  await page.evaluate(() => {
    localStorage.setItem(
      'promeos_scope',
      JSON.stringify({ orgId: 1, entiteId: null, portefeuilleId: null, siteId: 1 })
    );
  });
  await page.goto(`${FRONTEND_URL}/cockpit`);
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

test.beforeAll(() => {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
});

test.describe('AUDIT 4 chips réglementaires /conformite', () => {
  test('01 — chips visibles + capture baseline', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 2200 });
    await login(page);
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto(`${FRONTEND_URL}/conformite`, { waitUntil: 'load' });
    await page.waitForTimeout(4_000);

    const bar = page.getByTestId('regulation-chips-bar');
    await expect(bar).toBeVisible({ timeout: 15_000 });

    const body = (await page.locator('body').textContent()) || '';
    console.log('CHIPS visibles (présence textContent):');
    for (const chip of CHIPS) {
      const present = body.includes(chip.label);
      console.log(`  ${chip.key}: ${present ? 'OK' : 'MANQUE'}`);
    }

    await page.screenshot({ path: path.join(OUT_DIR, '01_baseline_1440.png'), fullPage: true });
    console.log(`Console errors baseline: ${consoleErrors.length}`);
    if (consoleErrors.length) console.log(consoleErrors.slice(0, 5));
  });

  for (const chip of CHIPS) {
    test(`02 — chip ${chip.key} (${chip.label}) clic + URL + résultat`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 2200 });
      await login(page);
      const consoleErrors = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      await page.goto(`${FRONTEND_URL}/conformite`, { waitUntil: 'load' });
      await page.waitForTimeout(3_000);

      const chipEl = page.getByTestId(`regulation-chip-${chip.key}`);
      const exists = await chipEl.count();
      console.log(`Chip data-testid="regulation-chip-${chip.key}" existe: ${exists}`);
      expect(exists, `chip ${chip.key} doit exister`).toBeGreaterThan(0);

      await chipEl.first().click({ timeout: 5_000 });
      await page.waitForTimeout(2_500);

      const url = page.url();
      console.log(`URL après clic chip ${chip.key}: ${url}`);
      expect(url, `URL doit contenir ?regulation=${chip.key}`).toContain(`regulation=${chip.key}`);

      const body = (await page.locator('body').textContent()) || '';
      // L'app ne doit pas crasher
      expect(body.length, `chip ${chip.key} casse la page`).toBeGreaterThan(500);
      expect(body).not.toContain('Page introuvable');
      expect(body).not.toContain('Application Error');

      await page.screenshot({
        path: path.join(OUT_DIR, `02_chip_${chip.key}_1440.png`),
        fullPage: true,
      });
      console.log(`Console errors chip ${chip.key}: ${consoleErrors.length}`);
      if (consoleErrors.length) console.log(consoleErrors.slice(0, 3));
    });
  }
});
