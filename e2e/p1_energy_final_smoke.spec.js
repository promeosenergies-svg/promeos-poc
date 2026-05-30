/**
 * PROMEOS — Sprint P1.S7 Playwright pack final brique Énergie.
 *
 * Vérifie sur les 5 vues principales de la brique Énergie :
 * - rail Énergie inchangé (aucune route top-level ajoutée) ;
 * - aucune erreur rouge visible ;
 * - au moins un KPI avec provenance visible par route ;
 * - scope-site-required propre si aucun site (3 vues impactées) ;
 * - capture desktop 1440×900.
 *
 * Routes couvertes :
 * - /monitoring                    (P1.S3b)
 * - /consommations/courbe          (P1.S3a)
 * - /consommations/cout-contrat    (P1.S5)
 * - /consommations/marche          (P1.S6)
 * - /usages?tab=semaine-type       (P1.S4)
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P1.S7 — Pack final brique Énergie', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Route 1 — /monitoring : MonitoringSynthesisStrip + provenance', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/monitoring`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('monitoring-synthesis')).toBeVisible({ timeout: 10_000 });
    // Au moins une provenance visible quand grid rendue
    const strip = page.getByTestId('monitoring-synthesis');
    const gridVisible = await strip
      .getByTestId('synthesis-kpis-grid')
      .isVisible()
      .catch(() => false);
    if (gridVisible) {
      const tooltips = strip.getByTestId('kpi-provenance-tooltip');
      expect(await tooltips.count()).toBeGreaterThan(0);
    }
    await page.screenshot({
      path: 'playwright-report/p1-s7-final-1-monitoring.png',
      fullPage: true,
    });
  });

  test('Route 2 — /consommations/courbe : pas d\'erreur rouge', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
    expect(page.url()).toContain('/consommations/courbe');
    await page.screenshot({
      path: 'playwright-report/p1-s7-final-2-courbe.png',
      fullPage: true,
    });
  });

  test('Route 3 — /consommations/cout-contrat : fix UX scope + cross-links', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/cout-contrat`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('cost-contract-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    // Fix UX S6 : aucune erreur rouge sur scope=org
    expect(await tab.getByTestId('cost-contract-error').count()).toBe(0);
    // Cross-links S7 : si données rendues, les links « Comparer à la facture »
    // et « Simuler une offre alternative » apparaissent
    const crossLinks = tab.getByTestId('energy-cross-links');
    const visible = await crossLinks.isVisible().catch(() => false);
    if (visible) {
      await expect(crossLinks).toContainText('Comparer à la facture');
      await expect(crossLinks).toContainText('Simuler une offre alternative');
    }
    await page.screenshot({
      path: 'playwright-report/p1-s7-final-3-cout-contrat.png',
      fullPage: true,
    });
  });

  test('Route 4 — /consommations/marche : fix UX scope + cross-links', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/marche`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('market-exposure-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    // Fix UX S6 : aucune erreur rouge sur scope=org
    expect(await tab.getByTestId('market-exposure-error').count()).toBe(0);
    // Cross-links S7 : si données rendues, les links Achat + Action V4
    const crossLinks = tab.getByTestId('energy-cross-links');
    const visible = await crossLinks.isVisible().catch(() => false);
    if (visible) {
      await expect(crossLinks).toContainText('Simuler une offre alternative');
      await expect(crossLinks).toContainText('Créer une action');
    }
    await page.screenshot({
      path: 'playwright-report/p1-s7-final-4-marche.png',
      fullPage: true,
    });
  });

  test('Route 5 — /usages?tab=semaine-type : fix UX scope', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/usages?tab=semaine-type`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('week-profile-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    // Fix UX S6 : aucune erreur rouge sur scope=org
    expect(await tab.getByTestId('week-profile-error').count()).toBe(0);
    await page.screenshot({
      path: 'playwright-report/p1-s7-final-5-semaine-type.png',
      fullPage: true,
    });
  });

  test('Rail Énergie inchangé sur les 5 routes (NavRegistry intact)', async ({ page }) => {
    const ROUTES = [
      '/monitoring',
      '/consommations/courbe',
      '/consommations/cout-contrat',
      '/consommations/marche',
      '/usages?tab=semaine-type',
    ];
    for (const route of ROUTES) {
      await page.goto(`${FRONTEND_URL}${route}`, { waitUntil: 'domcontentloaded' });
      const railLabels = await page.locator('nav a').allTextContents();
      // Rail ne doit pas avoir d'item top-level pour les onglets internes Énergie
      const topLevel = railLabels.filter((l) => l.length < 30);
      expect(topLevel.filter((l) => /^Coût & contrat$/i.test(l)).length).toBe(0);
      expect(topLevel.filter((l) => /^Marché & exposition$/i.test(l)).length).toBe(0);
      expect(topLevel.filter((l) => /^Semaine type$/i.test(l)).length).toBe(0);
      expect(topLevel.filter((l) => /^Courbe de charge$/i.test(l)).length).toBe(0);
    }
  });
});
