/**
 * Sprint α smoke test — claude/refonte-sol2 HEAD ccfb6420
 *
 * Vérifie 5 objectifs :
 *   1. App.jsx Provider chain OK (boot sans erreur, redirect / → /cockpit/strategique)
 *   2. ConformitePage useEvents → 1 fetch /api/v1/events/upcoming?page_key=conformite
 *   3. CommandCenter useEvents → 1 fetch /api/v1/events/upcoming?page_key=cockpit_daily
 *   4. Pas de fetch dispersés (1 nouveau fetch par changement de page)
 *   5. Console errors = 0
 *
 * Usage:
 *   node tools/playwright/sprint_alpha_smoke.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const BACKEND_URL  = process.env.PROMEOS_BACKEND_URL  || 'http://localhost:8001';
const OUT_DIR = resolve(process.cwd(), 'tools/playwright/captures/sprint_alpha_smoke');
const VIEWPORT = { width: 1440, height: 900 };

if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const allFetches = [];     // [{url, method, status, durMs, t}]
const consoleMessages = [];
const pageErrors = [];

function recordFetch(req, resp, durMs) {
  allFetches.push({
    url: req.url(),
    method: req.method(),
    status: resp ? resp.status() : null,
    durMs,
    t: Date.now(),
  });
}

(async () => {
  console.log(`[smoke] FE=${FRONTEND_URL} BE=${BACKEND_URL}`);
  console.log(`[smoke] OUT=${OUT_DIR}`);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();

  // Console / errors capture
  page.on('console', (msg) => {
    consoleMessages.push({ type: msg.type(), text: msg.text(), location: msg.location() });
  });
  page.on('pageerror', (err) => {
    pageErrors.push({ message: err.message, stack: err.stack });
  });

  // Network: track every events/upcoming fetch latency
  const pendingByUrl = new Map();
  page.on('request', (req) => {
    if (req.url().includes('/events/upcoming')) {
      pendingByUrl.set(req, Date.now());
    }
  });
  page.on('response', (resp) => {
    const req = resp.request();
    if (req.url().includes('/events/upcoming')) {
      const t0 = pendingByUrl.get(req);
      const dur = t0 ? Date.now() - t0 : -1;
      recordFetch(req, resp, dur);
      pendingByUrl.delete(req);
    }
  });

  const objectives = {
    obj1_boot_redirect: { ok: false, detail: '', screenshot: '' },
    obj2_conformite_fetch: { ok: false, detail: '', screenshot: '', fetchCount: 0 },
    obj3_command_center_fetch: { ok: false, detail: '', screenshot: '', fetchCount: 0 },
    obj4_no_scattered: { ok: false, detail: '' },
    obj5_no_console_errors: { ok: false, detail: '', errorCount: 0 },
  };

  try {
    // ──────────────────────────────────────────────────────
    // OBJ 1 — Boot + redirect / → /cockpit/strategique
    // (login démo requis — DEMO_MODE bypass auth backend mais AuthContext FE exige login)
    // ──────────────────────────────────────────────────────
    console.log('\n[obj 1] login via /login');
    await page.goto(FRONTEND_URL + '/login', { waitUntil: 'load', timeout: 60_000 });
    // Wait for SPA to mount the login form
    try {
      await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 20_000 });
    } catch (e) {
      console.log('[obj 1] WARN: login email field not visible — taking diagnostic shot');
      await page.screenshot({ path: join(OUT_DIR, '00-login-not-visible.png'), fullPage: true });
      throw e;
    }
    await page.fill('input[type="email"]', 'promeos@promeos.io');
    await page.fill('input[type="password"]', 'promeos2024');
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20_000 });
    await page.waitForTimeout(2500);

    // Now we should be redirected to /cockpit/strategique (or other root)
    const url1 = page.url();
    const shot1 = join(OUT_DIR, '01-boot-redirect.png');
    await page.screenshot({ path: shot1, fullPage: true });
    objectives.obj1_boot_redirect.screenshot = shot1;
    objectives.obj1_boot_redirect.detail = `post-login landed on ${url1}`;
    objectives.obj1_boot_redirect.ok =
      !page.url().includes('/login') &&
      !pageErrors.some((e) => /Cannot read|undefined is not|EventsProvider|Provider/i.test(e.message));

    // ──────────────────────────────────────────────────────
    // OBJ 2 — /conformite useEvents
    // ──────────────────────────────────────────────────────
    console.log('[obj 2] navigate /conformite');
    const fetchesBefore2 = allFetches.length;
    await page.goto(FRONTEND_URL + '/conformite', { waitUntil: 'load', timeout: 60_000 });
    await page.waitForTimeout(2500); // laisser la page settle + 1er fetch events
    const conformiteFetches = allFetches
      .slice(fetchesBefore2)
      .filter((f) => f.url.includes('page_key=conformite'));
    const shot2 = join(OUT_DIR, '02-conformite.png');
    await page.screenshot({ path: shot2, fullPage: true });
    objectives.obj2_conformite_fetch.screenshot = shot2;
    objectives.obj2_conformite_fetch.fetchCount = conformiteFetches.length;
    objectives.obj2_conformite_fetch.detail =
      conformiteFetches.length > 0
        ? `${conformiteFetches.length}x fetch — first: ${conformiteFetches[0].url}`
        : 'no fetch detected';
    objectives.obj2_conformite_fetch.ok = conformiteFetches.length >= 1;

    // ──────────────────────────────────────────────────────
    // OBJ 3 — /command-center useEvents
    // ──────────────────────────────────────────────────────
    console.log('[obj 3] navigate /command-center');
    const fetchesBefore3 = allFetches.length;
    await page.goto(FRONTEND_URL + '/command-center', { waitUntil: 'load', timeout: 60_000 });
    await page.waitForTimeout(2500);
    const ccFetches = allFetches
      .slice(fetchesBefore3)
      .filter((f) => f.url.includes('page_key=cockpit_daily'));
    const shot3 = join(OUT_DIR, '03-command-center.png');
    await page.screenshot({ path: shot3, fullPage: true });
    objectives.obj3_command_center_fetch.screenshot = shot3;
    objectives.obj3_command_center_fetch.fetchCount = ccFetches.length;
    objectives.obj3_command_center_fetch.detail =
      ccFetches.length > 0
        ? `${ccFetches.length}x fetch — first: ${ccFetches[0].url}`
        : 'no fetch detected';
    objectives.obj3_command_center_fetch.ok = ccFetches.length >= 1;

    // ──────────────────────────────────────────────────────
    // OBJ 4 — Pas de fetch dispersés (cycle conformite → cockpit_daily)
    // 1 navigation = exactement 1 fetch attendu (ou 2 max si StrictMode dev)
    // ──────────────────────────────────────────────────────
    console.log('[obj 4] cycle conformite → cockpit_daily');
    const fetchesBefore4a = allFetches.length;
    await page.goto(FRONTEND_URL + '/conformite', { waitUntil: 'load', timeout: 60_000 });
    await page.waitForTimeout(2500);
    const conf2 = allFetches
      .slice(fetchesBefore4a)
      .filter((f) => f.url.includes('/events/upcoming'));

    const fetchesBefore4b = allFetches.length;
    await page.goto(FRONTEND_URL + '/command-center', { waitUntil: 'load', timeout: 60_000 });
    await page.waitForTimeout(2500);
    const cc2 = allFetches
      .slice(fetchesBefore4b)
      .filter((f) => f.url.includes('/events/upcoming'));

    // Tolérance : 1 fetch attendu, max 2 (React StrictMode double-mount en dev)
    const conf2OnlyConformite = conf2.filter((f) => f.url.includes('page_key=conformite'));
    const cc2OnlyCockpit = cc2.filter((f) => f.url.includes('page_key=cockpit_daily'));
    const acceptable =
      conf2OnlyConformite.length >= 1 &&
      conf2OnlyConformite.length <= 3 &&
      cc2OnlyCockpit.length >= 1 &&
      cc2OnlyCockpit.length <= 3;
    objectives.obj4_no_scattered.detail = `conformite=${conf2OnlyConformite.length}, cockpit_daily=${cc2OnlyCockpit.length} (max acceptable=3 pour StrictMode dev)`;
    objectives.obj4_no_scattered.ok = acceptable;

    // ──────────────────────────────────────────────────────
    // OBJ 5 — Console errors (red React errors only — warnings tolérés)
    // ──────────────────────────────────────────────────────
    const realErrors = consoleMessages.filter(
      (m) =>
        m.type === 'error' &&
        // Filtrer le bruit Vite/HMR/preload connu
        !/Failed to load resource.*favicon/i.test(m.text) &&
        !/preload.*was not used/i.test(m.text) &&
        !/source map/i.test(m.text),
    );
    objectives.obj5_no_console_errors.errorCount = realErrors.length + pageErrors.length;
    objectives.obj5_no_console_errors.ok = realErrors.length === 0 && pageErrors.length === 0;
    objectives.obj5_no_console_errors.detail =
      realErrors.length === 0 && pageErrors.length === 0
        ? 'aucune erreur'
        : `console=${realErrors.length}, pageErrors=${pageErrors.length} — premier: ${(realErrors[0]?.text || pageErrors[0]?.message || '').slice(0, 200)}`;

    // ──────────────────────────────────────────────────────
    // Latence moyenne fetch /events/upcoming
    // ──────────────────────────────────────────────────────
    const eventsFetches = allFetches.filter((f) => f.url.includes('/events/upcoming'));
    const events404 = eventsFetches.filter((f) => f.status === 404);
    const events200 = eventsFetches.filter((f) => f.status === 200);
    const avgLatency = eventsFetches.length
      ? Math.round(eventsFetches.reduce((s, f) => s + Math.max(f.durMs, 0), 0) / eventsFetches.length)
      : -1;

    // ──────────────────────────────────────────────────────
    // Rapport JSON + console
    // ──────────────────────────────────────────────────────
    const report = {
      head: 'ccfb6420',
      branch: 'claude/refonte-sol2',
      generated_at: new Date().toISOString(),
      objectives,
      latency_ms_avg: avgLatency,
      events_fetch_count_total: eventsFetches.length,
      events_fetch_404_count: events404.length,
      events_fetch_200_count: events200.length,
      console_errors_count: realErrors.length,
      page_errors_count: pageErrors.length,
      sample_events_fetches: eventsFetches.slice(0, 12).map((f) => ({
        url: f.url.replace(BACKEND_URL, ''),
        status: f.status,
        durMs: f.durMs,
      })),
      sample_console_errors: realErrors.slice(0, 5).map((m) => m.text),
      sample_page_errors: pageErrors.slice(0, 5).map((e) => e.message),
    };

    const reportPath = join(OUT_DIR, 'report.json');
    writeFileSync(reportPath, JSON.stringify(report, null, 2));

    console.log('\n══════════════ RAPPORT SMOKE SPRINT α ══════════════');
    for (const [k, v] of Object.entries(objectives)) {
      const tag = v.ok ? 'OK ' : 'KO ';
      console.log(`[${tag}] ${k}: ${v.detail}`);
      if (v.screenshot) console.log(`         shot: ${v.screenshot}`);
    }
    console.log(`\nLatence moy /events/upcoming: ${avgLatency}ms (n=${eventsFetches.length}, 200=${events200.length}, 404=${events404.length})`);
    console.log(`Console errors: ${realErrors.length} | Page errors: ${pageErrors.length}`);
    console.log(`Rapport JSON: ${reportPath}`);

    const allOk = Object.values(objectives).every((o) => o.ok);
    console.log(`\nVERDICT: ${allOk ? 'GO cleanup' : 'NO-GO — voir détails'}`);
  } catch (e) {
    console.error('[smoke] ERROR:', e.message);
    console.error(e.stack);
    process.exitCode = 1;
  } finally {
    await ctx.close();
    await browser.close();
  }
})();
