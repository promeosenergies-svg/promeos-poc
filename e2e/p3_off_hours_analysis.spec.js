/**
 * PROMEOS — Playwright /consommations/courbe (Sprint Énergie P3.2).
 *
 * Sprint P3.2 ajoute la section « Consommation hors horaires » sous
 * /consommations/courbe :
 * - 4 KPI (off_hours_kwh, off_hours_share_pct, weekend_off_hours_kwh,
 *   night_baseload_kw) avec provenance ;
 * - résumé horaires déclarés + 7 jours ;
 * - top créneaux hors horaires ;
 * - recommandations FR métier + CTA Centre d'action.
 *
 * Microcopy : « Consommation hors horaires », « Horaires déclarés »,
 * « Top créneaux hors horaires », « Créer une action d'analyse ».
 * Interdit : Business hours / Off hours / Opening hours.
 *
 * Lancement :
 *   cd e2e && npx playwright test p3_off_hours_analysis.spec.js \
 *     --config=playwright.p3_off_hours_analysis.config.js
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://127.0.0.1:5175';
const BACKEND_URL = 'http://127.0.0.1:8001';
const DEMO_USER = { email: 'promeos@promeos.io', password: 'promeos2024' };

const OUT_DIR = path.resolve(__dirname, '..', 'docs/audits/p3_2_off_hours');

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
  // Force scope site=1 (Siège HELIOS Paris, horaires déclarés Lun-Ven 08-19h)
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

test.describe('P3.2 — Consommation hors horaires desktop 1440', () => {
  test('01 — section « Consommation hors horaires » visible', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    // period=30d + hour pour aligner sur le seed démo (avril 2026).
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=30d&granularity=hour`, {
      waitUntil: 'load',
    });
    await page.waitForTimeout(5_000);

    const card = page.getByTestId('off-hours-analysis-card');
    await expect(card).toBeVisible({ timeout: 15_000 });

    const file = path.join(OUT_DIR, '01_off_hours_default_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });

  test('02 — microcopy FR + KPI + CTA Centre d\'action', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=30d&granularity=hour`, {
      waitUntil: 'load',
    });
    await page.waitForTimeout(5_000);

    const body = (await page.locator('body').textContent()) || '';

    expect(body).toContain('Consommation hors horaires');
    expect(body).toContain('Comparez la consommation mesurée aux horaires déclarés');

    // Microcopy anglais interdit
    expect(body).not.toContain('Business hours');
    expect(body).not.toContain('Off hours');
    expect(body).not.toContain('Opening hours');

    // Aucune erreur rouge ENERGY_*
    expect(body).not.toContain('ENERGY_SCOPE_INVALID');
    expect(body).not.toContain('ENERGY_OPENING_HOURS_MISSING');

    // CTA Centre d'action présent (au moins via cross-link existant)
    expect(body).toContain("Créer une action d'analyse");
  });

  test('03 — rail Énergie inchangé après P3.2', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'load' });
    await page.waitForTimeout(1_500);

    const rail = page.locator('nav, aside').first();
    const railText = await rail.textContent();
    expect(railText).toContain('Consommations');
    expect((railText || '').match(/Consommation hors horaires/g)?.length ?? 0).toBe(0);
    expect((railText || '').match(/Horaires d'ouverture/g)?.length ?? 0).toBe(0);
  });

  test('04 — capture pleine page documentaire 1440', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 3200 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=30d&granularity=hour`, {
      waitUntil: 'load',
    });
    await page.waitForTimeout(5_000);

    const file = path.join(OUT_DIR, '04_off_hours_doc_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });
});
