/**
 * Playwright Sprint P1 — AFTER screenshots
 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const OUT = 'playwright-screenshots/p1-after';

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

  // 1. Cockpit — KPIs with Pourquoi
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/01-cockpit-kpis.png`, fullPage: true });

  // 2. Bill Intel — enhanced explainer
  await page.goto(`${BASE}/bill-intel`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/02-bill-intel.png`, fullPage: true });

  // 3. Bill Intel — toggle Expert and expand methodology
  // Toggle Expert mode
  const expertToggle = page.locator('text=Expert').first();
  if (await expertToggle.isVisible()) {
    await expertToggle.click();
    await page.waitForTimeout(1000);
    // Open methodology details
    const details = page.locator('summary:has-text("Méthodologie")').first();
    if (await details.isVisible()) {
      await details.click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: `${OUT}/03-bill-intel-expert-methodology.png`, fullPage: false });
  }

  // 4. Admin users
  await page.goto(`${BASE}/admin/users`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/04-admin-users.png`, fullPage: false });

  // 5. Performance
  await page.goto(`${BASE}/monitoring`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/05-performance.png`, fullPage: false });

  // 6. Conformité — no dev badges in standard mode
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/06-conformite-no-badges.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
