/**
 * Playwright Sprint P1 — BEFORE screenshots
 */
import { chromium } from 'playwright';

const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const OUT = 'artifacts/playwright/p1-before';

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

  // 1. Cockpit — KPIs
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/01-cockpit.png`, fullPage: true });

  // 2. Bill Intel / Shadow billing
  await page.goto(`${BASE}/bill-intel`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/02-bill-intel.png`, fullPage: true });

  // 3. Performance
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/03-performance.png`, fullPage: false });

  // 4. Achat / Purchase
  await page.goto(`${BASE}/achat`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/04-achat.png`, fullPage: false });

  // 5. Admin
  await page.goto(`${BASE}/admin/users`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/05-admin.png`, fullPage: false });

  // 6. Consommation
  await page.goto(`${BASE}/consommation`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/06-consommation.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
