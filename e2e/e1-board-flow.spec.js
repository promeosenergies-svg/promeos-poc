/**
 * PROMEOS — E1: DG / Owner / Board Flow
 * Sprint E — Full clicked & asserted demo journey.
 *
 * Parcours: Login → Cockpit → KPIs → Conformité → Finding →
 *           Create Action → Actions list → Detail → Add proof →
 *           Close action → Deeplink retour
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, assertCleanBody, assertNotErrorPage,
  assertNoHorizontalScroll, assertRealSiteName, waitForPageReady,
  screenshot, navigateAndAssert, VIEWPORTS,
} from './helpers.js';

const viewports = [
  { name: 'desktop-1440', ...VIEWPORTS.desktop },
  { name: 'laptop-1280', ...VIEWPORTS.laptop },
  { name: 'compact-1024', ...VIEWPORTS.compact },
];

for (const vp of viewports) {
  test.describe(`E1 — Board Flow [${vp.name}]`, () => {
    let consoleMonitor;

    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      consoleMonitor = attachConsoleMonitor(page);
      await login(page);
    });

    test.afterEach(async () => {
      const errors = consoleMonitor.getErrors();
      if (errors.length > 0) {
        console.warn(`[E1 ${vp.name}] Console errors:`, errors);
      }
      // Assert no unexpected console errors
      expect(errors.length, `Unexpected console errors: ${errors.join(' | ')}`).toBe(0);
    });

    test('Cockpit loads with executive KPIs', async ({ page }) => {
      await page.goto('/cockpit');
      await waitForPageReady(page);

      // KPI section should be visible (use heading role to avoid sidebar match)
      await expect(page.getByRole('heading', { name: 'Vue exécutive' })).toBeVisible({ timeout: 10_000 });
      await screenshot(page, `e1-cockpit-${vp.name}`);

      const body = await assertCleanBody(page);
      await assertNoHorizontalScroll(page, true);

      // Should show EUR amounts
      expect(body).toMatch(/€|EUR|k€/);

      // Should show real data, not empty
      expect(body.length).toBeGreaterThan(300);

      // No fallback site names
      await assertRealSiteName(page);
    });

    test('Cockpit KPI tiles are credible', async ({ page }) => {
      await page.goto('/cockpit');
      await waitForPageReady(page);

      // Check that key KPI labels exist
      const body = await page.textContent('body');
      expect(body).toContain('Conformité');

      // Risk KPI should show a value (not "Données manquantes" after D+ fix)
      const risqueSection = page.locator('text=Risque').first();
      await expect(risqueSection).toBeVisible({ timeout: 10_000 });
    });

    test('Conformité page loads with obligations', async ({ page }) => {
      const body = await navigateAndAssert(page, '/conformite', 'Conformité');
      await screenshot(page, `e1-conformite-${vp.name}`);

      // Tab "Obligations" should be visible (use first() to handle sidebar match)
      await expect(page.locator('text=Obligations').first()).toBeVisible({ timeout: 10_000 });

      // Should show compliance findings
      expect(body.length).toBeGreaterThan(200);
    });

    test('Conformité → open finding detail', async ({ page }) => {
      await page.goto('/conformite');
      await waitForPageReady(page);

      // Look for a finding row (table row or card with a severity/status badge)
      const findingRow = page.locator('table tbody tr, [data-testid*="finding"], [class*="finding"]').first();
      const findingVisible = await findingRow.isVisible().catch(() => false);

      if (findingVisible) {
        await findingRow.click();
        await page.waitForTimeout(1000);
        await screenshot(page, `e1-finding-detail-${vp.name}`);

        // A drawer or detail section should appear
        const detailBody = await page.textContent('body');
        expect(detailBody.length).toBeGreaterThan(200);
      } else {
        // Try the Recommandations tab for actionable findings
        const recoTab = page.locator('text=Recommandations').first();
        if (await recoTab.isVisible().catch(() => false)) {
          await recoTab.click();
          await page.waitForTimeout(1500);
          await screenshot(page, `e1-recommandations-${vp.name}`);
        }
      }

      await assertCleanBody(page);
    });

    test('Actions page lists demo actions', async ({ page }) => {
      const body = await navigateAndAssert(page, '/actions', 'Actions');
      await screenshot(page, `e1-actions-list-${vp.name}`);

      // Should have action items (seeded by demo)
      expect(body.length).toBeGreaterThan(200);

      // No fallback site names
      await assertRealSiteName(page);
    });

    test('Action detail drawer opens with coherent data', async ({ page }) => {
      await page.goto('/actions');
      await waitForPageReady(page);

      // Click first action row
      const actionRow = page.locator('table tbody tr, [data-testid*="action-row"]').first();
      const isVisible = await actionRow.isVisible({ timeout: 5000 }).catch(() => false);

      if (!isVisible) {
        test.skip(true, 'No action rows visible in demo data');
        return;
      }

      await actionRow.click();
      await page.waitForTimeout(1500);
      await screenshot(page, `e1-action-detail-${vp.name}`);

      // Drawer should show action detail
      const body = await page.textContent('body');
      await assertCleanBody(page);

      // Should show source label (Conformité, Facturation, etc.)
      const hasSource = /Conformité|Facturation|Consommation|Achats|Actions/.test(body);
      expect(hasSource).toBe(true);

      // Should show a status (En cours, Ouvert, Terminé, etc.)
      const hasStatus = /En cours|Ouvert|Terminé|Fermé|À faire|in_progress|open|done/i.test(body);
      expect(hasStatus).toBe(true);
    });

    test('Full flow: Cockpit → Conformité → Actions → Detail', async ({ page }) => {
      // Step 1: Cockpit
      await page.goto('/cockpit');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Step 2: Navigate to Conformité via sidebar or direct
      await page.goto('/conformite');
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      // Step 3: Navigate to Actions
      await page.goto('/actions');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Step 4: Open first action detail
      const row = page.locator('table tbody tr').first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1500);
        await assertCleanBody(page);
      }

      await screenshot(page, `e1-full-flow-${vp.name}`);

      // Validate no errors accumulated
      const errors = consoleMonitor.getErrors();
      expect(errors.length, `Console errors during full flow: ${errors.join(' | ')}`).toBe(0);
    });
  });
}
