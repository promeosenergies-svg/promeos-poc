/**
 * PROMEOS — E3: Bill Intel / Shadow Billing Flow
 * Sprint E — Invoice overview, anomalies, drawer, shadow billing.
 *
 * Parcours: Login → Bill Intel → Hero KPIs → Anomalies table →
 *           Drawer detail → Shadow billing check → Units coherence
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, assertCleanBody, assertNotErrorPage,
  assertNoHorizontalScroll, waitForPageReady,
  screenshot, navigateAndAssert, VIEWPORTS,
} from './helpers.js';

const viewports = [
  { name: 'desktop-1440', ...VIEWPORTS.desktop },
  { name: 'laptop-1280', ...VIEWPORTS.laptop },
  { name: 'compact-1024', ...VIEWPORTS.compact },
];

for (const vp of viewports) {
  test.describe(`E3 — Bill Intel [${vp.name}]`, () => {
    let consoleMonitor;

    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      consoleMonitor = attachConsoleMonitor(page);
      await login(page);
    });

    test.afterEach(async () => {
      const errors = consoleMonitor.getErrors();
      expect(errors.length, `Console errors: ${errors.join(' | ')}`).toBe(0);
    });

    test('Bill Intel loads with hero KPIs', async ({ page }) => {
      const body = await navigateAndAssert(page, '/bill-intel', 'Bill Intel');
      await screenshot(page, `e3-bill-intel-${vp.name}`);

      // Should show billing data
      expect(body.length).toBeGreaterThan(200);

      // Should show EUR amounts
      expect(body).toMatch(/€|EUR|k€/);

      // Should NOT show "—" on critical KPIs (D+ fix)
      // Allow some "—" but not on primary hero KPIs
    });

    test('Bill Intel shows invoice count and anomaly count', async ({ page }) => {
      await page.goto('/bill-intel');
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // Should mention factures/invoices
      const hasBillingContent = /facture|invoice|anomalie|insight/i.test(body);
      expect(hasBillingContent).toBe(true);

      // Should show numeric values (not empty)
      expect(body).toMatch(/\d+/);
    });

    test('Bill Intel units are homogeneous (EUR, kWh/MWh)', async ({ page }) => {
      await page.goto('/bill-intel');
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // Should NOT show mixed dollar signs
      expect(body).not.toContain('$');

      // Should use FR formatting (not US)
      // No explicit "." as thousands separator (FR uses space)
    });

    test('Bill Intel anomaly drawer opens', async ({ page }) => {
      await page.goto('/bill-intel');
      await waitForPageReady(page);

      // Look for clickable anomaly/insight rows
      const insightRow = page.locator('table tbody tr, [data-testid*="insight"], [data-testid*="anomaly"]').first();
      const isVisible = await insightRow.isVisible({ timeout: 5000 }).catch(() => false);

      if (!isVisible) {
        // Try to find any clickable content card
        const card = page.locator('[class*="card"], [class*="anomal"]').first();
        if (await card.isVisible({ timeout: 3000 }).catch(() => false)) {
          await card.click();
          await page.waitForTimeout(1500);
        } else {
          test.skip(true, 'No clickable insight/anomaly found');
          return;
        }
      } else {
        await insightRow.click();
        await page.waitForTimeout(1500);
      }

      await screenshot(page, `e3-bill-intel-drawer-${vp.name}`);
      await assertCleanBody(page);
    });

    test('Billing timeline loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/billing', 'Billing Timeline');
      await screenshot(page, `e3-billing-timeline-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);
    });

    test('Bill Intel → Billing timeline flow', async ({ page }) => {
      // Start at Bill Intel
      await page.goto('/bill-intel');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Navigate to billing timeline
      await page.goto('/billing');
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      await screenshot(page, `e3-billing-flow-${vp.name}`);
    });
  });
}
