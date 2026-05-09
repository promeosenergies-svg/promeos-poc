import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';
const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/cockpit-jour-phase3.2');
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

const decCount = await page.locator('[data-testid="decision-evidence-card"]').count();
const ctaArb = await page.locator('[data-testid="cockpit-jour-cta-arbitrage-portefeuille"]').count();
const sevCritical = await page.locator('[data-testid="decision-evidence-card"][data-severity="critical"]').count();
const sevWarning = await page.locator('[data-testid="decision-evidence-card"][data-severity="warning"]').count();

// Extract narrative + DEC titles to verify aggregation
const narrative = await page.locator('[data-testid="cockpit-jour-briefing-narrative"]').innerText();
const decTitles = await page.locator('[data-testid="decision-evidence-card"] h2').allInnerTexts();
console.log('--- Phase 3.2 DOM check ---');
console.log('DEC count (target ≤3 even with 5 backend):', decCount);
console.log('CTA Arbitrer le portefeuille:', ctaArb);
console.log('Severity critical (must be 0):', sevCritical);
console.log('Severity warning:', sevWarning);
console.log('Narrative:', narrative);
console.log('DEC titles (deduped if agg):');
decTitles.forEach((t, i) => console.log(`  ${i+1}.`, t));

await ctx.close(); await browser.close();
console.log('OK', OUT);
