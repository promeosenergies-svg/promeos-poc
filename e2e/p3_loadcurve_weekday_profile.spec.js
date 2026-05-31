/**
 * PROMEOS — Playwright capture /consommations/courbe (Sprint P3.1).
 *
 * Sprint P3.1 ajoute sous l'onglet « Courbe de charge » :
 * - section « Pics de puissance » (top_peaks backend, plus de
 *   placeholder « Top pics indisponible ») ;
 * - section « Profil moyen par jour » (7 courbes Lun→Dim) ;
 * - section « Répartition par jour » (7 barres + comparaison
 *   ouvrés/week-end).
 *
 * Capture desktop 1440 × 900 + assertions FR métier :
 * - « Profil moyen par jour » visible ;
 * - « Pics de puissance » visible (et plus « Top pics indisponible ») ;
 * - rail Énergie inchangé ;
 * - libellé site = nom métier (pas « Site #<id> »).
 *
 * Lancement :
 *   cd e2e && npx playwright test p3_loadcurve_weekday_profile.spec.js \
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

const OUT_DIR = path.resolve(__dirname, '..', 'docs/audits/p3_1_loadcurve_weekday');

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
  // Force un scope site sélectionné (org=1, site=1) pour P3.1 — sinon
  // la vue affiche « Aucun site sélectionné ». Le shape correspond à
  // `STORAGE_KEY = 'promeos_scope'` dans ScopeContext.
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

test.describe('P3.1 — Profil moyen par jour + Pics de puissance desktop 1440', () => {
  test('01 — sections P3.1 visibles sous /consommations/courbe', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=90d&granularity=day`, { waitUntil: 'load' });
    await page.waitForTimeout(3_000);

    const file = path.join(OUT_DIR, '01_loadcurve_weekday_default_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });

  test('02 — sections P3.1 visibles : « Pics de puissance » + « Profil moyen par jour » + 7 jours', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    // period=90d garantit que le seed démo expose des données mesurées
    // pour le site 1 (cf. live curl P3.1).
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=90d&granularity=day`, { waitUntil: 'load' });
    await page.waitForTimeout(4_000);

    const body = (await page.locator('body').textContent()) || '';

    // Sections P3.1 visibles
    expect(body).toContain('Pics de puissance');
    expect(body).toContain('Profil moyen par jour');
    expect(body).toContain('Répartition par jour');

    // 7 jours Lun → Dim affichés (issue de weekday_decomposition / overlay)
    for (const day of ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']) {
      expect(body).toContain(day);
    }

    // Plus aucun wording « Top pics »
    expect(body).not.toContain('Top pics indisponible');
    expect(body).not.toContain('Top pics');

    // Pas d'identifiant technique « Site #<num> »
    expect(body.match(/Site #\d+/)?.length ?? 0).toBe(0);

    // Aucune erreur rouge ENERGY_* visible
    expect(body).not.toContain('ENERGY_GRANULARITY_TOO_FINE');
    expect(body).not.toContain('ENERGY_SCOPE_INVALID');

    // Cross-link Centre d'action présent
    expect(body).toContain("Créer une action d'analyse");
  });

  test('03 — rail Énergie inchangé après P3.1', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'load' });
    await page.waitForTimeout(1_500);

    const rail = page.locator('nav, aside').first();
    const railText = await rail.textContent();
    expect(railText).toContain('Consommations');
    // Pas d'entrée rail « Profil moyen par jour » / « Pics de puissance ».
    expect((railText || '').match(/Profil moyen par jour/g)?.length ?? 0).toBe(0);
    expect((railText || '').match(/Pics de puissance/g)?.length ?? 0).toBe(0);
  });

  test('04 — capture pleine page large 1440 documentaire', async ({ page }) => {
    // Viewport vertical large pour capturer toutes les sections P3.1
    // (KPI + chart + Pics + Profil moyen + Répartition + cross-link)
    // dans une seule capture documentaire.
    await page.setViewportSize({ width: 1440, height: 2400 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/consommations/courbe?period=90d&granularity=day`, { waitUntil: 'load' });
    await page.waitForTimeout(4_000);

    const file = path.join(OUT_DIR, '04_loadcurve_weekday_doc_1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });
});
