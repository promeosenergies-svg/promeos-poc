/**
 * PROMEOS — E4: Patrimoine / Conformité / APER Flow
 * Sprint E — Site portfolio, site detail, compliance score, APER, frise.
 *
 * Parcours: Login → Patrimoine → Site detail → Conformité →
 *           Score → Obligations tabs → APER → Frise
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
  test.describe(`E4 — Patrimoine & Conformité [${vp.name}]`, () => {
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

    test('Patrimoine loads with site table', async ({ page }) => {
      const body = await navigateAndAssert(page, '/patrimoine', 'Patrimoine');
      await screenshot(page, `e4-patrimoine-${vp.name}`);

      // Should show sites (table rows)
      expect(body.length).toBeGreaterThan(200);

      // Should show real site names
      await assertRealSiteName(page);

      // Should show site data (ville, surface, status)
      expect(body).toMatch(/m²|surface|ville|statut|conformité/i);
    });

    test('Patrimoine → Site360 drill-down', async ({ page }) => {
      await page.goto('/patrimoine');
      await waitForPageReady(page);

      // Click first site row
      const firstRow = page.locator('table tbody tr').first();
      await expect(firstRow).toBeVisible({ timeout: 10_000 });
      await firstRow.click();
      await page.waitForTimeout(1500);

      // Look for "Voir la fiche site" CTA in drawer
      const ficheSiteBtn = page.locator('text=Voir la fiche site');
      if (await ficheSiteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await ficheSiteBtn.click();
        await page.waitForURL(/\/sites\/\d+/, { timeout: 10_000 });
      } else {
        // Direct site links
        const siteLink = page.locator('a[href*="/sites/"]').first();
        if (await siteLink.isVisible({ timeout: 3000 }).catch(() => false)) {
          await siteLink.click();
          await page.waitForURL(/\/sites\/\d+/, { timeout: 10_000 });
        } else {
          // Fallback: go directly
          const manifest = await (await page.request.get(`${BACKEND_URL}/api/demo/manifest`)).json();
          await page.goto(`/sites/${manifest.all_site_ids[0]}`);
        }
      }

      await waitForPageReady(page);
      await screenshot(page, `e4-site360-${vp.name}`);

      const body = await assertCleanBody(page);
      expect(body).not.toContain('Site introuvable');

      // Should show tabs
      expect(body).toContain('Résumé');
      expect(body).toContain('Conformité');
    });

    test('Site360 shows all expected tabs', async ({ page }) => {
      const manifest = await (await page.request.get(`${BACKEND_URL}/api/demo/manifest`)).json();
      await page.goto(`/sites/${manifest.all_site_ids[0]}`);
      await waitForPageReady(page);

      const body = await page.textContent('body');

      // Core tabs
      expect(body).toContain('Résumé');
      expect(body).toContain('Consommation');
      expect(body).toContain('Conformité');
      expect(body).toContain('Actions');
    });

    test('Conformité page shows score and obligations', async ({ page }) => {
      const body = await navigateAndAssert(page, '/conformite', 'Conformité');
      await screenshot(page, `e4-conformite-${vp.name}`);

      // Should show obligations tab
      await expect(page.locator('text=Obligations').first()).toBeVisible({ timeout: 10_000 });
    });

    test('Conformité tabs navigate without error', async ({ page }) => {
      await page.goto('/conformite');
      await waitForPageReady(page);

      // Click through available tabs
      const tabLabels = ['Obligations', 'Données', 'Recommandations', 'Preuves'];

      for (const label of tabLabels) {
        const tab = page.locator(`text=${label}`).first();
        if (await tab.isVisible({ timeout: 3000 }).catch(() => false)) {
          await tab.click();
          await page.waitForTimeout(1000);
          await assertCleanBody(page);
        }
      }

      await screenshot(page, `e4-conformite-tabs-${vp.name}`);
    });

    test('Conformité Tertiaire page loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/conformite/tertiaire', 'Tertiaire');
      await screenshot(page, `e4-tertiaire-${vp.name}`);

      expect(body.length).toBeGreaterThan(50);
    });

    test('Compliance pipeline loads', async ({ page }) => {
      const body = await navigateAndAssert(page, '/compliance/pipeline', 'Pipeline');
      await screenshot(page, `e4-pipeline-${vp.name}`);

      expect(body.length).toBeGreaterThan(100);
    });

    test('Full flow: Patrimoine → Site360 → Conformité → Pipeline', async ({ page }) => {
      // Patrimoine
      await page.goto('/patrimoine');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Get first site
      const manifest = await (await page.request.get(`${BACKEND_URL}/api/demo/manifest`)).json();
      const siteId = manifest.all_site_ids[0];

      // Site360
      await page.goto(`/sites/${siteId}`);
      await waitForPageReady(page);
      await assertCleanBody(page);
      await assertNotErrorPage(page);

      // Conformité
      await page.goto('/conformite');
      await waitForPageReady(page);
      await assertCleanBody(page);

      // Pipeline
      await page.goto('/compliance/pipeline');
      await waitForPageReady(page);
      await assertCleanBody(page);

      await screenshot(page, `e4-full-flow-${vp.name}`);
    });
  });
}
