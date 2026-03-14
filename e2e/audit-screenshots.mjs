/**
 * Playwright audit script — capture before/after screenshots of problematic pages.
 * Usage: node e2e/audit-screenshots.mjs [before|after]
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { join } from 'path';

const BASE = 'http://localhost:5173';
const SHOT_DIR = join(process.cwd(), 'e2e', 'screenshots');
const SUFFIX = process.argv[2] || 'before';

mkdirSync(SHOT_DIR, { recursive: true });

const PAGES = [
  { name: 'aper', path: '/conformite/aper' },
  { name: 'performance', path: '/performance' },
  { name: 'consommation', path: '/consommations' },
  { name: 'anomalies', path: '/anomalies' },
  { name: 'cockpit', path: '/cockpit' },
  { name: 'patrimoine', path: '/patrimoine' },
  { name: 'conformite', path: '/conformite' },
  { name: 'actions', path: '/actions' },
  { name: 'bill-intel', path: '/bill-intel' },
];

async function login(page) {
  console.log('Logging in...');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(500);

  // Fill demo credentials
  const emailInput = page.locator('input[type="email"], input[placeholder*="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();

  if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    await emailInput.fill('promeos@promeos.io');
    await passwordInput.fill('promeos2024');
    await page.locator('button[type="submit"]').click();
    await page.waitForTimeout(3000);
    console.log('Login submitted, waiting for redirect...');
    // Wait for navigation away from login
    await page.waitForURL(/\/(cockpit|patrimoine|conformite)/, { timeout: 10000 }).catch(() => {});
    console.log('Logged in. Current URL:', page.url());
  } else {
    console.log('No login form found, may already be authenticated');
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'fr-FR',
  });
  const page = await ctx.newPage();

  // Login first
  await login(page);
  await page.waitForTimeout(1000);

  for (const { name, path } of PAGES) {
    console.log(`[${SUFFIX}] Capturing ${name} → ${path}`);
    try {
      await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);
      await page.screenshot({
        path: join(SHOT_DIR, `${name}_${SUFFIX}.png`),
        fullPage: true,
      });
      console.log(`  OK: ${name}_${SUFFIX}.png`);
    } catch (err) {
      console.log(`  ERROR on ${name}: ${err.message}`);
      try {
        await page.screenshot({
          path: join(SHOT_DIR, `${name}_${SUFFIX}_error.png`),
          fullPage: true,
        });
      } catch {}
    }
  }

  await browser.close();
  console.log(`\nDone. Screenshots saved to ${SHOT_DIR}`);
}

run();
