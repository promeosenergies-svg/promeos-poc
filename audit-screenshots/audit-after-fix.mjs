/**
 * Audit AFTER fix — Captures the 4 key screens after P1/P2/BONUS fixes
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND = 'http://localhost:5173';
const BACKEND  = 'http://localhost:8001';
const OUT_DIR  = resolve(import.meta.dirname || '.', 'captures', 'after-fix');
mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 3000 } });
  const page = await ctx.newPage();

  const res = await (await fetch(`${BACKEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
  })).json();
  await page.goto(FRONTEND);
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), res.token || res.access_token);

  const snap = async (name) => {
    await page.waitForTimeout(2000);
    await page.screenshot({ path: join(OUT_DIR, `${name}.png`), fullPage: true });
    console.log(`[SNAP] ${name}`);
  };

  // ── 1. OBLIGATION BACS (P1: date contextualisée) ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // Obligations tab
  await page.locator('button').filter({ hasText: 'Obligations' }).last().click();
  await page.waitForTimeout(2000);
  await snap('AFTER-01-obligations-bacs-date');

  // Expert mode
  await page.locator('text=Expert').first().click();
  await page.waitForTimeout(2000);
  await snap('AFTER-02-obligations-expert-bacs');

  // Force-expand all obligation cards
  await page.evaluate(() => {
    document.querySelectorAll('svg').forEach(svg => {
      const classes = svg.getAttribute('class') || '';
      if (classes.includes('chevron-down') || svg.innerHTML?.includes('polyline')) {
        const parent = svg.closest('button') || svg.closest('div[class*="cursor"]') || svg.parentElement;
        if (parent) parent.click();
      }
    });
  });
  await page.waitForTimeout(2000);
  await snap('AFTER-03-obligations-expanded-expert');

  // ── 2. PAGE PREUVES (P2: seed preuves) ──
  await page.locator('button').filter({ hasText: /Preuves/ }).last().click();
  await page.waitForTimeout(2000);
  await snap('AFTER-04-preuves-tab');

  // ── 3. PLAN D'EXÉCUTION (B4 lifecycle) ──
  await page.locator('button').filter({ hasText: /Plan d/ }).last().click();
  await page.waitForTimeout(2000);
  await snap('AFTER-05-execution-tab');

  // ── 4. PAGE /ACTIONS (P2: seed actions conformité) ──
  await page.goto(`${FRONTEND}/actions`);
  await page.waitForTimeout(3000);
  await snap('AFTER-06-actions-page');

  // ── 5. TOP 3 URGENCES with formatted date ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);
  // Scroll to see top 3 urgences
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('AFTER-07-top3-urgences');

  // ── 6. EXPERT TOOLTIP (hover on toggle) ──
  const expertDiv = page.locator('div[title*="mode Expert"]').first();
  if (await expertDiv.isVisible()) {
    await expertDiv.hover();
    await page.waitForTimeout(1000);
    await snap('AFTER-08-expert-tooltip');
  }

  await browser.close();
  console.log(`\n=== Done. ${OUT_DIR} ===`);
}

run().catch((e) => { console.error(e); process.exit(1); });
