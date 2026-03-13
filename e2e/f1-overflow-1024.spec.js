/**
 * PROMEOS — F1: No Horizontal Scroll at 1024px
 * Sprint F — Strict assertion: 0 overflow on all board-facing pages.
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, waitForPageReady,
  assertNoHorizontalScroll, screenshot, VIEWPORTS,
} from './helpers.js';

const PAGES = [
  '/cockpit',
  '/conformite',
  '/actions',
  '/patrimoine',
  '/achat-energie',
  '/renouvellements',
  '/notifications',
  '/facturation',
  '/consommation',
];

const viewports = [
  { name: 'compact-1024', ...VIEWPORTS.compact },
  { name: 'laptop-1280', ...VIEWPORTS.laptop },
  { name: 'desktop-1440', ...VIEWPORTS.desktop },
];

for (const vp of viewports) {
  test.describe(`F1 — No overflow [${vp.name}]`, () => {
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

    test('All board-facing pages have 0 horizontal scroll', async ({ page }) => {
      test.setTimeout(120_000); // 9 pages to check
      const overflows = [];

      for (const route of PAGES) {
        await page.goto(route);
        await waitForPageReady(page);

        const overflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth - document.documentElement.clientWidth;
        });

        if (overflow > 5) {
          overflows.push({ route, overflow });
        }
      }

      // Screenshot last page
      await screenshot(page, `f1-overflow-check-${vp.name}`);

      // Strict assertion: no overflow > 5px on any page
      expect(
        overflows,
        `Overflow detected at ${vp.name}: ${overflows.map((o) => `${o.route} (${o.overflow}px)`).join(', ')}`
      ).toHaveLength(0);
    });
  });
}
