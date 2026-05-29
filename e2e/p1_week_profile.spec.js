/**
 * PROMEOS — e2e Sprint Énergie P1.S4.
 *
 * Vérifie que /usages?tab=semaine-type devient l'onglet « Semaine type » :
 * - le composant WeekProfileTab est rendu ;
 * - il consomme /api/energy/week-profile ;
 * - la heatmap 7×24 est visible OU empty state propre ;
 * - aucun nouvel item rail Énergie n'est introduit ;
 * - capture desktop 1440×900 pour la PR.
 *
 * Pas de calcul métier vérifié côté DOM — assuré par source-guards backend
 * + tests vitest WeekProfileTab.test.jsx.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P1.S4 — Semaine type /usages', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Onglet « Semaine type » visible dans /usages + consomme /api/energy/week-profile', async ({
    page,
  }) => {
    const weekProfileCalls = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('/api/energy/week-profile')) weekProfileCalls.push(url);
    });

    await page.goto(`${FRONTEND_URL}/usages`, { waitUntil: 'domcontentloaded' });

    // Le label de l'onglet apparaît dans la TabBar
    const tabButton = page.getByRole('button', { name: /Semaine type/i });
    await expect(tabButton).toBeVisible({ timeout: 10_000 });
    await tabButton.click();

    // Le composant tab se monte
    const tab = page.getByTestId('week-profile-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    // L'URL contient bien tab=semaine-type
    await expect.poll(() => page.url(), { timeout: 5_000 }).toContain('tab=semaine-type');

    // L'appel API doit avoir été déclenché
    await expect.poll(() => weekProfileCalls.length, { timeout: 10_000 }).toBeGreaterThan(0);
    expect(weekProfileCalls[0]).toMatch(/scope=(org|site|portfolio)/);
    expect(weekProfileCalls[0]).toMatch(/days=\d+/);

    // Le rendu se stabilise : heatmap OU empty state OU error documenté
    await page.waitForFunction(
      () => {
        const root = document.querySelector('[data-testid="week-profile-tab"]');
        if (!root) return false;
        return (
          root.querySelector('[data-testid="week-profile-heatmap"]') ||
          root.querySelector('[data-testid="week-profile-error"]') ||
          root.textContent?.includes('Données insuffisantes')
        );
      },
      { timeout: 12_000 }
    );

    await page.screenshot({
      path: 'playwright-report/p1-s4-week-profile-1440.png',
      fullPage: true,
    });
  });

  test('Deep-link /usages?tab=semaine-type charge directement l\'onglet', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/usages?tab=semaine-type`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('week-profile-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    const header = page.getByTestId('week-profile-header');
    await expect(header).toContainText('Semaine type');
    await expect(header).toContainText('Votre comportement du lundi au dimanche');
  });

  test('Rail Énergie inchangé (aucun « Semaine type » top-level)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/usages`, { waitUntil: 'domcontentloaded' });
    const railLabels = await page.locator('nav a').allTextContents();
    const railTxt = railLabels.join(' | ');
    // Le rail ne doit PAS contenir « Semaine type » (c'est un onglet interne)
    expect(railTxt).not.toMatch(/Semaine type/i);
  });

  test('Provenance visible sur au moins un KPI quand grid rendue', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/usages?tab=semaine-type`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('week-profile-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    const grid = tab.getByTestId('week-profile-kpis-grid');
    const gridVisible = await grid.isVisible().catch(() => false);
    if (!gridVisible) {
      test.info().annotations.push({
        type: 'note',
        description: 'KPI grid pas rendue (empty/error) — provenance non vérifiable',
      });
      return;
    }
    const cards = tab.getByTestId(/^week-profile-kpi-/);
    expect(await cards.count()).toBeGreaterThan(0);
    const tooltip = cards.first().getByTestId('kpi-provenance-tooltip');
    expect(await tooltip.count()).toBeGreaterThan(0);
  });
});
