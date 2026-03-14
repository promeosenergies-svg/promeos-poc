/**
 * Playwright Sprint P2 — AFTER screenshots (validation)
 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const OUT = 'playwright-screenshots/sprint-p2-after';

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
  await page.waitForTimeout(3000);

  // 1. Site #1 — verify no "undefined" anomalies
  await page.goto(`${BASE}/sites/1`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-site-1-detail.png`, fullPage: false });

  // 2. Site #4 — verify proper error handling (not skeleton forever)
  await page.goto(`${BASE}/sites/4`);
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${OUT}/02-site-4-handling.png`, fullPage: false });

  // 3. Consumption explorer — correct route
  await page.goto(`${BASE}/consommations/explorer`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/03-consumption-1440.png`, fullPage: false });

  // 4. Consumption at 1024px
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUT}/04-consumption-1024.png`, fullPage: false });
  await page.setViewportSize({ width: 1440, height: 900 });

  // 5. Monitoring page — cleaner with details collapsed
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/05-monitoring-standard.png`, fullPage: true });

  // 6. Conformité — score with adaptive labels
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/06-conformite-top.png`, fullPage: false });

  // 7. Conformité scrolled — timeline + obligations
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUT}/07-conformite-bottom.png`, fullPage: true });

  // 8. Cockpit
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/08-cockpit.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
