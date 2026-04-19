/**
 * PROMEOS — Playwright helper refonte Sol V1
 *
 * Helper réutilisable pour les Lots 1-6 : capture une paire A/B de
 * screenshots (main 5173 legacy + refonte 5175 Sol) avec login réel,
 * dismiss onboarding overlay, et sauvegarde dans
 * docs/design/screenshots/ selon la nomenclature SOL_MIGRATION_GUIDE.md.
 *
 * Usage :
 *   import { captureABPair } from './sol_refonte_helper.mjs';
 *   await captureABPair('cockpit', '/cockpit');
 *   await captureABPair('conformite', '/conformite');
 *
 * CLI :
 *   node tools/playwright/sol_refonte_helper.mjs cockpit /cockpit
 *   node tools/playwright/sol_refonte_helper.mjs "cockpit,conformite,patrimoine,achat" "/cockpit,/conformite,/patrimoine,/achat-energie"
 */
import { chromium } from 'playwright';
import { resolve } from 'path';

const DEFAULT_MAIN_URL = 'http://127.0.0.1:5173';
const DEFAULT_REFONTE_URL = 'http://127.0.0.1:5175';
const DEFAULT_OUT_DIR = resolve(
  'c:/Users/amine/promeos-poc/promeos-refonte/docs/design/screenshots'
);
const EMAIL = 'promeos@promeos.io';
const PASSWORD = 'promeos2024';
const VIEWPORT = { width: 1440, height: 900 };
const SETTLE_MS = 3500;

async function loginAndGoto(page, baseUrl, routePath) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' });
  // Si déjà loggé, la redirection saute le form (input absent ou URL changée)
  const stillOnLogin = await page.url().includes('/login');
  const hasEmailInput = stillOnLogin && (await page.locator('input[type="email"]').count()) > 0;
  if (hasEmailInput) {
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((u) => !u.pathname.endsWith('/login'), { timeout: 15000 }).catch(() => {});
  }
  await page.goto(`${baseUrl}${routePath}`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(SETTLE_MS);

  // Dismisser OnboardingOverlay si présent (touche Escape + boutons connus)
  for (const sel of [
    'button:has-text("Passer le tour")',
    'button:has-text("Fermer")',
    'button[aria-label="Fermer"]',
    'button:has-text("×")',
    'button:has-text("Plus tard")',
  ]) {
    try { await page.locator(sel).first().click({ timeout: 800 }); break; } catch (_) {}
  }
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(500);
}

async function snapPair(browser, baseUrl, routePath, outPrefix) {
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();
  try {
    await loginAndGoto(page, baseUrl, routePath);
    await page.screenshot({ path: `${outPrefix}.png`, fullPage: true });
    await page.screenshot({ path: `${outPrefix}_fold.png`, fullPage: false });
    console.log(`OK ${outPrefix}.png + _fold`);
  } catch (e) {
    console.error(`FAIL ${outPrefix}: ${e.message}`);
  } finally {
    await ctx.close();
  }
}

/**
 * Capture une paire A/B pour une page donnée.
 * @param {string} pageName — kebab-case, sert de prefix fichier (ex 'cockpit', 'conformite')
 * @param {string} routePath — route après le host (ex '/cockpit')
 * @param {object} [opts] — { mainUrl, refonteUrl, outDir, skipMain, skipRefonte }
 */
export async function captureABPair(pageName, routePath, opts = {}) {
  const mainUrl = opts.mainUrl ?? DEFAULT_MAIN_URL;
  const refonteUrl = opts.refonteUrl ?? DEFAULT_REFONTE_URL;
  const outDir = opts.outDir ?? DEFAULT_OUT_DIR;

  const browser = await chromium.launch({ headless: true });
  try {
    if (!opts.skipMain) {
      await snapPair(browser, mainUrl, routePath, `${outDir}/${pageName}_main_before`);
    }
    if (!opts.skipRefonte) {
      await snapPair(browser, refonteUrl, routePath, `${outDir}/${pageName}_refonte_after`);
    }
  } finally {
    await browser.close();
  }
}

// CLI entry point — detection robuste Windows + POSIX
const isCli = (() => {
  try {
    const arg = (process.argv[1] || '').replace(/\\/g, '/').toLowerCase();
    const here = import.meta.url.toLowerCase();
    return arg && (here.endsWith(arg) || here.endsWith(`/${arg.split('/').pop()}`));
  } catch (_) { return false; }
})();
if (isCli) {
  const [pages, routes] = process.argv.slice(2);
  if (!pages || !routes) {
    console.error('Usage: node sol_refonte_helper.mjs <pages> <routes>');
    console.error('Ex   : node sol_refonte_helper.mjs "cockpit,conformite" "/cockpit,/conformite"');
    process.exit(1);
  }
  const pageList = pages.split(',').map((s) => s.trim());
  const routeList = routes.split(',').map((s) => s.trim());
  if (pageList.length !== routeList.length) {
    console.error('Error: pages and routes must have the same length.');
    process.exit(1);
  }
  (async () => {
    for (let i = 0; i < pageList.length; i++) {
      await captureABPair(pageList[i], routeList[i]);
    }
  })().catch((e) => { console.error(e); process.exit(1); });
}
