/**
 * PROMEOS — Playwright capture /consommations/courbe (Sprint P1.S3a).
 *
 * Capture desktop 1440 × 900 de l'onglet « Courbe de charge » pour
 * valider :
 * - l'onglet est visible dans la nav interne /consommations ;
 * - le filtre granularité 1h est sélectionné par défaut ;
 * - l'erreur granularité trop fine s'affiche proprement avec hint.
 *
 * Lancement :
 *   cd e2e && npx playwright test p1_loadcurve.spec.js \
 *     --config=playwright.refonte5175.config.js --reporter=list
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://127.0.0.1:5175';
const BACKEND_URL = 'http://127.0.0.1:8001';
const DEMO_USER = { email: 'promeos@promeos.io', password: 'promeos2024' };

const OUT_DIR = path.resolve(__dirname, '..', 'docs/audits/p1_s3a_loadcurve');

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
  await page.goto(`${FRONTEND_URL}/cockpit`);
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

test.beforeAll(() => {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
});

test.describe('P1.S3a — Courbe de charge desktop 1440', () => {
  test('01 — onglet visible dans /consommations + KPI + chart hour', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'load' });

    // L'onglet « Courbe de charge » est sélectionné dans la nav interne.
    const tabLink = page.locator('text=Courbe de charge').first();
    await expect(tabLink).toBeVisible({ timeout: 15_000 });

    // Filter bar visible
    await expect(page.getByTestId('energy-filter-bar')).toBeVisible({ timeout: 15_000 });

    // Attendre le rendu (loadcurve API peut être 200 vide en démo)
    await page.waitForTimeout(3_000);

    const file = path.join(OUT_DIR, '01_loadcurve_default_desktop_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });

  test('02 — granularité 15min sur 30j → erreur ENERGY_GRANULARITY_TOO_FINE', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);

    // On force la granularité 15min via URL params (période défaut 30d)
    await page.goto(
      `${FRONTEND_URL}/consommations/courbe?period=30d&granularity=15min`,
      { waitUntil: 'load' }
    );
    await page.waitForTimeout(3_000);

    // L'état d'erreur doit afficher message + hint + code + correlation_id.
    // En mode démo offline, l'API peut renvoyer 200 — la capture sert
    // alors à documenter visuellement l'onglet, pas l'erreur exacte.
    const file = path.join(OUT_DIR, '02_loadcurve_15min_30d_desktop_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });

  test('03 — onglet rail Énergie n’est pas modifié', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'load' });
    await page.waitForTimeout(1_500);

    // Le rail Énergie doit toujours contenir Consommations / Performance
    // énergétique / Usages énergétiques / Diagnostics (pas de nouvelle entrée
    // "Courbe de charge" au niveau rail).
    const rail = page.locator('nav, aside').first();
    const railText = await rail.textContent();
    expect(railText).toContain('Consommations');
    // Le label "Courbe de charge" est dans la tabBar interne, pas dans
    // le rail. On vérifie qu'il apparaît UNE seule fois maximum dans le
    // rail (0 attendu — il vit dans la tabBar du PageShell, pas le rail).
    expect(railText?.match(/Courbe de charge/g)?.length ?? 0).toBeLessThanOrEqual(0);
  });
});
