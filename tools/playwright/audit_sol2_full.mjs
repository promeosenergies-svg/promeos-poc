/**
 * Audit complet refonte-sol2 — runtime browser réel
 *
 * Couvre 10 routes principales : login → /cockpit/strategique →
 * /cockpit/decision → /cockpit/pilotage → /conformite → /command-center
 * → /anomalies → /achat → /factures → /flexibilite → /actions
 *
 * Capture pour chaque route :
 *  - Console errors (filtré : pas de favicon/preload/source-map)
 *  - Page errors (uncaught)
 *  - Network failures (status >= 400)
 *  - Network /api 404 (regression bug double-prefix)
 *  - Latence moyenne /api
 *  - Screenshot full page
 *
 * Usage:
 *   PROMEOS_FRONTEND_URL=http://localhost:5175 PROMEOS_BACKEND_URL=http://localhost:8001 node tools/playwright/audit_sol2_full.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const BACKEND_URL = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const OUT_DIR = resolve(process.cwd(), 'tools/playwright/captures/audit_sol2_full');
const VIEWPORT = { width: 1440, height: 900 };

if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const ROUTES_TO_AUDIT = [
  { path: '/cockpit/strategique', label: 'cockpit_strategique' },
  { path: '/cockpit/decision', label: 'cockpit_decision' },
  { path: '/cockpit/pilotage', label: 'cockpit_pilotage' },
  { path: '/conformite', label: 'conformite' },
  { path: '/command-center', label: 'command_center' },
  { path: '/anomalies', label: 'anomalies_hub' },
  { path: '/achat', label: 'achat' },
  { path: '/factures', label: 'factures' },
  { path: '/flexibilite', label: 'flexibilite' },
  { path: '/actions', label: 'actions' },
];

function isRealConsoleError(text) {
  if (/Failed to load resource.*favicon/i.test(text)) return false;
  if (/preload.*was not used/i.test(text)) return false;
  if (/source map/i.test(text)) return false;
  if (/DevTools/i.test(text)) return false;
  return true;
}

(async () => {
  console.log(`[audit] FE=${FRONTEND_URL} BE=${BACKEND_URL}`);
  console.log(`[audit] OUT=${OUT_DIR}`);
  console.log(`[audit] ${ROUTES_TO_AUDIT.length} routes à auditer\n`);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();

  // Login one time
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'load', timeout: 60_000 });
  await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 20_000 });
  await page.fill('input[type="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20_000 });
  await page.waitForTimeout(2000);
  console.log(`[audit] login OK → ${page.url()}\n`);

  const routeReports = [];

  for (const { path, label } of ROUTES_TO_AUDIT) {
    const consoleErrors = [];
    const consoleWarnings = [];
    const pageErrors = [];
    const networkRequests = []; // { url, status, durMs }
    const network404s = [];
    const networkApiCalls = [];
    const requestTimings = new Map();

    const onConsole = (msg) => {
      if (msg.type() === 'error' && isRealConsoleError(msg.text())) {
        consoleErrors.push({ text: msg.text().slice(0, 300), location: msg.location() });
      } else if (msg.type() === 'warning' && isRealConsoleError(msg.text())) {
        consoleWarnings.push({ text: msg.text().slice(0, 300) });
      }
    };
    const onPageError = (err) => {
      pageErrors.push({ message: err.message.slice(0, 300), stack: (err.stack || '').slice(0, 500) });
    };
    const onRequest = (req) => {
      requestTimings.set(req, Date.now());
    };
    const onResponse = (resp) => {
      const req = resp.request();
      const t0 = requestTimings.get(req);
      const dur = t0 ? Date.now() - t0 : -1;
      const status = resp.status();
      const url = req.url();
      const entry = { url, status, durMs: dur, method: req.method() };
      networkRequests.push(entry);
      if (url.includes('/api/')) networkApiCalls.push(entry);
      if (status >= 400) network404s.push(entry);
      requestTimings.delete(req);
    };

    page.on('console', onConsole);
    page.on('pageerror', onPageError);
    page.on('request', onRequest);
    page.on('response', onResponse);

    let navStatus = 'OK';
    let navError = '';
    try {
      await page.goto(FRONTEND_URL + path, { waitUntil: 'load', timeout: 30_000 });
      await page.waitForTimeout(3000); // settle async fetches
    } catch (e) {
      navStatus = 'NAV_FAIL';
      navError = e.message.slice(0, 200);
    }

    const shotPath = join(OUT_DIR, `${label}.png`);
    try {
      await page.screenshot({ path: shotPath, fullPage: true });
    } catch (e) {
      // ignore screenshot fail
    }

    // Detach listeners
    page.off('console', onConsole);
    page.off('pageerror', onPageError);
    page.off('request', onRequest);
    page.off('response', onResponse);

    const apiAvgLatency = networkApiCalls.length
      ? Math.round(
          networkApiCalls.reduce((s, r) => s + Math.max(r.durMs, 0), 0) / networkApiCalls.length,
        )
      : 0;
    const apiP95Latency = (() => {
      if (!networkApiCalls.length) return 0;
      const sorted = networkApiCalls.map((r) => Math.max(r.durMs, 0)).sort((a, b) => a - b);
      return sorted[Math.floor(sorted.length * 0.95)] || sorted[sorted.length - 1];
    })();

    // Detect /api/api/* (double prefix anti-regression)
    const doublePrefix = networkApiCalls.filter((r) => r.url.includes('/api/api/'));

    const report = {
      route: path,
      label,
      navStatus,
      navError,
      console_errors: consoleErrors.length,
      console_warnings: consoleWarnings.length,
      page_errors: pageErrors.length,
      api_calls_total: networkApiCalls.length,
      api_calls_404plus: network404s.length,
      api_avg_latency_ms: apiAvgLatency,
      api_p95_latency_ms: apiP95Latency,
      double_prefix_404: doublePrefix.length,
      sample_console_errors: consoleErrors.slice(0, 5),
      sample_page_errors: pageErrors.slice(0, 3),
      sample_404s: network404s.slice(0, 5).map((r) => ({ url: r.url.replace(BACKEND_URL, '').replace(FRONTEND_URL, ''), status: r.status, method: r.method })),
      double_prefix_samples: doublePrefix.slice(0, 3).map((r) => r.url),
      screenshot: shotPath,
    };
    routeReports.push(report);

    const tag =
      navStatus !== 'OK'
        ? 'KO_NAV'
        : pageErrors.length > 0
          ? 'KO_RUNTIME'
          : consoleErrors.length > 0
            ? 'WARN_CONSOLE'
            : network404s.length > 0
              ? 'WARN_404'
              : 'OK';

    console.log(
      `[${tag.padEnd(13)}] ${path.padEnd(28)} api=${networkApiCalls.length}/${apiAvgLatency}ms p95=${apiP95Latency}ms err=${consoleErrors.length} 4xx=${network404s.length} doubleP=${doublePrefix.length}`,
    );
  }

  // Synthèse
  const totalConsole = routeReports.reduce((s, r) => s + r.console_errors, 0);
  const totalPageErr = routeReports.reduce((s, r) => s + r.page_errors, 0);
  const totalApi404 = routeReports.reduce((s, r) => s + r.api_calls_404plus, 0);
  const totalDoublePrefix = routeReports.reduce((s, r) => s + r.double_prefix_404, 0);
  const totalApi = routeReports.reduce((s, r) => s + r.api_calls_total, 0);
  const totalNavFail = routeReports.filter((r) => r.navStatus !== 'OK').length;

  const synth = {
    generated_at: new Date().toISOString(),
    branch: 'claude/refonte-sol2',
    routes_audited: ROUTES_TO_AUDIT.length,
    nav_failures: totalNavFail,
    total_console_errors: totalConsole,
    total_page_errors: totalPageErr,
    total_api_calls: totalApi,
    total_api_4xx: totalApi404,
    total_double_prefix_violations: totalDoublePrefix,
    routes: routeReports,
  };

  const reportPath = join(OUT_DIR, 'audit_sol2_full_report.json');
  writeFileSync(reportPath, JSON.stringify(synth, null, 2));

  console.log(`\n══════════ SYNTHÈSE AUDIT SOL2 FULL ══════════`);
  console.log(`Routes auditées        : ${ROUTES_TO_AUDIT.length}`);
  console.log(`Nav failures           : ${totalNavFail}`);
  console.log(`Page errors (uncaught) : ${totalPageErr}`);
  console.log(`Console errors total   : ${totalConsole}`);
  console.log(`API calls total        : ${totalApi}`);
  console.log(`API 4xx+ total         : ${totalApi404}`);
  console.log(`Double prefix /api/api : ${totalDoublePrefix}`);
  console.log(`\nRapport JSON: ${reportPath}`);

  await ctx.close();
  await browser.close();

  process.exitCode = totalPageErr > 0 || totalDoublePrefix > 0 || totalNavFail > 0 ? 1 : 0;
})();
