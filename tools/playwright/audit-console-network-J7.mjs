/**
 * Audit J+7 — Console errors + API network failures
 * Adapté pour PROMEOS audit post-merge PR #264
 * Remplace le script tools/playwright/audit-console-network.mjs absent du repo
 */
import { createRequire } from 'module';
const _require = createRequire(import.meta.url);
const { chromium } = _require('/opt/node22/lib/node_modules/playwright');
import { writeFileSync, mkdirSync } from 'fs';
import { resolve } from 'path';

const FRONTEND = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const BACKEND  = process.env.PROMEOS_BACKEND_URL  || 'http://localhost:8001';
const OUT_DIR  = process.env.AUDIT_OUT_DIR || resolve('/home/user/promeos-poc/audit/v6/console-network-J7');
mkdirSync(OUT_DIR, { recursive: true });

// 36 routes à auditer — extraites de App.jsx (PR #264 HEAD)
const ROUTES = [
  '/',
  '/cockpit',
  '/conformite',
  '/bill-intel',
  '/billing',
  '/achat-energie',
  '/monitoring',
  '/import',
  '/connectors',
  '/kb',
  '/notifications',
  '/watchers',
  '/patrimoine',
  '/sites',
  '/activation',
  '/actions',
  '/admin/users',
  '/admin/roles',
  '/admin/assignments',
  '/admin/audit',
  '/profile',
  '/settings',
  '/help',
  // Redirects P0 (M-05 : /energy-copilot → /cockpit)
  '/energy-copilot',
  // Consommations nested
  '/consommations',
  '/consommations/portfolio',
  // Conformite sub-pages
  '/conformite/aper',
  '/conformite/bacs',
  '/conformite/audit',
  // Pilotage
  '/pilotage',
  // Sites detail
  '/sites/1',
  // KB
  '/kb/items',
  // Error boundary (404)
  '/page-qui-nexiste-pas',
  // Import
  '/import/upload',
  // Billing detail
  '/billing/invoices',
  // admin kb-metrics
  '/admin/kb-metrics',
];

const IGNORED_CONSOLE_PATTERNS = [
  /ERR_CERT_AUTHORITY_INVALID/i,
  /Download the React DevTools/i,
  /ResizeObserver loop/i,
  /favicon/i,
];

const IGNORED_NETWORK_PATTERNS = [
  /chrome-extension/,
  /localhost:\d+\/favicon/,
];

async function getToken() {
  const res = await fetch(`${BACKEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
  });
  if (!res.ok) throw new Error(`Auth failed: ${res.status}`);
  const data = await res.json();
  return data.token || data.access_token;
}

async function auditRoute(page, route) {
  const consoleErrors = [];
  const networkFails = [];

  const consoleHandler = (msg) => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      const text = msg.text();
      if (!IGNORED_CONSOLE_PATTERNS.some(p => p.test(text))) {
        consoleErrors.push({ type: msg.type(), text });
      }
    }
  };

  const responseHandler = (response) => {
    const url = response.url();
    if (IGNORED_NETWORK_PATTERNS.some(p => p.test(url))) return;
    const status = response.status();
    if (status >= 400 && url.includes('/api/')) {
      networkFails.push({ url, status });
    }
  };

  page.on('console', consoleHandler);
  page.on('response', responseHandler);

  let crashed = false;
  let crashMessage = null;
  let timedOut = false;

  try {
    const resp = await page.goto(`${FRONTEND}${route}`, {
      waitUntil: 'networkidle',
      timeout: 15000,
    });

    await page.waitForTimeout(2000);

    // Detect React ErrorBoundary
    const errorBoundary = await page.locator('text=/something went wrong|une erreur est survenue|ErrorBoundary/i').count();
    if (errorBoundary > 0) {
      crashed = true;
      crashMessage = 'React ErrorBoundary visible';
    }
  } catch (e) {
    if (e.message.includes('Timeout')) {
      timedOut = true;
    } else {
      crashed = true;
      crashMessage = e.message.slice(0, 200);
    }
  }

  page.off('console', consoleHandler);
  page.off('response', responseHandler);

  const status = (crashed || consoleErrors.length > 0 || networkFails.length > 0) ? 'KO' : 'OK';

  return {
    route,
    status,
    console_errors: consoleErrors,
    network_fails: networkFails,
    crashed,
    crash_message: crashMessage,
    timed_out: timedOut,
  };
}

async function run() {
  const startedAt = new Date().toISOString();
  console.log(`[AUDIT J+7] Démarrage — ${ROUTES.length} routes — ${startedAt}`);

  let token;
  try {
    token = await getToken();
    console.log('[AUTH] Token obtenu');
  } catch (e) {
    console.error('[AUTH] ÉCHEC:', e.message);
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();

  // Inject auth token
  await page.goto(FRONTEND, { timeout: 10000 });
  await page.evaluate((t) => {
    localStorage.setItem('promeos_token', t);
    // Désactiver la modale onboarding (fix M-01)
    localStorage.removeItem('promeos_onboarding_show');
  }, token);

  const results = [];
  for (const route of ROUTES) {
    const result = await auditRoute(page, route);
    const icon = result.status === 'OK' ? '✅' : '❌';
    console.log(`${icon} ${route.padEnd(40)} | errors=${result.console_errors.length} fails=${result.network_fails.length} crashed=${result.crashed}`);
    results.push(result);
  }

  await browser.close();

  const okCount = results.filter(r => r.status === 'OK').length;
  const koCount = results.filter(r => r.status === 'KO').length;
  const totalConsoleErrors = results.reduce((s, r) => s + r.console_errors.length, 0);
  const totalNetworkFails = results.reduce((s, r) => s + r.network_fails.length, 0);
  const totalCrashes = results.filter(r => r.crashed).length;

  const report = {
    meta: {
      generated_at: new Date().toISOString(),
      started_at: startedAt,
      git_sha: '7309165c',
      branch: 'claude/refonte-visuelle-sol',
      pr: '#264',
      audit_type: 'J+7 post-merge regression check',
      frontend_url: FRONTEND,
      backend_url: BACKEND,
      total_routes: ROUTES.length,
    },
    summary: {
      routes_ok: okCount,
      routes_ko: koCount,
      total_console_errors: totalConsoleErrors,
      total_network_fails: totalNetworkFails,
      total_crashes: totalCrashes,
      verdict: koCount === 0 ? 'CLEAN' : 'REGRESSION',
    },
    routes: results,
  };

  const outFile = resolve(OUT_DIR, 'console-network-report.json');
  writeFileSync(outFile, JSON.stringify(report, null, 2));
  console.log(`\n[RAPPORT] ${outFile}`);
  console.log(`[RÉSUMÉ] ${okCount}/${ROUTES.length} OK · ${totalConsoleErrors} console errors · ${totalNetworkFails} API fails · ${totalCrashes} crashes`);
  console.log(`[VERDICT] ${report.summary.verdict}`);

  return report;
}

run().catch((e) => {
  console.error('[FATAL]', e);
  process.exit(1);
});
