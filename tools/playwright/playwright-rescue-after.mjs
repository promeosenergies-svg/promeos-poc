/**
 * Playwright UI Rescue Sprint — AFTER screenshots
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const DIR = 'artifacts/playwright/rescue-after';
mkdirSync(DIR, { recursive: true });
const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';

(async () => {
  const browser = await chromium.launch({ headless: true });

  async function runAtWidth(width, label) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await ctx.newPage();

    await page.goto(`${BASE}/login`);
    await page.waitForTimeout(1000);
    await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
    await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    async function shot(name, url, opts = {}) {
      if (url) await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(opts.wait || 1500);
      if (opts.click) {
        try { await page.click(opts.click, { timeout: 3000 }); await page.waitForTimeout(1000); } catch {}
      }
      if (opts.scroll) {
        await page.evaluate((px) => window.scrollBy(0, px), opts.scroll);
        await page.waitForTimeout(500);
      }
      await page.screenshot({ path: `${DIR}/${label}-${name}.png`, fullPage: opts.fullPage || false });
      console.log(`  ✓ ${label}-${name}`);
    }

    console.log(`\n📐 Width: ${width}px (${label})`);
    await shot('01-patrimoine', '/patrimoine', { fullPage: true });
    await shot('02-site-detail-4', '/sites/4');
    await shot('03-site-detail-1', '/sites/1');
    await shot('04-consommation', '/consommations');
    await shot('05-performance-top', '/monitoring');
    await shot('06-performance-scroll', '/monitoring', { scroll: 600 });
    await shot('07-performance-full', '/monitoring', { fullPage: true });
    await shot('08-anomalies', '/anomalies');
    await shot('09-cockpit', '/cockpit');

    await ctx.close();
  }

  await runAtWidth(1440, 'w1440');
  await runAtWidth(1280, 'w1280');
  await runAtWidth(1024, 'w1024');

  await browser.close();
  console.log(`\n✅ AFTER screenshots saved to ${DIR}/`);
})();
