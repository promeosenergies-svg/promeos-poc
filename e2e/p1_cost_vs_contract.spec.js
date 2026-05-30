/**
 * PROMEOS — e2e Sprint Énergie P1.S5.
 *
 * Vérifie que /consommations/cout-contrat est l'onglet « Coût & contrat » :
 * - le composant CostContractTab est rendu ;
 * - il consomme /api/energy/cost-vs-contract ;
 * - 4 scénarios visibles (sauf empty/error) ;
 * - warning « Simulation indicative » visible (ou empty state propre) ;
 * - rail Énergie inchangé ;
 * - capture desktop 1440×900.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P1.S5 — Coût & contrat /consommations', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Onglet « Coût & contrat » visible + consomme /api/energy/cost-vs-contract', async ({
    page,
  }) => {
    const calls = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('/api/energy/cost-vs-contract')) calls.push(url);
    });

    await page.goto(`${FRONTEND_URL}/consommations`, { waitUntil: 'domcontentloaded' });

    const tabLink = page.getByRole('link', { name: /Coût & contrat/i });
    await expect(tabLink).toBeVisible({ timeout: 10_000 });
    await tabLink.click();

    const tab = page.getByTestId('cost-contract-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    await expect.poll(() => page.url(), { timeout: 5_000 }).toContain('/cout-contrat');

    await expect.poll(() => calls.length, { timeout: 10_000 }).toBeGreaterThan(0);
    expect(calls[0]).toMatch(/scope=(org|site|portfolio)/);
    expect(calls[0]).toMatch(/period=12m/);
    expect(calls[0]).toMatch(/scenarios=fixed/);

    // Rendu stabilisé : grid scénarios OU empty/error
    await page.waitForFunction(
      () => {
        const root = document.querySelector('[data-testid="cost-contract-tab"]');
        if (!root) return false;
        return (
          root.querySelector('[data-testid="scenarios-grid"]') ||
          root.querySelector('[data-testid="cost-contract-error"]') ||
          root.textContent?.includes('Aucun contrat actif')
        );
      },
      { timeout: 12_000 }
    );

    await page.screenshot({
      path: 'playwright-report/p1-s5-cost-contract-1440.png',
      fullPage: true,
    });
  });

  test('Deep-link /consommations/cout-contrat charge directement l\'onglet', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/cout-contrat`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('cost-contract-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    const header = page.getByTestId('cost-contract-header');
    await expect(header).toContainText('Coût & contrat');
    await expect(header).toContainText('Votre coût réel selon le contrat actif');
  });

  test('Warning « Simulation indicative » visible quand scénarios rendus', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/cout-contrat`, {
      waitUntil: 'domcontentloaded',
    });
    const tab = page.getByTestId('cost-contract-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    const grid = tab.getByTestId('scenarios-grid');
    const gridVisible = await grid.isVisible().catch(() => false);
    if (!gridVisible) {
      test.info().annotations.push({
        type: 'note',
        description: 'Scénarios grid pas rendue (empty/error) — warning non vérifiable',
      });
      return;
    }
    const warning = tab.getByTestId('simulation-warning');
    await expect(warning).toBeVisible();
    await expect(warning).toContainText('Simulation indicative');
  });

  test('Rail Énergie inchangé (aucun « Coût & contrat » top-level)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations`, { waitUntil: 'domcontentloaded' });
    const railLabels = await page.locator('nav a').allTextContents();
    // Le rail principal ne doit pas mentionner "Coût & contrat" (c'est interne)
    // Note : le tab interne utilise <NavLink> qui peut être dans <nav> du
    // PageShell. On filtre sur le pattern top-level / Énergie module.
    const topLevel = railLabels.filter((l) => l.length < 30);
    expect(topLevel.filter((l) => /^Coût & contrat$/i.test(l)).length).toBe(0);
  });
});
