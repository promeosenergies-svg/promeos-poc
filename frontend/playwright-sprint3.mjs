/**
 * Playwright Sprint 3 — Sidebar Context-first + Timeline Fix
 * Screenshots: sidebar (multiple modules), regulatory timeline, density
 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const OUT = 'playwright-screenshots/sprint3';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Login
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  // 1. Sidebar — Pilotage module (default)
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/01-sidebar-pilotage.png`, fullPage: false });

  // 2. Sidebar — Patrimoine module
  await page.goto(`${BASE}/patrimoine`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/02-sidebar-patrimoine.png`, fullPage: false });

  // 3. Sidebar — Énergie module
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/03-sidebar-energie.png`, fullPage: false });

  // 4. Sidebar — Achat module
  await page.goto(`${BASE}/bill-intel`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/04-sidebar-achat.png`, fullPage: false });

  // 5. Regulatory timeline (conformité page)
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/05-conformite-timeline.png`, fullPage: true });

  // 6. Performance page — check density
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/06-performance-page.png`, fullPage: false });

  // 7. Anomalies page
  await page.goto(`${BASE}/anomalies`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/07-anomalies.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
