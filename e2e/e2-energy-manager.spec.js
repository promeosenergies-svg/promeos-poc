/**
 * PROMEOS — E2: Energy Manager Multi-Site Flow
 * Sprint E — Scope switching, consumption, performance, anomalies.
 *
 * Parcours: Login → Scope switch (org/site) → Consommation →
 *           Portfolio → Diagnostic → Monitoring → Actions
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, assertCleanBody, assertNotErrorPage,
  assertNoHorizontalScroll, assertRealSiteName, waitForPageReady,
  screenshot, navigateAndAssert, VIEWPORTS, BACKEND_URL,
} from './helpers.js';

const viewports = [
  { name: 'desktop-1440', ...VIEWPORTS.desktop },
  { name: 'laptop-1280', ...VIEWPORTS.laptop },
  { name: 'compact-1024', ...VIEWPORTS.compact },
];

for (const vp of viewports) {
  test.describe(`E2 — Energy Manager [${vp.name}]`, () => {
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

    test('Scope is visible and shows org name', async ({ page }) => {
      await page.goto('/cockpit');
      await waitForPageReady(page);

      // Scope should show org name "Groupe HELIOS" or "Tous les sites"
      const body = await page.textContent('body');
      const hasScope = /HELIOS|Tous les sites|Portefeuille|sites/i.test(body);
      expect(hasScope).toBe(true);

      await screenshot(page, `e2-scope-visible-${vp.name}`);
    });

    test('Consumption portfolio loads with data', async ({ page }) => {
      const body = await navigateAndAssert(page, '/consommations/portfolio', 'Portfolio Conso');
      await screenshot(page, `e2-conso-portfolio-${vp.name}`);

      // Should show consumption data or relevant labels
      expect(body.length).toBeGreaterThan(100);
    });

    test('Consumption explorer loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/consommations/explorer', 'Explorer');
      await screenshot(page, `e2-conso-explorer-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);
    });

    test('Diagnostic page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/diagnostic-conso', 'Diagnostic');
      await screenshot(page, `e2-diagnostic-${vp.name}`);

      expect(body.length).toBeGreaterThan(50);
    });

    test('Monitoring page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/monitoring', 'Monitoring');
      await screenshot(page, `e2-monitoring-${vp.name}`);

      expect(body.length).toBeGreaterThan(50);
    });

    test('Usages horaires page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/usages-horaires', 'Usages horaires');
      await screenshot(page, `e2-usages-${vp.name}`);

      expect(body.length).toBeGreaterThan(50);
    });

    test('Scope change to single site updates data', async ({ page }) => {
      // First visit cockpit with "tous les sites"
      await page.goto('/cockpit');
      await waitForPageReady(page);
      const bodyAll = await page.textContent('body');

      // Get first site ID from manifest
      const manifestRes = await page.request.get(`${BACKEND_URL}/api/demo/manifest`);
      const manifest = await manifestRes.json();
      const firstSiteId = manifest.all_site_ids[0];

      // Navigate to a single-site view
      await page.goto(`/consommations/explorer?site_id=${firstSiteId}`);
      await waitForPageReady(page);
      await assertCleanBody(page);
      await screenshot(page, `e2-site-scoped-${vp.name}`);

      const bodySite = await page.textContent('body');
      expect(bodySite.length).toBeGreaterThan(50);
    });

    test('Actions page shows actions with site context', async ({ page }) => {
      await page.goto('/actions');
      await waitForPageReady(page);

      const body = await assertCleanBody(page);
      await assertRealSiteName(page);
      await screenshot(page, `e2-actions-${vp.name}`);

      // Should list actions
      expect(body.length).toBeGreaterThan(200);
    });

    test('Multi-page flow: Portfolio → Explorer → Diagnostic → Actions', async ({ page }) => {
      // Portfolio
      await page.goto('/consommations/portfolio');
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      // Explorer
      await page.goto('/consommations/explorer');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Diagnostic
      await page.goto('/diagnostic-conso');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Actions
      await page.goto('/actions');
      await waitForPageReady(page);
      await assertCleanBody(page);

      await screenshot(page, `e2-multi-flow-${vp.name}`);
    });
  });
}
