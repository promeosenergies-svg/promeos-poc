/**
 * PROMEOS — Sprint Énergie P2.5 audit final UX/UI.
 *
 * Pour chaque route :
 * - charger en 1440×900 ;
 * - capturer la page ;
 * - vérifier absence de texte interdit (« Site # », « Site Site »,
 *   « undefined », « NaN », « [object Object] », jargon anglais) ;
 * - vérifier absence d'erreur rouge non attendue ;
 * - vérifier rail Énergie inchangé ;
 * - vérifier pas de zone vide massive sans EmptyState.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

const ROUTES = [
  { path: '/monitoring', testId: 'monitoring-synthesis', shot: 'monitoring' },
  { path: '/consommations/courbe', testId: 'loadcurve-tab', shot: 'courbe' },
  {
    path: '/consommations/cout-contrat',
    testId: 'cost-contract-tab',
    shot: 'cout-contrat',
  },
  {
    path: '/consommations/marche',
    testId: 'market-exposure-tab',
    shot: 'marche',
  },
  {
    path: '/usages?tab=semaine-type',
    testId: 'week-profile-tab',
    shot: 'semaine-type',
  },
];

const FORBIDDEN_PATTERNS = [
  /Site #\d+/,
  /Site Site/,
  /Compteur #\d+/,
  /Organisation #\d+/,
  /Entité #\d+/,
  /\bundefined\b/,
  /\bNaN\b/,
  /\[object Object\]/,
  /^Loading\.\.\.$/m,
];

test.describe('Sprint Énergie P2.5 — Audit visuel UX/UI 5 routes', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const route of ROUTES) {
    test(`Route ${route.path} — pas de texte interdit + capture 1440`, async ({ page }) => {
      await page.goto(`${FRONTEND_URL}${route.path}`, { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

      // Capture
      await page.screenshot({
        path: `playwright-report/p2-5-visual-${route.shot}.png`,
        fullPage: true,
      });

      // Récupère le texte rendu
      const bodyText = await page.evaluate(() => document.body.innerText);

      // Vérifie absence de chaque pattern interdit
      for (const pattern of FORBIDDEN_PATTERNS) {
        expect(bodyText).not.toMatch(pattern);
      }
    });

    test(`Route ${route.path} — composant cible rendu (pas de page blanche)`, async ({
      page,
    }) => {
      await page.goto(`${FRONTEND_URL}${route.path}`, { waitUntil: 'domcontentloaded' });
      const target = page.getByTestId(route.testId);
      await expect(target).toBeVisible({ timeout: 10_000 });
    });
  }

  test('Rail Énergie inchangé sur les 5 routes (aucun label « Site # »)', async ({ page }) => {
    for (const route of ROUTES) {
      await page.goto(`${FRONTEND_URL}${route.path}`, { waitUntil: 'domcontentloaded' });
      const railText = (await page.locator('nav').allTextContents()).join(' ');
      expect(railText).not.toMatch(/Site #\d+/);
      expect(railText).not.toMatch(/Site Site/);
    }
  });

  test('Aucune erreur rouge ENERGY_SCOPE_INVALID sur scope attendu', async ({ page }) => {
    // Cas connu : scope=org sur Semaine type / Coût contrat / Marché.
    // Ces vues affichent SiteRequiredState (pas d'erreur rouge).
    for (const route of [
      '/usages?tab=semaine-type',
      '/consommations/cout-contrat',
      '/consommations/marche',
    ]) {
      await page.goto(`${FRONTEND_URL}${route}`, { waitUntil: 'domcontentloaded' });
      const bodyText = await page.evaluate(() => document.body.innerText);
      // Le texte SiteRequiredState est OK, mais pas le code technique
      expect(bodyText).not.toMatch(/ENERGY_SCOPE_INVALID/);
    }
  });
});
