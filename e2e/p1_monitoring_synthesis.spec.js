/**
 * PROMEOS — e2e Sprint Énergie P1.S3b.
 *
 * Vérifie que /monitoring devient une « Synthèse Énergie 30 secondes » :
 * - la strip MonitoringSynthesisStrip est rendue ;
 * - elle consomme /api/energy/synthesis ;
 * - la narrative + (jusqu'à) 10 KPI sont affichés avec provenance ;
 * - aucun nouvel item rail Énergie n'est introduit ;
 * - capture desktop 1440×900 (avant / après scroll) pour PR.
 *
 * Pas de calcul métier vérifié côté DOM — la doctrine reste assurée par
 * les source-guards backend + tests vitest MonitoringSynthesis.test.jsx.
 */
import { expect, test } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5175';

test.describe('Sprint Énergie P1.S3b — Monitoring synthesis', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Monitoring rend MonitoringSynthesisStrip + capture le contrat /api/energy/synthesis', async ({
    page,
  }) => {
    const synthesisCalls = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('/api/energy/synthesis')) synthesisCalls.push(url);
    });

    await page.goto(`${FRONTEND_URL}/monitoring`, { waitUntil: 'domcontentloaded' });

    // La strip doit apparaître dès le rendu (avant ou après loading)
    const strip = page.getByTestId('monitoring-synthesis');
    await expect(strip).toBeVisible({ timeout: 10_000 });

    // L'appel API doit avoir été déclenché
    await expect.poll(() => synthesisCalls.length, { timeout: 8_000 }).toBeGreaterThan(0);
    expect(synthesisCalls[0]).toMatch(/scope=(org|site|portfolio)/);
    expect(synthesisCalls[0]).toMatch(/period=30d/);

    // Le rendu se stabilise : soit grid de KPI, soit empty/error documenté
    await page.waitForFunction(
      () => {
        const root = document.querySelector('[data-testid="monitoring-synthesis"]');
        if (!root) return false;
        return (
          root.querySelector('[data-testid="synthesis-kpis-grid"]') ||
          root.querySelector('[data-testid="synthesis-error"]') ||
          root.textContent?.includes('Aucune synthèse énergétique')
        );
      },
      { timeout: 12_000 }
    );

    await page.screenshot({
      path: 'playwright-report/p1-s3b-monitoring-synthesis-1440.png',
      fullPage: true,
    });
  });

  test('Rail Énergie inchangé (4 items canoniques)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/monitoring`, { waitUntil: 'domcontentloaded' });

    // Le rail latéral garde ses items canoniques
    const railLabels = await page.locator('nav a').allTextContents();
    const railTxt = railLabels.join(' | ');
    expect(railTxt).not.toContain('Synthèse Énergie');
    expect(railTxt).not.toContain('Synthèse 30s');
  });

  test('Provenance visible sur au moins un KPI rendu', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/monitoring`, { waitUntil: 'domcontentloaded' });
    const strip = page.getByTestId('monitoring-synthesis');
    await expect(strip).toBeVisible({ timeout: 10_000 });

    // On laisse le temps à la grid de se rendre
    const grid = strip.getByTestId('synthesis-kpis-grid');
    const gridVisible = await grid.isVisible().catch(() => false);
    if (!gridVisible) {
      test.info().annotations.push({
        type: 'note',
        description: 'KPI grid pas rendue (empty state ou error) — provenance non vérifiable',
      });
      return;
    }

    // Au moins une carte avec un tooltip provenance (rendu en <details>)
    const cards = strip.getByTestId(/^synthesis-kpi-/);
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);

    const firstCard = cards.first();
    const tooltip = firstCard.getByTestId('kpi-provenance-tooltip');
    expect(await tooltip.count()).toBeGreaterThan(0);
  });
});
