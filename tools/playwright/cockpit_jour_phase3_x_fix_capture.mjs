import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';
const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/cockpit-jour-phase3.x.fix');
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
const fileVisible = await page.locator('[data-testid*="cockpit-jour"]:has-text("Autres priorités")').count();

// Récup CTA label de la 1ère DEC
const firstDecCtaLabel = await page.locator('[data-testid="decision-evidence-card"]').first().locator('a, button').last().innerText().catch(() => null);
const arbHref = await page.locator('[data-testid="cockpit-jour-cta-arbitrage-portefeuille"]').first().getAttribute('href').catch(() => null);

console.log('--- Phase 3.X.fix DOM check ---');
console.log('DEC count:', decCount);
console.log('CTA Arbitrer count:', ctaArb);
console.log('Arbitrer href (sans ?focus=exposure):', arbHref);
console.log('1ère DEC CTA label:', firstDecCtaLabel);
console.log('File "Autres priorités" visible:', fileVisible, '(devrait être 0 si tout agrégé)');

await ctx.close(); await browser.close();
console.log('OK', OUT);
