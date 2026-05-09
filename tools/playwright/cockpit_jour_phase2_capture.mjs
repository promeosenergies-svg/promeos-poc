import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/cockpit-jour-phase2');
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

await page.goto(FE + '/cockpit/jour', { waitUntil: 'load' });
await page.waitForTimeout(4500);
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

const briefingNarrative = await page.locator('[data-testid="cockpit-jour-briefing-narrative"]').count();
const topDecisions = await page.locator('[data-testid="cockpit-jour-top-decisions"]').count();
const decisionCards = await page.locator('[data-testid="decision-evidence-card"]').count();
const solFooter = await page.locator('[data-testid="sol-page-footer"]').count();
const termAcronyms = await page.locator('[data-component="Term"], [data-testid^="term-"], abbr.sol-term').count();

console.log('briefing narrative count:', briefingNarrative);
console.log('top-decisions section:', topDecisions);
console.log('DecisionEvidenceCard count:', decisionCards);
console.log('SolPageFooter count:', solFooter);
console.log('Term elements (any selector):', termAcronyms);

await ctx.close(); await browser.close();
console.log('OK');
