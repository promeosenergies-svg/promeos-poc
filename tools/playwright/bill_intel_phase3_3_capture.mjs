import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';
const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/bill-intel-phase3.3');
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
const page = await ctx.newPage();
await page.goto(FE + '/login');
await page.fill('input[type="email"]', 'promeos@promeos.io');
await page.fill('input[type="password"]', 'promeos2024');
await page.click('button[type="submit"]');
await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 30000 });
await page.waitForTimeout(2500);
await page.goto(FE + '/bill-intel', { waitUntil: 'load' });
await page.waitForTimeout(5000);
await page.evaluate(() => {
  document.querySelectorAll('*').forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.animationName !== 'none' || cs.transitionProperty !== 'none') {
      el.style.animation = 'none'; el.style.transition = 'none';
    }
  });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(OUT, '1440x900-after-full.png'), fullPage: true });
await page.screenshot({ path: join(OUT, '1440x900-after-above.png'), fullPage: false });

const oldHero = await page.locator('[data-testid="top-anomaly-hero"]').count();
const newSection = await page.locator('[data-testid="bill-intel-top-decisions"]').count();
const decCount = await page.locator('[data-testid="bill-intel-top-decisions"] [data-testid="decision-evidence-card"]').count();
const decCritical = await page.locator('[data-testid="bill-intel-top-decisions"] [data-testid="decision-evidence-card"][data-severity="critical"]').count();
const decWarning = await page.locator('[data-testid="bill-intel-top-decisions"] [data-testid="decision-evidence-card"][data-severity="warning"]').count();

console.log('--- Phase 3.3 LEDGER bill-intel DOM check ---');
console.log('Ancien topInsight hero (must be 0):', oldHero);
console.log('Nouveau bill-intel-top-decisions section:', newSection);
console.log('DEC count (target 3):', decCount);
console.log('DEC severity=critical:', decCritical);
console.log('DEC severity=warning:', decWarning);

await ctx.close(); await browser.close();
console.log('OK', OUT);
