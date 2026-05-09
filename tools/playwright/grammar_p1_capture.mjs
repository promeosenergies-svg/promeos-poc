import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/conformite-phase1');
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

await page.goto(FE + '/conformite', { waitUntil: 'load' });
await page.waitForTimeout(4000);
await page.evaluate(() => {
  document.querySelectorAll('*').forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.animationName !== 'none' || cs.transitionProperty !== 'none') {
      el.style.animation = 'none'; el.style.transition = 'none';
    }
  });
});
await page.waitForTimeout(300);

await page.screenshot({ path: join(OUT, '1440x900-after.png'), fullPage: true });
await page.screenshot({ path: join(OUT, '1440x900-after-above.png'), fullPage: false });

// Vérifier la présence du DecisionEvidenceCard et des Term
const decisionCard = await page.locator('[data-testid="conformite-decision-evidence-demo"]').count();
const termCount = await page.locator('[data-component="Term"], abbr.sol-term, [data-testid^="term-"]').count();
const acronymTooltips = await page.locator('[role="button"]').count();
console.log(`DecisionEvidenceCard count: ${decisionCard}`);
console.log(`Term elements: ${termCount}`);
console.log(`Tooltip-able elements: ${acronymTooltips}`);

await ctx.close();
await browser.close();
console.log('Capture done →', OUT);
