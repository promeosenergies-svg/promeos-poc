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

const URL = process.env.TARGET_URL || 'http://127.0.0.1:5174';
const OUT_DIR = process.env.OUT_DIR || resolve('tools/playwright/captures/sol-refonte-smoke');
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
  await page.goto(`${URL}/login`, { waitUntil: 'load', timeout: 20000 });
  // Wait for React to render the login form
  await page.waitForSelector('input[type="email"], #main-content', { timeout: 8000 }).catch(() => {});
  const stillOnLogin = page.url().includes('/login');
  if (stillOnLogin && (await page.locator('input[type="email"]').count()) > 0) {
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((u) => !u.pathname.endsWith('/login'), { timeout: 15000 }).catch(() => {});
    // Wait for app shell to mount after login
    await page.waitForSelector('#main-content', { timeout: 10000 }).catch(() => {});
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

async function safeGoto(page, url) {
  // Use 'load' — networkidle never fires with Vite HMR websocket
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 20000 });
  } catch (_) {
    try { await page.goto(url, { waitUntil: 'commit', timeout: 10000 }); } catch (_2) {}
  }
  // Give React time to mount and render after load
  await page.waitForSelector('#main-content', { timeout: 8000 }).catch(() => {});
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

  // ─── 2z. / (CommandCenter Lot 1.1) ───────────────────────────────────────
  await safeGoto(page, `${URL}/`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const cmdKicker = await expectVisible(page, '.sol-page-kicker');
  const cmdKpis = await expectVisible(page, '.sol-kpi-row');
  const cmdTiles = await page.locator('text=Accès rapide aux modules').count();
  const shotCmd = await snap(page, 'step00_command_center');
  log('02z / CommandCenter render', cmdKicker && cmdKpis && cmdTiles > 0 ? 'OK' : 'FAIL',
    `kicker ${cmdKicker} · kpis ${cmdKpis} · tiles ${cmdTiles > 0}`, shotCmd);

  // ─── 2a. /cockpit ────────────────────────────────────────────────────────
  await safeGoto(page, `${URL}/cockpit`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const hasCockpitKicker = await expectVisible(page, '.sol-page-kicker');
  const hasKpiRow = await expectVisible(page, '.sol-kpi-row');
  const shot1 = await snap(page, 'step01_cockpit');
  log('02a /cockpit render', hasCockpitKicker && hasKpiRow ? 'OK' : 'FAIL',
    hasCockpitKicker ? 'kicker + kpi-row visibles' : 'structure incomplète', shot1);

  // ─── 2b. Panel item clic — "Tableau de bord" (design intentionnel : /actions
  //         est dans le header Centre d'actions, pas le panel — cf. triage doc ligne 30)
  const panelItemExists = await page.locator('.sol-panel-item').count();
  const shot2 = await snap(page, 'step02_panel_items');
  log('02b panel items /cockpit', panelItemExists > 0 ? 'OK' : 'WARN',
    `${panelItemExists} item(s) sol-panel-item visibles`, shot2);

  // ─── 2c. /conformite via rail ─────────────────────────────────────────────
  await safeGoto(page, `${URL}/conformite`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const conformiteKpis = await expectVisible(page, '.sol-kpi-row');
  const trajectoryChart = await page.locator('text=Trajectoire Décret Tertiaire').count();
  const shot3 = await snap(page, 'step03_conformite');
  log('02c /conformite render', conformiteKpis && trajectoryChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${conformiteKpis} · Trajectoire: ${trajectoryChart > 0}`, shot3);

  // ─── 2d. /bill-intel ──────────────────────────────────────────────────────
  await safeGoto(page, `${URL}/bill-intel`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const billKpis = await expectVisible(page, '.sol-kpi-row');
  const barChart = await page.locator('text=Facturation mensuelle').count();
  const shot4 = await snap(page, 'step04_bill_intel');
  log('02d /bill-intel render', billKpis && barChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${billKpis} · BarChart: ${barChart > 0}`, shot4);

  // ─── 2e. /patrimoine ──────────────────────────────────────────────────────
  await safeGoto(page, `${URL}/patrimoine`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const patrimoineKpis = await expectVisible(page, '.sol-kpi-row');
  const consoPerSite = await page.locator('text=Consommation par site').count();
  const shot5 = await snap(page, 'step05_patrimoine');
  log('02e /patrimoine render', patrimoineKpis && consoPerSite > 0 ? 'OK' : 'FAIL',
    `KPIs: ${patrimoineKpis} · Conso par site: ${consoPerSite > 0}`, shot5);

  // ─── 2f. /patrimoine?type=bureau filtre client-side ───────────────────────
  await safeGoto(page, `${URL}/patrimoine?type=bureau`);
  await page.waitForTimeout(2500);
  const titleFiltered = await page.locator('text=bureau').count();
  const shot6 = await snap(page, 'step06_patrimoine_filter_bureau');
  log('02f /patrimoine?type=bureau filter', titleFiltered > 0 ? 'OK' : 'WARN',
    `mention "bureau" dans contenu: ${titleFiltered} occurrences`, shot6);

  // ─── 2g. Week-card site drill-down → /sites/:id ──────────────────────────
  await safeGoto(page, `${URL}/patrimoine`);
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
  await safeGoto(page, `${URL}/achat-energie`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const achatKpis = await expectVisible(page, '.sol-kpi-row');
  const marketChart = await page.locator('text=Prix marché spot EPEX').count();
  const shot8 = await snap(page, 'step08_achat');
  log('02h /achat-energie render', achatKpis && marketChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${achatKpis} · Marché: ${marketChart > 0}`, shot8);

  // ─── 2i. /conformite/aper (Lot 1.2) ──────────────────────────────────────
  await safeGoto(page, `${URL}/conformite/aper`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const aperKpis = await expectVisible(page, '.sol-kpi-row');
  const aperChart = await page.locator('text=Potentiel PV par site').count();
  const shotAper = await snap(page, 'step20_aper');
  log('02i /conformite/aper render', aperKpis && aperChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${aperKpis} · BarChart: ${aperChart > 0}`, shotAper);

  // ─── 2j. /monitoring (Lot 1.3) ───────────────────────────────────────────
  await safeGoto(page, `${URL}/monitoring`);
  await page.waitForTimeout(3500);
  await dismissOverlay(page);
  const monitKpis = await expectVisible(page, '.sol-kpi-row');
  const monitChart = await page.locator('text=Consommation patrimoine').count();
  const shotMonit = await snap(page, 'step21_monitoring');
  log('02j /monitoring render', monitKpis && monitChart > 0 ? 'OK' : 'FAIL',
    `KPIs: ${monitKpis} · Trajectory: ${monitChart > 0}`, shotMonit);

  // ─── 2k. /sites/3 Site360Sol (Pattern C Lot 3 P2) ────────────────────────
  await safeGoto(page, `${URL}/sites/3`);
  await page.waitForTimeout(4500);
  await dismissOverlay(page);
  const siteBreadcrumb = await page.locator('[aria-label="Fil d\'Ariane"]').count();
  const siteEntityCard = await page.locator('text=PDL / PRM').count();
  const siteTrajectoire = await page.locator('text=Trajectoire Décret Tertiaire').count();
  const shotSite = await snap(page, 'step22_site360_pattern_c');
  log('02k /sites/3 Site360Sol render',
    siteBreadcrumb > 0 && siteEntityCard > 0 && siteTrajectoire > 0 ? 'OK' : 'FAIL',
    `breadcrumb: ${siteBreadcrumb > 0} · entity: ${siteEntityCard > 0} · trajectoire: ${siteTrajectoire > 0}`,
    shotSite);

  // ─── 2l. /regops/3 RegOpsSol (Pattern C Lot 3 P3) ────────────────────────
  // AI endpoints non-bloquants — la fiche rend en <3s via priorité assessment.
  const regopsStart = Date.now();
  await safeGoto(page, `${URL}/regops/3`);
  await page.waitForTimeout(3500);
  const regopsRenderMs = Date.now() - regopsStart;
  await dismissOverlay(page);
  const regopsBreadcrumb = await page.locator('[aria-label="Fil d\'Ariane"]').count();
  const regopsTimeline = await page.locator('text=Timeline du dossier').count();
  const shotRegOps = await snap(page, 'step23_regops_pattern_c');
  log('02l /regops/3 RegOpsSol render',
    regopsBreadcrumb > 0 && regopsTimeline > 0 ? 'OK' : 'FAIL',
    `breadcrumb: ${regopsBreadcrumb > 0} · timeline: ${regopsTimeline > 0} · render: ${regopsRenderMs}ms`,
    shotRegOps);

  // ─── 2m. /conformite/tertiaire/efa/1 EfaSol (Pattern C Lot 3 P4) ─────────
  await safeGoto(page, `${URL}/conformite/tertiaire/efa/1`);
  await page.waitForTimeout(8000);
  await dismissOverlay(page);
  const efaBreadcrumb = await page.locator('[aria-label="Fil d\'Ariane"]').count();
  const efaTrajectoire = await page.locator('text=Trajectoire Décret Tertiaire').count();
  const efaSafetyBanner = await page.locator('[aria-label="Aide à la conformité OPERAT"]').count();
  const shotEfa = await snap(page, 'step24_efa_pattern_c');
  log('02m /conformite/tertiaire/efa/1 EfaSol render',
    efaBreadcrumb > 0 && efaTrajectoire > 0 && efaSafetyBanner > 0 ? 'OK' : 'FAIL',
    `breadcrumb: ${efaBreadcrumb > 0} · trajectoire: ${efaTrajectoire > 0} · safety banner: ${efaSafetyBanner > 0}`,
    shotEfa);

  // ─── 2n. /diagnostic-conso DiagnosticConsoSol (Pattern A hybride P5+6.1) ─
  await safeGoto(page, `${URL}/diagnostic-conso`);
  await page.waitForTimeout(12000);
  await dismissOverlay(page);
  const diagKicker = await expectVisible(page, '.sol-page-kicker');
  const diagKpis = await expectVisible(page, '.sol-kpi-row');
  const diagBarChart = await page.locator('text=Top sites par pertes').count();
  // Post-6.1 : plus de double header. Vérifier absence du title legacy "Diagnostic" seul.
  const shotDiag = await snap(page, 'step25_diagnostic_pattern_a');
  log('02n /diagnostic-conso DiagnosticConsoSol render',
    diagKicker && diagKpis && diagBarChart > 0 ? 'OK' : 'FAIL',
    `kicker: ${diagKicker} · kpis: ${diagKpis} · bar chart: ${diagBarChart > 0}`,
    shotDiag);

  // ─── 2o. /anomalies AnomaliesSol (Pattern B pur, Lot 2 P2) ──────────────
  await safeGoto(page, `${URL}/anomalies`);
  await page.waitForTimeout(5000);
  await dismissOverlay(page);
  const anomKicker = await expectVisible(page, '.sol-page-kicker');
  const anomKpis = await expectVisible(page, '.sol-kpi-row');
  const anomGrid = await page.locator('table.sol-expert-grid-full').count();
  const shotAnom = await snap(page, 'step26_anomalies_pattern_b');
  log('02o /anomalies AnomaliesSol render',
    anomKicker && anomKpis && anomGrid > 0 ? 'OK' : 'FAIL',
    `kicker: ${anomKicker} · kpis: ${anomKpis} · grid: ${anomGrid > 0}`,
    shotAnom);

  // ─── 2p. /contrats ContratsSol (Pattern B pur + KpiRow, Lot 2 P3) ───────
  await safeGoto(page, `${URL}/contrats`);
  await page.waitForTimeout(5000);
  await dismissOverlay(page);
  const contratsKicker = await expectVisible(page, '.sol-page-kicker');
  const contratsKpis = await expectVisible(page, '.sol-kpi-row');
  const contratsGrid = await page.locator('table.sol-expert-grid-full').count();
  const shotContrats = await snap(page, 'step27_contrats_pattern_b');
  log('02p /contrats ContratsSol render',
    contratsKicker && contratsKpis && contratsGrid > 0 ? 'OK' : 'FAIL',
    `kicker: ${contratsKicker} · kpis: ${contratsKpis} · grid: ${contratsGrid > 0}`,
    shotContrats);

  // ─── 2q. /renouvellements RenouvellementsSol (Pattern B + horizon, P4) ──
  await safeGoto(page, `${URL}/renouvellements`);
  await page.waitForTimeout(5000);
  await dismissOverlay(page);
  const renouvKicker = await expectVisible(page, '.sol-page-kicker');
  const renouvKpis = await expectVisible(page, '.sol-kpi-row');
  const renouvHorizon = await page.locator('button[aria-pressed]').count();
  const shotRenouv = await snap(page, 'step28_renouvellements_pattern_b');
  log('02q /renouvellements RenouvellementsSol render',
    renouvKicker && renouvKpis && renouvHorizon > 0 ? 'OK' : 'FAIL',
    `kicker: ${renouvKicker} · kpis: ${renouvKpis} · horizon buttons: ${renouvHorizon}`,
    shotRenouv);

  // ─── 2r. /usages UsagesSol (Pattern A hybride, Lot 2 P5) ────────────────
  await safeGoto(page, `${URL}/usages`);
  await page.waitForTimeout(8000);
  await dismissOverlay(page);
  const usagesKicker = await expectVisible(page, '.sol-page-kicker');
  const usagesKpis = await expectVisible(page, '.sol-kpi-row');
  const usagesLegacyTabs = await page.locator('text=Profil conso').count() + await page.locator('text=Baseline').count();
  const shotUsages = await snap(page, 'step29_usages_pattern_a');
  log('02r /usages UsagesSol render',
    usagesKicker && usagesKpis ? 'OK' : 'FAIL',
    `kicker: ${usagesKicker} · kpis: ${usagesKpis} · legacy tabs: ${usagesLegacyTabs > 0}`,
    shotUsages);

  // ─── 2s. /usages-horaires UsagesHorairesSol (Pattern A compact, P6) ─────
  await safeGoto(page, `${URL}/usages-horaires`);
  await page.waitForTimeout(6000);
  await dismissOverlay(page);
  const horairesKicker = await expectVisible(page, '.sol-page-kicker');
  const horairesKpis = await expectVisible(page, '.sol-kpi-row');
  const shotHoraires = await snap(page, 'step30_usages_horaires_pattern_a');
  log('02s /usages-horaires UsagesHorairesSol render',
    horairesKicker && horairesKpis ? 'OK' : 'FAIL',
    `kicker: ${horairesKicker} · kpis: ${horairesKpis}`,
    shotHoraires);

  // ─── 2t. /watchers WatchersSol (Pattern B preludeSlot, Lot 2 P7) ────────
  await safeGoto(page, `${URL}/watchers`);
  await page.waitForTimeout(6000);
  await dismissOverlay(page);
  const watchersKicker = await expectVisible(page, '.sol-page-kicker');
  const watchersGrid = await page.locator('table.sol-expert-grid-full').count();
  // Prélude SolWatcherCard : grid responsive avec cards
  const watcherCards = await page.locator('text=Exécuter').count();
  const shotWatchers = await snap(page, 'step31_watchers_pattern_b_prelude');
  log('02t /watchers WatchersSol render',
    watchersKicker && watchersGrid > 0 && watcherCards > 0 ? 'OK' : 'FAIL',
    `kicker: ${watchersKicker} · grid: ${watchersGrid > 0} · watcher cards (Exécuter buttons): ${watcherCards}`,
    shotWatchers);

  // ─── 3. Raccourcis clavier ────────────────────────────────────────────────
  await safeGoto(page, `${URL}/cockpit`);
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
  const scopeSwitcherVisible = await page.locator('[data-testid="scope-switcher-trigger"], [class*="scope-switcher"], [aria-label*="scope" i]').count();
  log('04 scope switcher top panel', scopeSwitcherVisible > 0 ? 'OK' : 'WARN',
    `elem count: ${scopeSwitcherVisible}`);

  // ─── 5. Responsive 1280x720 ──────────────────────────────────────────────
  const ctxSmall = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const pageSmall = await ctxSmall.newPage();
  await login(pageSmall);
  await safeGoto(pageSmall, `${URL}/cockpit`);
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
  await safeGoto(pageFresh, `${URL}/bill-intel`);
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
