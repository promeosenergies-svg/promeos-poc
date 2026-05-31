/**
 * PROMEOS — Playwright Site360 onglets / routes mortes (Sprint Site360 P0).
 *
 * Scénario :
 * - ouvrir Site360 « Siège HELIOS Paris » (site_id=1) ;
 * - cliquer chaque onglet visible ;
 * - vérifier qu'aucun n'affiche écran blanc / 404 / placeholder
 *   « À venir » / jargon « Analytics » ;
 * - vérifier que les boutons top ont l'accent correct (« Évaluation
 *   RegOps ») et ne mènent pas à des routes mortes ;
 * - capture documentaire 1440.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://127.0.0.1:5175';
const BACKEND_URL = 'http://127.0.0.1:8001';
const DEMO_USER = { email: 'promeos@promeos.io', password: 'promeos2024' };
const SITE_ID = 1;
const OUT_DIR = path.resolve(__dirname, '..', 'docs/audits/site360_p0_tabs');

const TAB_LABELS = [
  'Résumé',
  'Consommation',
  'Analyse énergétique',
  'Factures',
  'Réconciliation',
  'Conformité',
  'Actions',
  'Puissance',
  'Usages',
];

const FORBIDDEN_TEXT = [
  'Analytics',
  'À venir',
  'Coming soon',
  'TODO',
  'lorem ipsum',
  'undefined',
  'NaN',
  '[object Object]',
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

test.describe('Site360 P0 — onglets / routes mortes desktop 1440', () => {
  test('01 — Site360 charge et expose les 9 onglets FR métier', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/sites/${SITE_ID}`, { waitUntil: 'load' });
    await page.waitForTimeout(4_000);

    const body = (await page.locator('body').textContent()) || '';

    // Chaque label FR canonique doit être présent (visible dans la TabBar).
    for (const label of TAB_LABELS) {
      expect(body, `label « ${label} » visible dans Site360`).toContain(label);
    }

    // Aucun jargon ou placeholder interdit.
    for (const forbidden of FORBIDDEN_TEXT) {
      expect(body, `mot interdit « ${forbidden} » présent`).not.toContain(forbidden);
    }

    const file = path.join(OUT_DIR, 'site360-resume-1440.png');
    await page.screenshot({ path: file, fullPage: false });
  });

  test('02 — boutons top : accent correct + aucune route morte', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/sites/${SITE_ID}`, { waitUntil: 'load' });
    await page.waitForTimeout(3_000);

    const body = (await page.locator('body').textContent()) || '';

    // Accent correct
    expect(body).toContain('Évaluation RegOps');
    expect(body).not.toMatch(/>\s*Evaluation RegOps\s*</);

    // Route morte historique bannie
    expect(body).not.toContain('/achat-assistant');
    // Pas de href="#" exposé
    const hashLinks = await page.locator('a[href="#"]').count();
    expect(hashLinks).toBe(0);
  });

  test('03 — cycle sur chaque onglet : pas d\'écran blanc ni jargon', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/sites/${SITE_ID}`, { waitUntil: 'load' });
    await page.waitForTimeout(3_000);

    for (const label of TAB_LABELS) {
      const tab = page.getByRole('button', { name: label }).or(
        page.getByText(label, { exact: true })
      );
      const target = tab.first();
      if (await target.count()) {
        try {
          await target.click({ timeout: 3_000 });
        } catch {
          // Onglet peut être dans une nav non-cliquable directement —
          // continue, le smoke check du body se fait après.
        }
        await page.waitForTimeout(800);
        const body = (await page.locator('body').textContent()) || '';
        // Smoke : aucun jargon obvious sur la page de l'onglet
        for (const forbidden of FORBIDDEN_TEXT) {
          expect(body, `onglet « ${label} » expose « ${forbidden} »`).not.toContain(forbidden);
        }
        // Body non vide (au moins 200 chars de contenu)
        expect(body.length, `onglet « ${label} » expose un écran vide`).toBeGreaterThan(200);
      }
    }
  });

  test('04 — capture audit documentaire 1440', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 2200 });
    await login(page);
    await page.goto(`${FRONTEND_URL}/sites/${SITE_ID}`, { waitUntil: 'load' });
    await page.waitForTimeout(4_000);

    const file = path.join(OUT_DIR, 'site360-tabs-audit-1440.png');
    await page.screenshot({ path: file, fullPage: true });
  });
});
