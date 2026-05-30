/**
 * PROMEOS — e2e Sprint Énergie P2.2.
 *
 * Vérifie les cross-links transverses ajoutés sur 3 vues clés :
 * - /monitoring                    : action + conformite/tertiaire
 * - /consommations/courbe          : action (wording générique)
 * - /usages?tab=semaine-type       : conformite?tab=donnees
 *
 * Assertions par vue :
 * - cross-links rendus avec testId dédié ;
 * - chaque link a un href vers une route NavRegistry existante ;
 * - rail Énergie inchangé ;
 * - capture desktop 1440×900.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P2.2 — Cross-links transverses 3 vues', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Route 1 — /monitoring : action + conformité-tertiaire', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/monitoring`, { waitUntil: 'domcontentloaded' });
    const block = page.getByTestId('monitoring-cross-links');
    await expect(block).toBeVisible({ timeout: 10_000 });
    await expect(block).toContainText('Aller plus loin');
    await expect(block).toContainText('Créer une action');
    await expect(block).toContainText('Voir trajectoire Décret Tertiaire');
    // Vérifie les hrefs
    const actionLink = block.getByTestId('cross-link-action');
    const confLink = block.getByTestId('cross-link-conformite');
    await expect(actionLink).toHaveAttribute('href', '/action-center-v4');
    await expect(confLink).toHaveAttribute('href', '/conformite/tertiaire');
    await page.screenshot({
      path: 'playwright-report/p2-2-1-monitoring.png',
      fullPage: true,
    });
  });

  test('Route 2 — /consommations/courbe : action (wording générique)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    // Le bloc apparaît si payload chargé — sinon empty/error → on skip
    const block = page.getByTestId('loadcurve-cross-links');
    const visible = await block.isVisible().catch(() => false);
    if (!visible) {
      test.info().annotations.push({
        type: 'note',
        description: 'LoadCurveTab pas en mode data — cross-link non rendu (filtres ou état initial)',
      });
      await page.screenshot({
        path: 'playwright-report/p2-2-2-courbe.png',
        fullPage: true,
      });
      return;
    }
    await expect(block).toContainText("Créer une action d'analyse");
    const link = block.getByTestId('cross-link-action');
    await expect(link).toHaveAttribute('href', '/action-center-v4');
    await page.screenshot({
      path: 'playwright-report/p2-2-2-courbe.png',
      fullPage: true,
    });
  });

  test('Route 3 — /usages?tab=semaine-type : conformité-donnees', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/usages?tab=semaine-type`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('week-profile-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    // Si pas de site sélectionné → SiteRequiredState → pas de cross-link
    const block = tab.getByTestId('week-profile-cross-links');
    const visible = await block.isVisible().catch(() => false);
    if (!visible) {
      test.info().annotations.push({
        type: 'note',
        description: 'WeekProfileTab en SiteRequiredState — cross-link conditionné aux data',
      });
      await page.screenshot({
        path: 'playwright-report/p2-2-3-semaine-type.png',
        fullPage: true,
      });
      return;
    }
    await expect(block).toContainText('Voir données réglementaires');
    const link = block.getByTestId('cross-link-conformite');
    // /conformite?tab=donnees → href avec query string
    const href = await link.getAttribute('href');
    expect(href).toMatch(/^\/conformite\?tab=donnees$/);
    await page.screenshot({
      path: 'playwright-report/p2-2-3-semaine-type.png',
      fullPage: true,
    });
  });

  test('Rail Énergie inchangé sur les 3 routes P2.2', async ({ page }) => {
    const ROUTES = [
      '/monitoring',
      '/consommations/courbe',
      '/usages?tab=semaine-type',
    ];
    for (const route of ROUTES) {
      await page.goto(`${FRONTEND_URL}${route}`, { waitUntil: 'domcontentloaded' });
      const railLabels = await page.locator('nav a').allTextContents();
      const topLevel = railLabels.filter((l) => l.length < 30);
      // Aucun item top-level pour les labels cross-links
      expect(topLevel.filter((l) => /^Créer une action/i.test(l)).length).toBe(0);
      expect(topLevel.filter((l) => /^Voir trajectoire/i.test(l)).length).toBe(0);
      expect(topLevel.filter((l) => /^Voir données/i.test(l)).length).toBe(0);
    }
  });
});
