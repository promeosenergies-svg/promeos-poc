import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/centre-action-phase2bis');
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

// Open peek slide-over
await page.goto(FE + '/?actionCenter=open&tab=actions', { waitUntil: 'load' });
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

// Crop on the slide-over for clarity
const drawer = page.locator('[role="dialog"]').first();
const drawerVisible = await drawer.count();
if (drawerVisible > 0) {
  try {
    await drawer.screenshot({ path: join(OUT, 'slideover-only.png') });
  } catch {}
}

const ledgerHero = await page.locator('[data-testid="ledger-mini-hero"]').count();
const ledgerTopDecisions = await page.locator('[data-testid="ledger-top-decisions"]').count();
const decisionCards = await page.locator('[data-testid="decision-evidence-card"]').count();
const ledgerFooter = await page.locator('[data-testid="ledger-footer"]').count();
const solPageFooter = await page.locator('[data-testid="sol-page-footer"]').count();
const termAcronyms = await page.locator('[data-component="Term"], [data-testid^="term-"], abbr.sol-term').count();

console.log('ledger mini-hero:', ledgerHero);
console.log('ledger top-decisions section:', ledgerTopDecisions);
console.log('DecisionEvidenceCard count:', decisionCards);
console.log('ledger footer:', ledgerFooter);
console.log('SolPageFooter count:', solPageFooter);
console.log('Term elements:', termAcronyms);

await ctx.close(); await browser.close();
console.log('Capture done →', OUT);
