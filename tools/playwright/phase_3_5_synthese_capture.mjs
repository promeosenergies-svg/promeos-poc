/**
 * PROMEOS — Phase 3.5 Synthèse Stratégique capture initiale.
 *
 * Capture les 3 modes prioritaires de /cockpit/strategique sur 3 viewports
 * (lg 1280 / 2xl 1536 / 4xl 1920). Permet la boucle d'audit visuel vs
 * maquettes de référence synthese_v7.html (REGULATORY) + synthese_v8.html
 * (PERFORMANCE) + catalogue_5_modes.html (DATA_INSUFFICIENT).
 *
 * Hypothèses environnement :
 *   - backend tourne sur http://localhost:8001 (PROMEOS_DEMO_MODE=true)
 *   - frontend tourne sur http://localhost:5175 (refonte-sol2)
 *   - seed HELIOS et MERIDIAN appliqués pour rendre REGULATORY + PERFORMANCE
 *
 * Usage :
 *   node tools/playwright/phase_3_5_synthese_capture.mjs
 *
 * Variables :
 *   PHASE_LABEL  — défaut "after_p35" → snapshots/after_p35/
 *   BASE_URL     — défaut http://localhost:5175
 *   BACKEND_URL  — défaut http://localhost:8001
 */

import { chromium } from 'playwright';
import { dirname, join, resolve } from 'path';
import { existsSync, mkdirSync } from 'fs';

const VIEWPORTS = [
  { name: '4xl', width: 1920, height: 1080 },
  { name: '2xl', width: 1536, height: 960 },
  { name: 'lg', width: 1280, height: 800 },
];

// 3 modes capturés Phase 3.5 (cf. ADR-023 + Phase 0 Q3 décision Amine).
// Chaque mode est obtenu en fonction du seed actif (HELIOS / MERIDIAN /
// onboarding vide). Pour forcer un mode spécifique sans toucher la DB, on
// pourrait passer un query param mode_override=X, mais ce n'est PAS implémenté
// (anti-pattern AP-stratX2). On capture donc l'état actuel du seed live.
const SCENARIOS = [
  { name: 'default', query: '' },
  { name: 'legacy', query: '?legacy=1' }, // smoke échappatoire legacy
];

const PHASE_LABEL = process.env.PHASE_LABEL || 'after_p35';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5175';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';
const AUTH_EMAIL = process.env.PROMEOS_AUTH_EMAIL || 'promeos@promeos.io';
const AUTH_PASSWORD = process.env.PROMEOS_AUTH_PASSWORD || 'promeos2024';

const REPO_ROOT = resolve(new URL('.', import.meta.url).pathname, '..', '..');
const SNAP_ROOT = join(REPO_ROOT, 'frontend', 'tests', 'visual', 'snapshots', PHASE_LABEL);

function ensureDir(filePath) {
  const dir = dirname(filePath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

async function capture({ page, vp, scenario }) {
  await page.setViewportSize(vp);
  const url = `${BASE_URL}/cockpit/strategique${scenario.query}`;
  console.log(`  [${vp.name} / ${scenario.name}] goto ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(1000);

  // Détecte le mode actif via data-mode
  let mode = 'unknown';
  try {
    mode = await page.evaluate(() => {
      const root = document.querySelector('[data-page="cockpit-strategique"]');
      return root?.getAttribute('data-mode') || 'unknown';
    });
  } catch {
    // ignore
  }

  const dir = join(SNAP_ROOT, vp.name);
  const baseName = scenario.name === 'default' ? mode : scenario.name;
  const above = join(dir, `above-${baseName}.png`);
  const full = join(dir, `full-${baseName}.png`);
  ensureDir(above);
  await page.screenshot({ path: above, fullPage: false });
  await page.screenshot({ path: full, fullPage: true });
  console.log(`    ✓ mode=${mode} · above + full saved`);

  if (scenario.name === 'default') {
    // Zoom hero
    const hero = page.locator('[data-component="SolHeroPremiumNight"]').first();
    if (await hero.count()) {
      await hero.screenshot({ path: join(dir, `hero-${mode}.png`) });
    }
    // Zoom cadre applicable
    const cadre = page.locator('[data-component="CadreApplicable"]').first();
    if (await cadre.count()) {
      await cadre.screenshot({ path: join(dir, `cadre-${mode}.png`) });
    }
    // Zoom mode banner
    const banner = page.locator('[data-component="StrategicModeBanner"]').first();
    if (await banner.count()) {
      await banner.screenshot({ path: join(dir, `banner-${mode}.png`) });
    }
    // Zoom dossier P1
    const dossier = page.locator('[data-component="DossierP1"]').first();
    if (await dossier.count()) {
      await dossier.screenshot({ path: join(dir, `dossier-p1-${mode}.png`) });
    }
    // Zoom verdict
    const verdict = page.locator('[data-component="VerdictFinal"]').first();
    if (await verdict.count()) {
      await verdict.screenshot({ path: join(dir, `verdict-${mode}.png`) });
    }
    // Zoom KPI individuels
    const kpis = page.locator('[data-component="HubKpiCard"]');
    const kCount = await kpis.count();
    for (let i = 0; i < kCount; i++) {
      await kpis.nth(i).screenshot({ path: join(dir, `kpi-${i + 1}-${mode}.png`) });
    }
  }

  return mode;
}

async function main() {
  console.log(`PROMEOS Phase 3.5 capture — BASE=${BASE_URL} BACKEND=${BACKEND_URL}`);
  console.log(`Snapshot root: ${SNAP_ROOT}`);

  // Sanity check backend
  try {
    const resp = await fetch(`${BACKEND_URL}/api/health`).catch(() => null);
    if (!resp || !resp.ok) {
      console.warn(`⚠ backend /api/health not reachable on ${BACKEND_URL}`);
    } else {
      console.log(`✓ backend health OK`);
    }
  } catch {
    console.warn(`⚠ backend probe failed`);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') console.warn(`  [browser-error] ${msg.text().slice(0, 200)}`);
  });

  // Login DEMO (DEMO_MODE lenient backend, mais frontend route requiert auth)
  console.log(`\nLogin DEMO ${AUTH_EMAIL}…`);
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(300);
  try {
    await page.fill('input[type="email"]', AUTH_EMAIL);
    await page.fill('input[type="password"]', AUTH_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !String(url).includes('/login'), { timeout: 8000 });
    console.log(`  ✓ logged in → ${page.url()}`);
  } catch (err) {
    console.warn(`  ⚠ login failed (${err.message.slice(0, 100)}) — captures will likely show login page`);
  }

  for (const vp of VIEWPORTS) {
    console.log(`\nViewport ${vp.name} (${vp.width}x${vp.height})`);
    for (const scenario of SCENARIOS) {
      await capture({ page, vp, scenario });
    }
  }

  await browser.close();
  console.log(`\n✅ Capture Phase 3.5 terminée. Snapshots dans ${SNAP_ROOT}`);
}

main().catch((err) => {
  console.error('❌ Capture failed:', err);
  process.exit(1);
});
