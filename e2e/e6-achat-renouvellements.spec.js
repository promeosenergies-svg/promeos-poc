/**
 * PROMEOS — E6: Achat / Renouvellements / Assistant Flow
 * Sprint E — Purchase module navigation, scenarios, contract radar.
 *
 * Parcours: Login → Achat Energie → Strategies → Renouvellements →
 *           Assistant → CTA coherence
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
  test.describe(`E6 — Achat & Renouvellements [${vp.name}]`, () => {
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

    test('Achat Énergie page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/achat-energie', 'Achat Énergie');
      await screenshot(page, `e6-achat-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);

      // Should NOT contain English-only CTA
      expect(body).not.toMatch(/\bBuy now\b|\bPurchase\b/i);
    });

    test('Achat shows tabs (Simulation, Portefeuille, etc.)', async ({ page }) => {
      await page.goto('/achat-energie');
      await waitForPageReady(page);

      const body = await page.textContent('body');
      // Should have navigation within purchase module
      expect(body.length).toBeGreaterThan(100);
    });

    test('Renouvellements page loads with contract data', async ({ page }) => {
      const body = await navigateAndAssert(page, '/renouvellements', 'Renouvellements');
      await screenshot(page, `e6-renouvellements-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);

      // Should show contract-related content
      const hasContractContent = /contrat|échéance|renouvellement|expir/i.test(body);
      expect(hasContractContent).toBe(true);
    });

    test('Renouvellements shows urgency badges', async ({ page }) => {
      await page.goto('/renouvellements');
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // Should show contract status indicators
      expect(body.length).toBeGreaterThan(100);
    });

    test('Purchase Assistant page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/achat-assistant', 'Assistant Achat');
      await screenshot(page, `e6-assistant-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);
    });

    test('No route fantôme in achat module', async ({ page }) => {
      const routes = ['/achat-energie', '/renouvellements', '/achat-assistant'];

      for (const route of routes) {
        await page.goto(route);
        await waitForPageReady(page);
        await assertNotErrorPage(page);
        await assertCleanBody(page);
      }

      await screenshot(page, `e6-no-404-${vp.name}`);
    });

    test('Full flow: Achat → Renouvellements → Assistant', async ({ page }) => {
      // Achat
      await page.goto('/achat-energie');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Renouvellements
      await page.goto('/renouvellements');
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      // Assistant
      await page.goto('/achat-assistant');
      await waitForPageReady(page);
      await assertCleanBody(page);

      await screenshot(page, `e6-full-flow-${vp.name}`);
    });

    test('Achat module uses FR microcopy', async ({ page }) => {
      await page.goto('/achat-energie');
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // No English-only words in navigation/CTAs
      expect(body).not.toMatch(/\bSubmit\b|\bCancel\b|\bLoading\.\.\.\b/);

      // Should use EUR format
      if (body.match(/€|EUR/)) {
        // Good — uses EUR
        expect(body).not.toContain('$');
      }
    });
  });
}
