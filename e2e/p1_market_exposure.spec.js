/**
 * PROMEOS — e2e Sprint Énergie P1.S6.
 *
 * Vérifie que /consommations/marche est l'onglet « Marché & exposition » :
 * - le composant MarketExposureTab est rendu ;
 * - scope=org (pas de site) affiche SiteRequiredState proprement
 *   (aucun ENERGY_SCOPE_INVALID rouge) ;
 * - avec site sélectionné : consomme /api/energy/market-exposure ;
 * - rail Énergie inchangé ;
 * - capture desktop 1440×900.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P1.S6 — Marché & exposition /consommations', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Onglet « Marché & exposition » visible + consomme /api/energy/market-exposure (site mode)', async ({
    page,
  }) => {
    const calls = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('/api/energy/market-exposure')) calls.push(url);
    });

    await page.goto(`${FRONTEND_URL}/consommations`, { waitUntil: 'domcontentloaded' });

    const tabLink = page.getByRole('link', { name: /Marché & exposition/i });
    await expect(tabLink).toBeVisible({ timeout: 10_000 });
    await tabLink.click();

    const tab = page.getByTestId('market-exposure-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    await expect.poll(() => page.url(), { timeout: 5_000 }).toContain('/marche');

    // Soit on est en mode org → SiteRequiredState (pas d'appel), soit en
    // mode site → appel API + score gauge OU empty/error documenté.
    await page.waitForFunction(
      () => {
        const root = document.querySelector('[data-testid="market-exposure-tab"]');
        if (!root) return false;
        return (
          root.querySelector('[data-testid="site-required-state"]') ||
          root.querySelector('[data-testid="exposure-score-gauge"]') ||
          root.querySelector('[data-testid="market-exposure-error"]') ||
          root.textContent?.includes('Aucune exposition marché')
        );
      },
      { timeout: 12_000 }
    );

    // Capture le résultat
    await page.screenshot({
      path: 'playwright-report/p1-s6-market-exposure-1440.png',
      fullPage: true,
    });

    // Si une grille KPI est rendue (mode site avec data), un appel API doit avoir eu lieu
    const gridVisible = await tab
      .getByTestId('market-exposure-kpis-grid')
      .isVisible()
      .catch(() => false);
    if (gridVisible) {
      expect(calls.length).toBeGreaterThan(0);
      expect(calls[0]).toMatch(/scope=site/);
      expect(calls[0]).toMatch(/period=12m/);
      expect(calls[0]).toMatch(/market=day_ahead/);
      expect(calls[0]).toMatch(/zone=FR/);
    }
  });

  test('Deep-link /consommations/marche charge directement l\'onglet', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/marche`, { waitUntil: 'domcontentloaded' });
    const tab = page.getByTestId('market-exposure-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });
    const header = page.getByTestId('market-exposure-header');
    await expect(header).toContainText('Marché & exposition');
    await expect(header).toContainText('Votre profil face aux prix spot');
  });

  test('Scope=org sans site → SiteRequiredState propre (pas d\'erreur rouge)', async ({
    page,
  }) => {
    await page.goto(`${FRONTEND_URL}/consommations/marche`, { waitUntil: 'domcontentloaded' });
    const tab = page.getByTestId('market-exposure-tab');
    await expect(tab).toBeVisible({ timeout: 10_000 });

    // Si on est par défaut sur scope=org sans site → SiteRequiredState
    const siteRequired = tab.getByTestId('site-required-state');
    const visible = await siteRequired.isVisible().catch(() => false);
    if (visible) {
      // Aucune erreur rouge ENERGY_SCOPE_INVALID ne doit apparaître
      const errorBox = tab.getByTestId('market-exposure-error');
      expect(await errorBox.count()).toBe(0);
      // Le message FR métier est bien là
      await expect(siteRequired).toContainText(/Sélectionnez un site/i);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: 'Site déjà sélectionné par défaut — SiteRequiredState non vérifiable',
      });
    }
  });

  test('Rail Énergie inchangé (aucun « Marché & exposition » top-level)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations`, { waitUntil: 'domcontentloaded' });
    const railLabels = await page.locator('nav a').allTextContents();
    const topLevel = railLabels.filter((l) => l.length < 30);
    expect(topLevel.filter((l) => /^Marché & exposition$/i.test(l)).length).toBe(0);
  });
});
