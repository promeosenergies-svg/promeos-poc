/**
 * Playwright Sprint P2 Audit — Full page captures for sprint audit
 * Captures: site detail (error + working), consumption (desktop + responsive),
 *           monitoring, conformité (top + scroll), APER, cockpit
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://localhost:5173';
const OUT = 'playwright-screenshots/sprint-p2-audit';

async function run() {
  // Ensure output directory exists
  mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // ── Login ──
  console.log('[1/10] Logging in...');
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(1500);
  await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000); // wait for auth + redirect

  // ── 1. /sites/4 — check for "Site #4" error or scope mismatch ──
  console.log('[2/10] /sites/4 — site detail (potential error)...');
  await page.goto(`${BASE}/sites/4`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/01-site-4-detail.png`, fullPage: true });

  // ── 2. /sites/1 — working site detail for comparison ──
  console.log('[3/10] /sites/1 — working site detail...');
  await page.goto(`${BASE}/sites/1`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/02-site-1-detail.png`, fullPage: true });

  // ── 3. /consumption — KPI cards at 1440px ──
  console.log('[4/10] /consumption — desktop 1440px...');
  await page.goto(`${BASE}/consumption`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/03-consumption-1440.png`, fullPage: true });

  // ── 4. /consumption at 1024px — responsive check ──
  console.log('[5/10] /consumption — responsive 1024px...');
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/04-consumption-1024.png`, fullPage: true });
  // Reset viewport
  await page.setViewportSize({ width: 1440, height: 900 });

  // ── 5. /monitoring — Performance page ──
  console.log('[6/10] /monitoring — performance page...');
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/05-monitoring.png`, fullPage: true });

  // ── 6. /conformite — top (score, anomalies, timeline) ──
  console.log('[7/10] /conformite — top view...');
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/06-conformite-top.png`, fullPage: false });

  // ── 7. /conformite scroll bottom — full timeline ──
  console.log('[8/10] /conformite — scroll bottom (full page)...');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/07-conformite-bottom.png`, fullPage: true });

  // ── 8. /aper — APER page ──
  console.log('[9/10] /aper — APER page...');
  await page.goto(`${BASE}/aper`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/08-aper.png`, fullPage: true });

  // ── 9. / — Cockpit with KPIs ──
  console.log('[10/10] / — Cockpit...');
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/09-cockpit.png`, fullPage: true });

  await browser.close();
  console.log(`\nDone — ${9} screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
