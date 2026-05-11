/**
 * PROMEOS — Phase 3.4 Hub Page L11 capture before/after.
 *
 * Equivalent Node-script du spec Playwright fourni dans
 * `frontend/tests/visual/phase_3_4_before_after.spec.js`. Utilise
 * l'API playwright brute (déjà installée à la racine, ~150 MB) sans
 * dépendre de `@playwright/test` (test-runner non installé).
 *
 * Aligné sur `tools/playwright/audit-agent.mjs` qui utilise le même
 * pattern (chromium + page.screenshot).
 *
 * Usage :
 *   node tools/playwright/phase_3_4_capture.mjs --phase after
 *   PHASE_LABEL=before node tools/playwright/phase_3_4_capture.mjs
 *   BASE_URL=http://localhost:5175 PHASE_LABEL=after \
 *     node tools/playwright/phase_3_4_capture.mjs
 *
 * Pré-requis : frontend dev server sur BASE_URL + backend port 8001 actif.
 * Auth : DEMO_MODE=true → pas de login requis (cf CLAUDE.md).
 *
 * Output : frontend/tests/visual/snapshots/{phase}/{2xl|xl|lg}/*.png
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join, dirname } from 'path';

const VIEWPORTS = [
  { name: '2xl', width: 1440, height: 900 },
  { name: 'xl', width: 1280, height: 800 },
  { name: 'lg', width: 1024, height: 768 },
];

// Note : `?demo_state=*` n'est PAS encore implémenté dans CockpitJour.jsx
// (à activer Phase E si retenu par l'audit). Les états loading/empty/error/
// partial captureront donc le même rendu que `default` — c'est une finding
// connue, traçable dans la grille d'audit (critère 4.x).
const STATES = [
  { name: 'default', query: '' },
  { name: 'loading', query: '?demo_state=loading' },
  { name: 'empty', query: '?demo_state=empty' },
  { name: 'error', query: '?demo_state=error' },
  { name: 'partial', query: '?demo_state=partial' },
];

const PHASE_LABEL = process.env.PHASE_LABEL || process.argv.includes('--phase')
  ? (process.env.PHASE_LABEL || process.argv[process.argv.indexOf('--phase') + 1])
  : 'after';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5175';

const REPO_ROOT = resolve(new URL('.', import.meta.url).pathname, '..', '..');
const SNAP_ROOT = join(REPO_ROOT, 'frontend', 'tests', 'visual', 'snapshots', PHASE_LABEL);

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';
const AUTH_EMAIL = process.env.PROMEOS_AUTH_EMAIL || 'promeos@promeos.io';
const AUTH_PASSWORD = process.env.PROMEOS_AUTH_PASSWORD || 'promeos2024';

function ensureDir(filePath) {
  const dir = dirname(filePath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

async function capture({ page, vp, state }) {
  await page.setViewportSize(vp);
  const url = `${BASE_URL}/cockpit/jour${state.query}`;
  console.log(`  [${vp.name} / ${state.name}] goto ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded' });

  if (state.name === 'default') {
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(800);
  } else if (state.name === 'loading') {
    await page.waitForTimeout(400);
  } else {
    await page.waitForTimeout(600);
  }

  const dir = join(SNAP_ROOT, vp.name);
  const above = join(dir, `above-${state.name}.png`);
  const full = join(dir, `full-${state.name}.png`);
  ensureDir(above);
  await page.screenshot({ path: above, fullPage: false });
  await page.screenshot({ path: full, fullPage: true });
  console.log(`    ✓ above + full screenshots saved`);

  if (state.name === 'default') {
    const hero = page.locator('[data-component="SolHeroPremiumNight"]').first();
    if (await hero.count()) {
      await hero.screenshot({ path: join(dir, 'hero-zoom.png') });
      console.log(`    ✓ hero-zoom.png saved`);
    } else {
      console.warn(`    ⚠ no SolHeroPremiumNight found`);
    }

    const kpis = page.locator('[data-component="HubKpiCard"]');
    const kCount = await kpis.count();
    console.log(`    KPI cards: ${kCount}`);
    for (let i = 0; i < kCount; i++) {
      await kpis.nth(i).screenshot({ path: join(dir, `kpi-${i + 1}.png`) });
    }

    const highlights = page.locator('[data-component="HubHighlight"]');
    const hCount = await highlights.count();
    console.log(`    Highlights: ${hCount}`);
    for (let i = 0; i < hCount; i++) {
      await highlights.nth(i).screenshot({ path: join(dir, `highlight-${i + 1}.png`) });
    }

    // Phase F.2 — capture des variantes ChartFrame* (Bars + Line) pour
    // valider que les selecteurs trouvent bien les SVG extraits.
    const bars = page.locator('[data-component="ChartFrameBars"]');
    const barsCount = await bars.count();
    console.log(`    ChartFrameBars: ${barsCount}`);
    for (let i = 0; i < barsCount; i++) {
      await bars.nth(i).screenshot({ path: join(dir, `chart-bars-${i + 1}.png`) });
    }
    const lines = page.locator('[data-component="ChartFrameLine"]');
    const linesCount = await lines.count();
    console.log(`    ChartFrameLine: ${linesCount}`);
    for (let i = 0; i < linesCount; i++) {
      await lines.nth(i).screenshot({ path: join(dir, `chart-line-${i + 1}.png`) });
    }
  }
}

(async () => {
  console.log(`\n=== Phase 3.4 capture · PHASE_LABEL=${PHASE_LABEL} · BASE_URL=${BASE_URL} ===\n`);
  console.log(`Output dir: ${SNAP_ROOT}\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ deviceScaleFactor: 1, reducedMotion: 'reduce' });
  const page = await context.newPage();

  // Auth flow (aligné audit-agent.mjs) : POST /api/auth/login → token →
  // localStorage `promeos_token`. RequireAuth (App.jsx) lit ce flag pour
  // débloquer les routes protégées même en DEMO_MODE.
  console.log(`[AUTH] Login ${AUTH_EMAIL} via ${BASE_URL} proxy → backend…`);
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  // Use relative `/api/auth/login` so Vite proxy routes to backend without
  // CORS issue (audit-agent.mjs uses absolute URL but backend CORS now stricter).
  const loginResp = await page.evaluate(async ({ email, password }) => {
    const res = await fetch(`/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return res.json();
  }, { email: AUTH_EMAIL, password: AUTH_PASSWORD });

  if (!loginResp.access_token) {
    console.error('[AUTH] FAILED:', loginResp.detail || 'Unknown error');
    await browser.close();
    process.exit(1);
  }
  await page.evaluate((token) => {
    localStorage.setItem('promeos_token', token);
  }, loginResp.access_token);
  console.log(`[AUTH] OK — ${loginResp.user?.email || AUTH_EMAIL}\n`);

  let okCount = 0;
  let failCount = 0;
  for (const vp of VIEWPORTS) {
    console.log(`Viewport ${vp.name} ${vp.width}×${vp.height}:`);
    for (const state of STATES) {
      try {
        await capture({ page, vp, state });
        okCount++;
      } catch (err) {
        console.error(`  ✗ FAILED [${vp.name} / ${state.name}]:`, err.message);
        failCount++;
      }
    }
  }

  await browser.close();
  console.log(`\n=== Done · ${okCount} OK · ${failCount} failed ===\n`);
  process.exit(failCount ? 1 : 0);
})();
