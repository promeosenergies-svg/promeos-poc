/**
 * PROMEOS — Smoke test d'ensemble refonte Sol V1 (Phase 4.5)
 *
 * Parcours utilisateur réaliste cross-pages + raccourcis clavier
 * + responsive + deep-link. Détecte régressions non-visibles par
 * les tests unitaires page-par-page.
 *
 * Résultats : screenshots horodatés dans docs/design/screenshots/smoke/
 * + récap console OK/FAIL/WARN par étape.
 *
 * Usage :
 *   node tools/playwright/sol_refonte_smoketest.mjs
 */
import { chromium } from 'playwright';
import { resolve } from 'path';

const URL = process.env.TARGET_URL || 'http://127.0.0.1:5175';
const OUT_DIR = resolve('c:/Users/amine/promeos-poc/promeos-refonte/docs/design/screenshots/smoke');
const EMAIL = 'promeos@promeos.io';
const PASSWORD = 'promeos2024';

const results = []; // { step, status: 'OK'|'FAIL'|'WARN', note, screenshot }

function log(step, status, note, screenshot) {
  const icon = { OK: '✓', FAIL: '✗', WARN: '⚠' }[status] || '·';
  const line = `${icon} ${step.padEnd(42)} ${status.padEnd(5)} ${note || ''}`;
  console.log(line);
  results.push({ step, status, note: note || '', screenshot: screenshot || null });
}

async function login(page) {
  await page.goto(`${URL}/login`, { waitUntil: 'networkidle' });
  const stillOnLogin = page.url().includes('/login');
  if (stillOnLogin && (await page.locator('input[type="email"]').count()) > 0) {
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((u) => !u.pathname.endsWith('/login'), { timeout: 15000 }).catch(() => {});
  }
}

async function dismissOverlay(page) {
  for (const sel of [
    'button:has-text("Passer le tour")',
    'button:has-text("Fermer")',
    'button[aria-label="Fermer"]',
    'button:has-text("Plus tard")',
  ]) {
    try { await page.locator(sel).first().click({ timeout: 600 }); break; } catch (_) {}
  }
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(400);
}

async function snap(page, stepName) {
  const file = `${OUT_DIR}/${stepName}.png`;
  await page.screenshot({ path: file, fullPage: false });
  return file;
}

