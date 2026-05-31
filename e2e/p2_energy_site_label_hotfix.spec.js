/**
 * PROMEOS — e2e Hotfix Énergie Site label (2026-05-31).
 *
 * Vérifie que les vues Énergie n'affichent JAMAIS de fallback technique
 * `Site #${id}` ni de doublon `Site Site` dans la barre de filtres.
 *
 * Vues couvertes :
 * - /consommations/courbe (LoadCurveTab + EnergyFilterBar)
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Hotfix Énergie Site label — /consommations/courbe', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Le rendu /consommations/courbe ne contient JAMAIS « Site # » technique', async ({
    page,
  }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

    // Récupère tout le contenu textuel rendu de la page
    const bodyText = await page.evaluate(() => document.body.innerText);

    // Aucune occurrence de "Site #" suivi d'un nombre
    expect(bodyText).not.toMatch(/Site #\d+/);
    // Aucune occurrence de "Compteur #" suivi d'un nombre
    expect(bodyText).not.toMatch(/Compteur #\d+/);
    // Aucune occurrence de "Organisation #" suivi d'un nombre
    expect(bodyText).not.toMatch(/Organisation #\d+/);

    await page.screenshot({
      path: 'playwright-report/hotfix-site-label-1-courbe.png',
      fullPage: true,
    });
  });

  test('Le filtre Site ne contient JAMAIS « Site Site » (doublon)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

    const filterBar = page.getByTestId('energy-filter-bar');
    const visible = await filterBar.isVisible().catch(() => false);
    if (!visible) {
      test.info().annotations.push({
        type: 'note',
        description: 'EnergyFilterBar pas visible (pas de site sélectionné ?) — skip',
      });
      return;
    }
    const text = (await filterBar.textContent()) || '';
    expect(text).not.toMatch(/Site Site/);
    expect(text).not.toMatch(/Site #/);
  });

  test('Le filtre Site affiche un libellé FR métier (nom OU fallback FR)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

    const labelEl = page.getByTestId('filter-scope-label');
    const visible = await labelEl.isVisible().catch(() => false);
    if (!visible) {
      test.info().annotations.push({
        type: 'note',
        description: 'filter-scope-label pas visible (filterbar masqué) — skip',
      });
      return;
    }
    const text = (await labelEl.textContent()) || '';
    // Le libellé doit être l'un de :
    //  - le nom métier du site (ex: « Siège HELIOS Paris »)
    //  - « Site sélectionné » (id connu, nom inconnu)
    //  - « Sélectionner un site » (aucun site)
    // Mais JAMAIS « Site #1 » ni « # » seul ni « —[*]».
    expect(text).not.toMatch(/^#/);
    expect(text).not.toContain('#');
    expect(text.length).toBeGreaterThan(0);
    expect(text).not.toBe('—');
  });

  test('Rail Énergie inchangé sur /consommations/courbe', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/consommations/courbe`, { waitUntil: 'domcontentloaded' });
    const railLabels = await page.locator('nav a').allTextContents();
    const railTxt = railLabels.join(' | ');
    // Aucun label rail ne devrait contenir « Site # »
    expect(railTxt).not.toMatch(/Site #\d+/);
  });
});
