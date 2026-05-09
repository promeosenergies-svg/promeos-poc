/**
 * Sprint Grammaire Produit v1 — Phase 0 audit read-only
 *
 * Capture chaque vue PROMEOS sur 3 viewports × 2 modes (full + above-the-fold)
 * pour analyse 4-disciplines (UX / UI / CX / Customer Success) vs grammaire Sol v1.1.
 *
 * Mapping sémantique → route réelle (justifié par App.jsx + NavRegistry.js) :
 *   /centre-action → /?actionCenter=open&tab=actions  (slide-over peek, NavRegistry:1183)
 *   /factures      → /bill-intel                       (canonical, NavRegistry:1223)
 *
 * Output :
 *   docs/audits/grammar_v1/screenshots/{slug}/{viewport}-{mode}.png
 *   docs/audits/grammar_v1/index.html
 *   docs/audits/grammar_v1/capture_report.json
 *
 * Usage :
 *   PROMEOS_FRONTEND_URL=http://localhost:5175 \
 *   PROMEOS_BACKEND_URL=http://localhost:8001 \
 *   node tools/playwright/grammar_audit_v1.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const BACKEND_URL = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const ROOT = resolve(process.cwd(), 'docs/audits/grammar_v1');
const SHOTS_DIR = join(ROOT, 'screenshots');

const VIEWPORTS = [
  { width: 1440, height: 900, key: '1440x900', label: 'Desktop large' },
  { width: 1280, height: 800, key: '1280x800', label: 'Desktop standard' },
  { width: 1024, height: 1366, key: '1024x1366', label: 'iPad portrait' },
];

const VIEWS = [
  {
    slug: 'cockpit-jour',
    path: '/cockpit/jour',
    label: 'Cockpit Décision (jour)',
    intent: 'Décider la journée — rythme HMM',
  },
  {
    slug: 'cockpit-strategique',
    path: '/cockpit/strategique',
    label: 'Cockpit Stratégique',
    intent: 'Lecture exécutive comité direction',
  },
  {
    slug: 'centre-action',
    path: '/?actionCenter=open&tab=actions',
    label: "Centre d'action (peek)",
    intent: 'Inbox transverse alertes + actions',
    note: 'Mapping prompt /centre-action → home + slide-over (NavRegistry.js:1183).',
  },
  {
    slug: 'anomalies',
    path: '/anomalies',
    label: 'Anomalies hub',
    intent: 'Audit + reclaim factures/contrats',
  },
  {
    slug: 'site-paris-bureaux',
    path: '/sites/1',
    label: 'Site360 — Siège HELIOS Paris (id=1)',
    intent: 'Drill-down site unique multi-pillar',
    note: 'Mapping prompt /sites/site_paris_bureaux → /sites/1 — IDs sont integers (1=Siège HELIOS Paris, 3 500 m2). Slug string ne match jamais (422).',
  },
  {
    slug: 'conformite',
    path: '/conformite',
    label: 'Conformité',
    intent: 'Scoring DT/BACS/APER/AUDIT + plan',
  },
  {
    slug: 'factures',
    path: '/bill-intel',
    label: 'Factures (Bill-Intel)',
    intent: 'Shadow billing + anomalies R01-R31',
    note: 'Mapping prompt /factures → /bill-intel (NavRegistry.js:1223).',
  },
  {
    slug: 'onboarding',
    path: '/onboarding',
    label: 'Onboarding',
    intent: 'Premier parcours utilisateur',
  },
];

[ROOT, SHOTS_DIR].forEach((d) => {
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
});
VIEWS.forEach((v) => {
  const d = join(SHOTS_DIR, v.slug);
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
});

function isRealConsoleError(text) {
  if (/Failed to load resource.*favicon/i.test(text)) return false;
  if (/preload.*was not used/i.test(text)) return false;
  if (/source map/i.test(text)) return false;
  if (/DevTools/i.test(text)) return false;
  return true;
}

async function login(page) {
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'load', timeout: 60_000 });
  await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 20_000 });
  await page.fill('input[type="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  // Robust: wait for either URL change OR email input disappearance, with retry
  try {
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 30_000 });
  } catch {
    // Fallback : email input gone = logged in
    await page.waitForSelector('input[type="email"]', { state: 'detached', timeout: 10_000 });
  }
  await page.waitForTimeout(2500);
}

async function captureView(page, view, viewport) {
  const consoleErrors = [];
  const pageErrors = [];
  const networkErrors = [];
  const apiCalls = [];

  const onConsole = (m) => {
    if (m.type() === 'error' && isRealConsoleError(m.text())) {
      consoleErrors.push(m.text().slice(0, 220));
    }
  };
  const onPageErr = (e) => pageErrors.push(e.message.slice(0, 220));
  const onResponse = (r) => {
    const u = r.url();
    if (u.includes('/api/')) apiCalls.push({ url: u, status: r.status() });
    if (r.status() >= 400 && !u.endsWith('/favicon.ico')) {
      networkErrors.push({ url: u, status: r.status() });
    }
  };

  page.on('console', onConsole);
  page.on('pageerror', onPageErr);
  page.on('response', onResponse);

  let navOk = true;
  let navErr = '';
  try {
    await page.goto(FRONTEND_URL + view.path, { waitUntil: 'load', timeout: 30_000 });
    await page.waitForTimeout(3500);
    await page.evaluate(() => {
      document.querySelectorAll('*').forEach((el) => {
        const cs = getComputedStyle(el);
        if (cs.animationName !== 'none' || cs.transitionProperty !== 'none') {
          el.style.animation = 'none';
          el.style.transition = 'none';
        }
      });
    });
    await page.waitForTimeout(300);
  } catch (e) {
    navOk = false;
    navErr = e.message.slice(0, 200);
  }

  const viewportDir = join(SHOTS_DIR, view.slug);
  const fullPath = join(viewportDir, `${viewport.key}-full.png`);
  const aboveFoldPath = join(viewportDir, `${viewport.key}-above.png`);

  try {
    await page.screenshot({ path: fullPath, fullPage: true });
  } catch {}
  try {
    await page.screenshot({ path: aboveFoldPath, fullPage: false });
  } catch {}

  page.off('console', onConsole);
  page.off('pageerror', onPageErr);
  page.off('response', onResponse);

  return {
    slug: view.slug,
    label: view.label,
    path: view.path,
    intent: view.intent,
    note: view.note || null,
    viewport: viewport.key,
    viewportLabel: viewport.label,
    navOk,
    navErr,
    consoleErrors: consoleErrors.length,
    pageErrors: pageErrors.length,
    networkErrors: networkErrors.length,
    apiCalls: apiCalls.length,
    sampleConsole: consoleErrors.slice(0, 3),
    samplePageErrors: pageErrors.slice(0, 3),
    sampleNetworkErrors: networkErrors.slice(0, 3),
    fullPath: fullPath.replace(ROOT + '/', ''),
    aboveFoldPath: aboveFoldPath.replace(ROOT + '/', ''),
  };
}

function buildIndexHtml(reports) {
  const byView = new Map();
  for (const r of reports) {
    if (!byView.has(r.slug)) byView.set(r.slug, { meta: r, captures: [] });
    byView.get(r.slug).captures.push(r);
  }

  const sections = [...byView.values()]
    .map(({ meta, captures }) => {
      const cards = captures
        .map(
          (c) => `
        <div class="card">
          <div class="vp">${c.viewportLabel} <span class="dim">(${c.viewport})</span></div>
          <div class="status ${c.navOk ? 'ok' : 'ko'}">
            ${c.navOk ? 'OK' : 'NAV_FAIL'}
            · console=${c.consoleErrors}
            · pageErr=${c.pageErrors}
            · 4xx=${c.networkErrors}
          </div>
          <div class="grid">
            <div class="shot"><div class="lab">above-the-fold</div><img src="${c.aboveFoldPath}" loading="lazy"/></div>
            <div class="shot"><div class="lab">full page</div><img src="${c.fullPath}" loading="lazy"/></div>
          </div>
        </div>`,
        )
        .join('');

      return `
      <section id="${meta.slug}">
        <h2>${meta.label} <span class="dim">${meta.path}</span></h2>
        <p class="intent">Intention : <em>${meta.intent}</em></p>
        ${meta.note ? `<p class="note">⚠️ ${meta.note}</p>` : ''}
        <div class="cards">${cards}</div>
        <p><a href="findings/${meta.slug}.md">→ findings/${meta.slug}.md</a></p>
      </section>`;
    })
    .join('\n');

  const toc = [...byView.keys()].map((s) => `<li><a href="#${s}">${s}</a></li>`).join('');

  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<title>Audit Grammaire Produit v1 — Phase 0</title>
<style>
  body { font: 14px/1.5 -apple-system, system-ui, sans-serif; max-width: 1600px; margin: 0 auto; padding: 24px; color: #111; background: #fafafa; }
  h1 { margin: 0 0 8px; }
  h2 { margin-top: 48px; padding-bottom: 8px; border-bottom: 1px solid #e5e5e5; }
  .dim { color: #888; font-weight: normal; font-size: 0.85em; }
  .intent { color: #444; }
  .note { color: #b04; background: #fff4f4; padding: 8px 12px; border-left: 3px solid #d22; }
  .cards { display: grid; grid-template-columns: 1fr; gap: 24px; }
  .card { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 16px; }
  .vp { font-weight: 600; }
  .status { font-family: ui-monospace, monospace; font-size: 12px; padding: 4px 8px; display: inline-block; border-radius: 4px; margin: 8px 0; }
  .status.ok { background: #e7f7e7; color: #1a5e1a; }
  .status.ko { background: #fde7e7; color: #8a1a1a; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
  .shot { border: 1px solid #eee; border-radius: 4px; overflow: hidden; }
  .lab { background: #f3f3f3; padding: 4px 8px; font-size: 12px; color: #555; }
  .shot img { display: block; width: 100%; height: auto; }
  .toc { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 16px; }
  .toc ul { list-style: none; padding: 0; margin: 0; columns: 3; }
  .toc li { margin: 4px 0; }
  a { color: #0a5; }
</style>
</head>
<body>
  <h1>Audit Grammaire Produit v1 — Phase 0 (read-only)</h1>
  <p>Capturé le ${new Date().toISOString()} · branche <code>claude/refonte-sol2</code> · FE <code>${FRONTEND_URL}</code></p>
  <div class="toc"><strong>Vues auditées</strong><ul>${toc}</ul></div>
  ${sections}
</body>
</html>`;
}

(async () => {
  console.log(`[grammar-audit-v1] FE=${FRONTEND_URL} BE=${BACKEND_URL}`);
  console.log(`[grammar-audit-v1] OUT=${ROOT}`);
  console.log(`[grammar-audit-v1] ${VIEWS.length} vues × ${VIEWPORTS.length} viewports = ${VIEWS.length * VIEWPORTS.length} captures × 2 modes\n`);

  const browser = await chromium.launch({ headless: true });
  const reports = [];

  // Outer = viewport (1 context + login per viewport, 3 logins total)
  for (const viewport of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
    });
    const page = await ctx.newPage();

    try {
      await login(page);
      console.log(`[login OK ] ${viewport.key} (${viewport.label})`);
    } catch (e) {
      console.log(`[login KO ] ${viewport.key} : ${e.message.slice(0, 100)}`);
      await ctx.close();
      continue;
    }

    for (const view of VIEWS) {
      const r = await captureView(page, view, viewport);
      reports.push(r);
      const tag =
        !r.navOk ? 'NAV_FAIL'
        : r.pageErrors > 0 ? 'KO_RUNTIME'
        : r.networkErrors > 0 ? 'WARN_4xx'
        : r.consoleErrors > 0 ? 'WARN_CONS'
        : 'OK';
      console.log(
        `  [${tag.padEnd(10)}] ${viewport.key.padEnd(11)} ${view.slug.padEnd(22)} api=${r.apiCalls} cons=${r.consoleErrors} 4xx=${r.networkErrors}`,
      );
    }

    await ctx.close();
  }

  await browser.close();

  const indexPath = join(ROOT, 'index.html');
  writeFileSync(indexPath, buildIndexHtml(reports));

  const reportPath = join(ROOT, 'capture_report.json');
  writeFileSync(
    reportPath,
    JSON.stringify(
      { generated_at: new Date().toISOString(), frontend_url: FRONTEND_URL, viewports: VIEWPORTS, views: VIEWS, reports },
      null,
      2,
    ),
  );

  console.log(`\n══════════ CAPTURE OK ══════════`);
  console.log(`Index HTML  : ${indexPath}`);
  console.log(`Report JSON : ${reportPath}`);
  console.log(`Screenshots : ${SHOTS_DIR}/`);

  const navFail = reports.filter((r) => !r.navOk).length;
  const totalPageErr = reports.reduce((s, r) => s + r.pageErrors, 0);
  process.exitCode = navFail > 0 || totalPageErr > 0 ? 1 : 0;
})();