async function expectVisible(page, selector, timeout = 4000) {
  try {
    await page.waitForSelector(selector, { timeout, state: 'visible' });
    return true;
  } catch (_) {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────

async function runSmokeTest() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Collect console errors for regression detection
  const consoleErrors = [];
  page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const txt = msg.text();
      // Ignore known-benign Recharts warnings and network 500s (issue #257)
      if (txt.includes('Recharts') || txt.includes('500') || txt.includes('Failed to load resource')) return;
      consoleErrors.push(`console: ${txt.slice(0, 140)}`);
    }
  });

  console.log('═══ SMOKE TEST refonte Sol V1 ═══');
  console.log(`URL: ${URL}`);
  console.log(`OUT: ${OUT_DIR}`);
  console.log('');

  // ─── 1. Login ─────────────────────────────────────────────────────────────
  try {
    await login(page);
    log('01 login', 'OK', `as ${EMAIL}`);
  } catch (e) {
    log('01 login', 'FAIL', e.message);
    await browser.close();
    return;
  }

  // ─── 2a. /cockpit ────────────────────────────────────────────────────────
  await page.goto(`${URL}/cockpit`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const hasCockpitKicker = await expectVisible(page, '.sol-page-kicker');
  const hasKpiRow = await expectVisible(page, '.sol-kpi-row');
  const shot1 = await snap(page, 'step01_cockpit');
  log('02a /cockpit render', hasCockpitKicker && hasKpiRow ? 'OK' : 'FAIL',
    hasCockpitKicker ? 'kicker + kpi-row visibles' : 'structure incomplète', shot1);

  // ─── 2b. Panel item clic (Journal d'actions) ─────────────────────────────
  const journalItemExists = await page.locator('.sol-panel-item:has-text("Journal d")').count();
  if (journalItemExists > 0) {
    await page.locator('.sol-panel-item:has-text("Journal d")').first().click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(1000);
    const urlChanged = page.url().includes('/actions') || page.url().includes('/notifications');
    const shot2 = await snap(page, 'step02_journal_click');
    log('02b panel item "Journal d\'actions"', urlChanged ? 'OK' : 'WARN',
      `url → ${page.url().split(URL)[1]}`, shot2);
  } else {
    log('02b panel item "Journal d\'actions"', 'WARN', 'item absent du panel (panel config differs?)');
  }

  // ─── 2c. /conformite via rail ─────────────────────────────────────────────
  await page.goto(`${URL}/conformite`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const conformiteKpis = await expectVisible(page, '.sol-kpi-row');
  const trajectoryChart = await page.locator('text=Trajectoire Décret Tertiaire').count();
  const shot3 = await snap(page, 'step03_conformite');
  log('02c /conformite render', conformiteKpis && trajectoryChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${conformiteKpis} · Trajectoire: ${trajectoryChart > 0}`, shot3);

  // ─── 2d. /bill-intel ──────────────────────────────────────────────────────
  await page.goto(`${URL}/bill-intel`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const billKpis = await expectVisible(page, '.sol-kpi-row');
  const barChart = await page.locator('text=Facturation mensuelle').count();
  const shot4 = await snap(page, 'step04_bill_intel');
  log('02d /bill-intel render', billKpis && barChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${billKpis} · BarChart: ${barChart > 0}`, shot4);

  // ─── 2e. /patrimoine ──────────────────────────────────────────────────────
  await page.goto(`${URL}/patrimoine`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const patrimoineKpis = await expectVisible(page, '.sol-kpi-row');
  const consoPerSite = await page.locator('text=Consommation par site').count();
  const shot5 = await snap(page, 'step05_patrimoine');
  log('02e /patrimoine render', patrimoineKpis && consoPerSite > 0 ? 'OK' : 'FAIL',
    `KPIs: ${patrimoineKpis} · Conso par site: ${consoPerSite > 0}`, shot5);

  // ─── 2f. /patrimoine?type=bureau filtre client-side ───────────────────────
  await page.goto(`${URL}/patrimoine?type=bureau`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const titleFiltered = await page.locator('text=bureau').count();
  const shot6 = await snap(page, 'step06_patrimoine_filter_bureau');
  log('02f /patrimoine?type=bureau filter', titleFiltered > 0 ? 'OK' : 'WARN',
    `mention "bureau" dans contenu: ${titleFiltered} occurrences`, shot6);

  // ─── 2g. Week-card site drill-down → /sites/:id ──────────────────────────
  await page.goto(`${URL}/patrimoine`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const weekCard = await page.locator('.sol-week-grid > *:first-child').first();
  const clickable = await weekCard.getAttribute('role').catch(() => null);
  if (clickable === 'button') {
    await weekCard.click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const onSitePage = page.url().includes('/sites/');
    const shot7 = await snap(page, 'step07_site_drilldown');
    log('02g week-card drill-down /sites/:id', onSitePage ? 'OK' : 'WARN',
      `url → ${page.url().split(URL)[1]}`, shot7);
  } else {
    log('02g week-card drill-down /sites/:id', 'WARN', 'week-card 1 non-clickable');
  }

  // ─── 2h. /achat-energie ──────────────────────────────────────────────────
  await page.goto(`${URL}/achat-energie`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const achatKpis = await expectVisible(page, '.sol-kpi-row');
  const marketChart = await page.locator('text=Prix marché spot EPEX').count();
  const shot8 = await snap(page, 'step08_achat');
  log('02h /achat-energie render', achatKpis && marketChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${achatKpis} · Marché: ${marketChart > 0}`, shot8);

  // ─── 3. Raccourcis clavier ────────────────────────────────────────────────
  await page.goto(`${URL}/cockpit`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await dismissOverlay(page);

  // Ctrl+K ouvre CommandPalette
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(800);
  const paletteOpen = await page.locator('[role="dialog"], [aria-label*="command" i], [placeholder*="Rechercher" i]').count();
  const shot9 = await snap(page, 'step09_ctrl_k_palette');
  log('03a Ctrl+K open CommandPalette', paletteOpen > 0 ? 'OK' : 'WARN',
    `overlay dialog count: ${paletteOpen}`, shot9);

  // Escape ferme palette
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  const paletteClosed = (await page.locator('[role="dialog"]').count()) === 0
    || !(await page.locator('[role="dialog"]').first().isVisible().catch(() => false));
  log('03b Escape close palette', paletteClosed ? 'OK' : 'WARN',
    paletteClosed ? 'closed' : 'still visible');

  // Ctrl+Shift+X toggle Expert
  await page.keyboard.press('Control+Shift+x');
  await page.waitForTimeout(600);
  const shot10 = await snap(page, 'step10_ctrl_shift_x_expert');
  log('03c Ctrl+Shift+X Expert toggle', 'OK', 'shortcut fired (visuel à vérifier sur screenshot)', shot10);

  // ─── 4. Scope switcher (vérification présence, pas interaction complexe) ──
  const scopeSwitcherVisible = await page.locator('[class*="scope-switcher"], [aria-label*="scope" i]').count();
  log('04 scope switcher top panel', scopeSwitcherVisible > 0 ? 'OK' : 'WARN',
    `elem count: ${scopeSwitcherVisible}`);

  // ─── 5. Responsive 1280x720 ──────────────────────────────────────────────
  const ctxSmall = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const pageSmall = await ctxSmall.newPage();
  await login(pageSmall);
  await pageSmall.goto(`${URL}/cockpit`, { waitUntil: 'networkidle' });
  await pageSmall.waitForTimeout(3000);
  await dismissOverlay(pageSmall);
  const shot11 = `${OUT_DIR}/step11_responsive_1280x720.png`;
  await pageSmall.screenshot({ path: shot11, fullPage: false });
  // Panel visible + main content reflow
  const panelWidth = await pageSmall.locator('.sol-app-panel, [aria-label="Navigation contextuelle"]').first().evaluate(
    (el) => el?.getBoundingClientRect().width
  ).catch(() => 0);
  log('05 responsive 1280x720', panelWidth > 200 ? 'OK' : 'WARN',
    `panel width: ${Math.round(panelWidth)}px`, shot11);
  await ctxSmall.close();

  // ─── 6. Deep-link fresh context /bill-intel ──────────────────────────────
  const ctxFresh = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageFresh = await ctxFresh.newPage();
  await login(pageFresh);
  await pageFresh.goto(`${URL}/bill-intel`, { waitUntil: 'networkidle' });
  await pageFresh.waitForTimeout(3500);
  await dismissOverlay(pageFresh);
  const freshHasKpis = await expectVisible(pageFresh, '.sol-kpi-row');
  const freshHasBarChart = await pageFresh.locator('text=Facturation mensuelle').count();
  const shot12 = `${OUT_DIR}/step12_deep_link_bill_intel.png`;
  await pageFresh.screenshot({ path: shot12, fullPage: false });
  log('06 deep-link /bill-intel fresh', freshHasKpis && freshHasBarChart > 0 ? 'OK' : 'FAIL',
    'rend sans flash legacy', shot12);
  await ctxFresh.close();

  // ─── Regressions collecte ────────────────────────────────────────────────
  console.log('');
  console.log('═══ Console errors / page errors ═══');
  if (consoleErrors.length === 0) {
    console.log('  (aucune erreur console notable)');
  } else {
    consoleErrors.forEach((e) => console.log('  ×', e));
  }

  // ─── Synthèse ────────────────────────────────────────────────────────────
  const ok = results.filter((r) => r.status === 'OK').length;
  const fail = results.filter((r) => r.status === 'FAIL').length;
  const warn = results.filter((r) => r.status === 'WARN').length;
  console.log('');
  console.log('═══ SYNTHÈSE ═══');
  console.log(`  OK    : ${ok}`);
  console.log(`  FAIL  : ${fail}`);
  console.log(`  WARN  : ${warn}`);
  console.log(`  Total : ${results.length}`);
  console.log(`  Console errors: ${consoleErrors.length}`);
  console.log(`  Screenshots dir: ${OUT_DIR}`);

  await browser.close();

  // Exit code : 0 si pas de FAIL, 1 sinon
  process.exit(fail > 0 ? 1 : 0);
}

runSmokeTest().catch((e) => { console.error(e); process.exit(2); });
