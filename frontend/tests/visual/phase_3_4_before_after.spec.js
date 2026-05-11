/**
 * Phase 3.4 — Capture before/after cockpit/jour V1 → V2
 *
 * ATTENTION : ce fichier est conservé en .spec.js pour traçabilité avec
 * le prompt HARD_STOP fourni. Le projet n'a PAS @playwright/test installé
 * comme test-runner (seul `playwright` API brute via Node scripts). Pour
 * exécuter la capture, voir le script Node équivalent :
 *   `tools/playwright/phase_3_4_capture.mjs`
 *
 * Différences avec le prompt original :
 *   - Le `data-component` est `SolHeroPremiumNight` (pas `SolHero`).
 *   - Phase F.1 : `data-component="HubKpiCard"` (extrait — était `KpiTriptychCard`).
 *   - Phase F.2 : `data-component="ChartFrameBars"` + `"ChartFrameLine"` (extraits
 *     des helpers locaux `BarsDaily7d` + `LineCharge24h`).
 *   - Le port frontend refonte-sol2 est 5175 (pas 5173, cf MEMORY.md
 *     ports POC vs refonte-sol).
 *   - `?demo_state=*` n'est PAS encore implémenté côté React → seuls les
 *     captures `default` rendent contenu réel ; loading/empty/error/
 *     partial sont à activer Phase E (P1 audit).
 *
 * Si @playwright/test installé un jour :
 *   PHASE_LABEL=after BASE_URL=http://localhost:5175 \
 *     npx playwright test frontend/tests/visual/phase_3_4_before_after.spec.js
 */

import { test } from '@playwright/test';

const VIEWPORTS = [
  { name: '2xl', width: 1440, height: 900 },
  { name: 'xl', width: 1280, height: 800 },
  { name: 'lg', width: 1024, height: 768 },
];

const STATES = [
  { name: 'default', query: '' },
  { name: 'loading', query: '?demo_state=loading' },
  { name: 'empty', query: '?demo_state=empty' },
  { name: 'error', query: '?demo_state=error' },
  { name: 'partial', query: '?demo_state=partial' },
];

const PHASE = process.env.PHASE_LABEL || 'after';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5175';

test.describe(`Phase 3.4 capture · ${PHASE}`, () => {
  for (const vp of VIEWPORTS) {
    test.describe(`Viewport ${vp.name} (${vp.width}×${vp.height})`, () => {
      for (const state of STATES) {
        test(`${PHASE} / ${state.name}`, async ({ page }) => {
          await page.setViewportSize(vp);
          await page.goto(`${BASE_URL}/cockpit/jour${state.query}`);

          if (state.name === 'default') {
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(800);
          }

          if (state.name === 'loading') {
            await page.waitForTimeout(400);
          }

          await page.screenshot({
            path: `frontend/tests/visual/snapshots/${PHASE}/${vp.name}/above-${state.name}.png`,
            fullPage: false,
          });

          await page.screenshot({
            path: `frontend/tests/visual/snapshots/${PHASE}/${vp.name}/full-${state.name}.png`,
            fullPage: true,
          });

          if (state.name === 'default') {
            const hero = page.locator('[data-component="SolHeroPremiumNight"]').first();
            await hero.screenshot({
              path: `frontend/tests/visual/snapshots/${PHASE}/${vp.name}/hero-zoom.png`,
            });

            const kpis = page.locator('[data-component="HubKpiCard"]');
            const count = await kpis.count();
            for (let i = 0; i < count; i++) {
              await kpis.nth(i).screenshot({
                path: `frontend/tests/visual/snapshots/${PHASE}/${vp.name}/kpi-${i + 1}.png`,
              });
            }

            const highlights = page.locator('[data-component="HubHighlight"]');
            const hCount = await highlights.count();
            for (let i = 0; i < hCount; i++) {
              await highlights.nth(i).screenshot({
                path: `frontend/tests/visual/snapshots/${PHASE}/${vp.name}/highlight-${i + 1}.png`,
              });
            }
          }
        });
      }
    });
  }
});
