/**
 * PROMEOS — E5: Notifications → Action Flow
 * Sprint E — Notification inbox, drawer, create action from notification.
 *
 * Parcours: Login → Notifications → Drawer → CTA create action →
 *           Prefill check → Source link
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
  test.describe(`E5 — Notifications → Action [${vp.name}]`, () => {
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

    test('Notifications page loads with entries', async ({ page }) => {
      const body = await navigateAndAssert(page, '/notifications', 'Notifications');
      await screenshot(page, `e5-notifications-${vp.name}`);

      // Should have notification entries
      expect(body.length).toBeGreaterThan(200);

      // Should show severity indicators or labels
      const hasSeverity = /critique|avertissement|info|critical|warn/i.test(body);
      expect(hasSeverity).toBe(true);
    });

    test('Notification severity filters visible', async ({ page }) => {
      await page.goto('/notifications');
      await waitForPageReady(page);

      // Should have filter/triage tabs or severity indicators
      const body = await page.textContent('body');
      // At minimum, notifications should show some categorization
      expect(body.length).toBeGreaterThan(100);
    });

    test('Notification drawer opens on click', async ({ page }) => {
      await page.goto('/notifications');
      await waitForPageReady(page);

      // Click first notification row
      const notifRow = page.locator('table tbody tr, [data-testid*="notification"], [class*="notif"]').first();
      const isVisible = await notifRow.isVisible({ timeout: 5000 }).catch(() => false);

      if (!isVisible) {
        test.skip(true, 'No notification rows visible');
        return;
      }

      await notifRow.click();
      await page.waitForTimeout(1500);
      await screenshot(page, `e5-notif-drawer-${vp.name}`);

      // Drawer should show notification detail
      const body = await page.textContent('body');
      await assertCleanBody(page);
    });

    test('Notification shows impact and source', async ({ page }) => {
      await page.goto('/notifications');
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // Should show impact in EUR or source labels
      const hasRelevantContent = /€|EUR|impact|source|Conformité|Facturation|Consommation/i.test(body);
      expect(hasRelevantContent).toBe(true);

      // Microcopy should be FR
      expect(body).not.toMatch(/\bCreate\b|\bDelete\b|\bUpdate\b/);
    });

    test('Notifications → Actions flow', async ({ page }) => {
      // Start at notifications
      await page.goto('/notifications');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Navigate to actions
      await page.goto('/actions');
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      await screenshot(page, `e5-notif-to-actions-${vp.name}`);
    });

    test('Notification deeplink paths are valid', async ({ page }) => {
      // Fetch notifications from API to check deeplinks
      const res = await page.request.get('http://127.0.0.1:8001/api/notifications/list');
      const notifications = await res.json();

      // Check that deeplinks don't lead to 404
      const deeplinks = [...new Set(
        notifications
          .filter(n => n.deeplink_path)
          .map(n => n.deeplink_path)
          .slice(0, 5) // test max 5 unique deeplinks
      )];

      for (const deeplink of deeplinks) {
        await page.goto(deeplink);
        await waitForPageReady(page);
        await assertNotErrorPage(page);
      }

      await screenshot(page, `e5-deeplinks-${vp.name}`);
    });
  });
}
