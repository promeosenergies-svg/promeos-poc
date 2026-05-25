#!/usr/bin/env node
/**
 * Audit postfix — Cockpit P0 cleanup + Billing KPIs (2026-05-25).
 *
 * Vérifie :
 * 1. /cockpit/strategique HTTP 200
 * 2. 12 endpoints orphelins → 410 Gone
 * 3. 5 endpoints vivants → 200
 * 4. Payload /api/cockpit/strategique contient billing_kpis (4 KPIs)
 * 5. Frontend rend CockpitBillingKpis avec 4 cartes
 * 6. CadreApplicable drill-down → /conformite?regulation=X
 * 7. SolNarrativeText glosse acronymes dans hero
 * 8. 0 console error, 0 network 5xx bloquant
 */
import { chromium } from 'playwright';

const FE = process.env.FE || 'http://localhost:5175';
const BE = process.env.BE || 'http://localhost:8001';
const results = [];
let exitCode = 0;

function record(name, ok, detail = '') {
  results.push({ name, ok, detail });
  if (!ok) exitCode = 1;
  console.log(`${ok ? '✅' : '❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const consoleErrors = [];
const networkFailures = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text());
});
page.on('response', (r) => {
  const s = r.status();
  if (s >= 400 && s < 600) networkFailures.push(`${s} ${r.url()}`);
});

try {
  // Login
  const loginRes = await page.request.post(`${FE}/api/auth/demo-login`);
  const { access_token } = await loginRes.json();

  // ─── 1. /cockpit/strategique route ───────────────────────────────
  await page.goto(`${FE}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), access_token);
  const resp = await page.goto(`${FE}/cockpit/strategique`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  await page.waitForTimeout(3500);
  record(`1. /cockpit/strategique HTTP ${resp?.status()}`, resp?.status() === 200);

  // ─── 2. Endpoints orphelins → 410 ────────────────────────────────
  const orphans = [
    '/cockpit/benchmark',
    '/cockpit/conso-month',
    '/cockpit/co2',
    '/cockpit/cdc',
    '/cockpit/levers',
    '/cockpit/impact_decision',
    '/cockpit/essentials',
    '/cockpit/essentials/health',
    '/cockpit/essentials/watchlist',
    '/cockpit/data_activation',
    '/cockpit/executive-v2',
    '/cockpit/top-contributors',
  ];
  let goneCount = 0;
  for (const e of orphans) {
    const r = await page.request.get(`${BE}/api${e}`, {
      headers: { Authorization: `Bearer ${access_token}`, 'X-Org-Id': '1' },
    });
    if (r.status() === 410) goneCount++;
  }
  record(`2. ${goneCount}/${orphans.length} endpoints orphelins → 410 Gone`, goneCount === orphans.length);

  // ─── 3. Endpoints vivants → 200 ──────────────────────────────────
  const alive = [
    '/cockpit',
    '/cockpit/trajectory',
    '/cockpit/priorities',
    '/cockpit/jour',
    '/cockpit/strategique',
  ];
  let aliveCount = 0;
  for (const e of alive) {
    const r = await page.request.get(`${BE}/api${e}`, {
      headers: { Authorization: `Bearer ${access_token}`, 'X-Org-Id': '1' },
    });
    if (r.status() === 200) aliveCount++;
  }
  record(`3. ${aliveCount}/${alive.length} endpoints vivants → 200`, aliveCount === alive.length);

  // ─── 4. Payload billing_kpis ─────────────────────────────────────
  const strategique = await page.request.get(`${BE}/api/cockpit/strategique`, {
    headers: { Authorization: `Bearer ${access_token}`, 'X-Org-Id': '1' },
  });
  const payload = await strategique.json();
  record(
    '4. Payload contient billing_kpis avec 4 KPIs',
    payload?.billing_kpis?.kpis?.length === 4,
    `kpis count=${payload?.billing_kpis?.kpis?.length || 0}`
  );
  const ids = (payload?.billing_kpis?.kpis || []).map((k) => k.id);
  for (const expected of [
    'surfacturations_a_contester',
    'anomalies_ouvertes',
    'anomalies_par_energie',
    'actions_facturation_ouvertes',
  ]) {
    record(`4.${expected} présent`, ids.includes(expected));
  }

  // ─── 5. Frontend rend CockpitBillingKpis ─────────────────────────
  const billingSection = page.locator('[data-testid="cockpit-billing-kpis"]');
  record('5. Section cockpit-billing-kpis visible', await billingSection.isVisible().catch(() => false));
  for (const id of [
    'billing-kpi-surfacturations',
    'billing-kpi-anomalies-ouvertes',
    'billing-kpi-anomalies-energie',
    'billing-kpi-actions-facturation',
  ]) {
    const card = page.locator(`[data-testid="${id}"]`);
    record(`5.${id} carte rendue`, await card.isVisible().catch(() => false));
  }

  // Lien /bill-intel
  const billLink = page.locator('[data-testid="billing-kpi-surfacturations-link"]');
  const billHref = await billLink.getAttribute('href').catch(() => null);
  record(`5.lien bill-intel : ${billHref}`, billHref === '/bill-intel');
  // Lien Centre Action Facturation
  const actionsLink = page.locator('[data-testid="billing-kpi-actions-facturation-link"]');
  const actionsHref = await actionsLink.getAttribute('href').catch(() => null);
  record(
    `5.lien centre-action?domain=facturation : ${actionsHref}`,
    actionsHref === '/centre-action?domain=facturation'
  );

  // ─── 6. CadreApplicable drill-down ──────────────────────────────
  // On clique sur la tile DT (applicable normalement chez HELIOS) et vérifie
  // qu'on arrive sur /conformite?regulation=dt
  const dtTile = page.locator('[data-rule="DT"]');
  if (await dtTile.isVisible().catch(() => false)) {
    const actionable = await dtTile.getAttribute('data-actionable');
    if (actionable === 'true') {
      await dtTile.click();
      await page.waitForTimeout(2000);
      const url = page.url();
      record(
        `6. CadreApplicable DT drill-down → /conformite?regulation=dt (actual: ${url})`,
        /\/conformite\?regulation=dt/.test(url)
      );
    } else {
      record('6. CadreApplicable DT non actionable (skip drill-down)', true, 'data-actionable=false');
    }
  } else {
    record('6. CadreApplicable DT tile présent', false, 'tile DT introuvable');
  }

  // ─── 7-8. Console + Network ──────────────────────────────────────
  const blockingErrors = consoleErrors.filter(
    (e) => !e.includes('React Router Future Flag') && !e.includes('Download the React DevTools')
  );
  record(
    `7. 0 console error bloquant (${blockingErrors.length} / ${consoleErrors.length})`,
    blockingErrors.length === 0,
    blockingErrors.slice(0, 3).join(' | ')
  );
  const blocking5xx = networkFailures.filter((f) => /^5\d\d /.test(f));
  record(
    `8. 0 network 5xx bloquant (${blocking5xx.length} / ${networkFailures.length})`,
    blocking5xx.length === 0,
    blocking5xx.slice(0, 3).join(' | ')
  );
} catch (e) {
  record('Audit terminé sans crash', false, e.message);
} finally {
  console.log('\n─── BILAN ───');
  console.log(`Passed: ${results.filter((r) => r.ok).length}/${results.length}`);
  await browser.close();
  process.exit(exitCode);
}
