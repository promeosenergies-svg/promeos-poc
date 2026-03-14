/**
 * Playwright KPI System Freeze — Multi-width validation
 * Tests Performance, Anomalies, Cockpit, Patrimoine, Consommation, APER
 * at 1440, 1280, 1024px widths.
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const DIR = 'playwright-screenshots/kpi-freeze';
mkdirSync(DIR, { recursive: true });
const BASE = 'http://localhost:5173';

(async () => {
  const browser = await chromium.launch({ headless: true });

  async function runAtWidth(width, label) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await ctx.newPage();

    // Login
    await page.goto(`${BASE}/login`);
    await page.waitForTimeout(1000);
    await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
    await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    async function shot(name, url, opts = {}) {
      if (url) await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(opts.wait || 1500);
      if (opts.scroll) {
        await page.evaluate((px) => window.scrollBy(0, px), opts.scroll);
        await page.waitForTimeout(500);
      }
      await page.screenshot({ path: `${DIR}/${label}-${name}.png`, fullPage: opts.fullPage || false });
      console.log(`  ✓ ${label}-${name}`);
    }

    console.log(`\n📐 Width: ${width}px (${label})`);

    // Performance page — executive summary + KPI strip
    await shot('01-performance-top', '/monitoring');
    await shot('02-performance-kpis', '/monitoring', { scroll: 400 });
    await shot('03-performance-full', '/monitoring', { fullPage: true });

    // Anomalies — KPI cards
    await shot('04-anomalies', '/anomalies');

    // Cockpit — executive KPIs
    await shot('05-cockpit', '/cockpit');

    // Consommation — ConsoKpiHeader
    await shot('06-consommation', '/consommations');

    // Patrimoine — KpiCardCompact
    await shot('07-patrimoine', '/patrimoine');

    // APER — KpiCardInline
    await shot('08-aper', '/aper', { fullPage: true });

    // Sidebar — always-open sections
    await shot('09-sidebar', '/patrimoine');

    await ctx.close();
  }

  await runAtWidth(1440, 'w1440');
  await runAtWidth(1280, 'w1280');
  await runAtWidth(1024, 'w1024');

  await browser.close();
  console.log(`\n✅ KPI Freeze screenshots saved to ${DIR}/`);
})();
