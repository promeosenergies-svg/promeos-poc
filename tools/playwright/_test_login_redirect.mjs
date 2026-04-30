/** Phase 15.bis — vérifier qu'une fresh login redirige bien sur /cockpit/strategique. */
import { chromium } from 'playwright';
const FRONT = 'http://localhost:5175';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

await page.goto(`${FRONT}/login`, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
await page.fill('input[type=email]', 'promeos@promeos.io');
await page.fill('input[type=password]', 'promeos2024');
await page.press('input[type=password]', 'Enter');
await page.waitForLoadState('networkidle').catch(() => {});
await page.waitForTimeout(2000);

const url = page.url();
console.log(`URL post-login = ${url}`);
const ok = url.endsWith('/cockpit/strategique');
console.log(ok ? '✅ PASS — redirige bien sur Vue exécutive' : '❌ FAIL — atterrit ailleurs');

// Test direct /
await page.goto(`${FRONT}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
const url2 = page.url();
console.log(`URL après goto / = ${url2}`);
const ok2 = url2.endsWith('/cockpit/strategique');
console.log(ok2 ? '✅ PASS — / redirige sur Vue exécutive' : '❌ FAIL — / ne redirige pas');

await browser.close();
process.exit(ok && ok2 ? 0 : 1);
