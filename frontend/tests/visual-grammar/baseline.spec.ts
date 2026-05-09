/**
 * Sprint Grammaire Produit v1 — Phase 0.3 baseline visuelle
 *
 * Spec Playwright destinée à @playwright/test (pas vitest).
 * À exécuter dès que @playwright/test est installé en Phase 3 :
 *   npm i -D @playwright/test
 *   npx playwright test --config=frontend/tests/visual-grammar/playwright.config.ts
 *
 * 21 baselines (7 vues × 3 viewports). /onboarding exclu — redirect /cockpit/jour
 * depuis Phase 0.1 (cf. App.jsx commentaire).
 *
 * Tolérance : maxDiffPixelRatio 0.005 (0,5 %) — bloque PR Phase 2 si drift
 * supérieur. Update baselines : `npx playwright test --update-snapshots`.
 *
 * Refs : docs/vision/promeos_sol_doctrine.md §5, ADR-016 enforcement runtime,
 * docs/audits/grammar_v1/SYNTHESE_AUDIT_PHASE_0.md (audit factuel).
 */

import { test, expect, type Page } from '@playwright/test';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';

const VIEWS = [
  { slug: 'cockpit-jour', path: '/cockpit/jour', label: 'Cockpit Briefing (jour)' },
  { slug: 'cockpit-strategique', path: '/cockpit/strategique', label: 'Cockpit Note exécutive' },
  { slug: 'centre-action', path: '/?actionCenter=open&tab=actions', label: "Centre d'action (peek)" },
  { slug: 'anomalies', path: '/anomalies', label: 'Anomalies — Ledger' },
  { slug: 'site-paris-bureaux', path: '/sites/1', label: 'Site360 — Atlas Paris' },
  { slug: 'conformite', path: '/conformite', label: 'Conformité' },
  { slug: 'factures', path: '/bill-intel', label: 'Bill-Intel — Ledger factures' },
] as const;

const VIEWPORTS = [
  { width: 1440, height: 900, key: '1440x900' },
  { width: 1280, height: 800, key: '1280x800' },
  { width: 1024, height: 1366, key: '1024x1366' },
] as const;

async function loginDemo(page: Page): Promise<void> {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'load', timeout: 60_000 });
  await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 20_000 });
  await page.fill('input[type="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 30_000 });
  await page.waitForTimeout(2500);
}

async function freezeAnimations(page: Page): Promise<void> {
  await page.evaluate(() => {
    document.querySelectorAll('*').forEach((el) => {
      const cs = getComputedStyle(el);
      if (cs.animationName !== 'none' || cs.transitionProperty !== 'none') {
        (el as HTMLElement).style.animation = 'none';
        (el as HTMLElement).style.transition = 'none';
      }
    });
  });
}

for (const vp of VIEWPORTS) {
  test.describe(`baseline ${vp.key}`, () => {
    for (const view of VIEWS) {
      test(`${view.slug} @ ${vp.key}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await loginDemo(page);

        await page.goto(`${FRONTEND_URL}${view.path}`, {
          waitUntil: 'load',
          timeout: 30_000,
        });
        await page.waitForLoadState('networkidle', { timeout: 30_000 });
        await page.waitForTimeout(1500);
        await freezeAnimations(page);
        await page.waitForTimeout(300);

        await expect(page).toHaveScreenshot(`baseline-${view.slug}-${vp.key}.png`, {
          fullPage: true,
          maxDiffPixelRatio: 0.005,
          animations: 'disabled',
        });
      });
    }
  });
}

test.describe('regression — onboarding redirect (Phase 0.1)', () => {
  test('/onboarding redirige vers /cockpit/jour', async ({ page }) => {
    await loginDemo(page);
    await page.goto(`${FRONTEND_URL}/onboarding`, { waitUntil: 'load' });
    await page.waitForTimeout(1500);
    expect(page.url()).toContain('/cockpit/jour');
  });
});
