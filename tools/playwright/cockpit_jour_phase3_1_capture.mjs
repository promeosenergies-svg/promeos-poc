import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const FE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const OUT = resolve(process.cwd(), 'docs/audits/grammar_v1/screenshots/cockpit-jour-phase3.1');
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

// Mesure du ratio rouge above-fold
const redRatio = await page.evaluate(() => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const docElement = document.documentElement;
  const w = docElement.clientWidth;
  const h = Math.min(900, docElement.scrollHeight);
  // Heuristique : compter les éléments avec background rouge sang
  const all = document.querySelectorAll('*');
  let redElements = 0;
  let totalArea = 0;
  let redArea = 0;
  for (const el of all) {
    const rect = el.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > h) continue;
    const cs = getComputedStyle(el);
    const bg = cs.backgroundColor;
    const area = Math.max(0, Math.min(rect.right, w) - Math.max(rect.left, 0)) *
                 Math.max(0, Math.min(rect.bottom, h) - Math.max(rect.top, 0));
    if (area === 0) continue;
    totalArea += area;
    // Rouge sang RGB(180+,30-,30-) approx
    const m = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)/);
    if (m) {
      const r = +m[1], g = +m[2], b = +m[3];
      if (r > 180 && g < 80 && b < 80) {
        redElements++;
        redArea += area;
      }
    }
  }
  return { redElements, redAreaPct: totalArea ? Math.round((redArea / totalArea) * 1000) / 10 : 0 };
});
console.log('Red elements above-fold:', redRatio.redElements);
console.log('Red area pct above-fold:', redRatio.redAreaPct, '%');

const decCards = await page.locator('[data-testid="decision-evidence-card"]').count();
const decSeverityWarning = await page.locator('[data-testid="decision-evidence-card"][data-severity="warning"]').count();
const decSeverityCritical = await page.locator('[data-testid="decision-evidence-card"][data-severity="critical"]').count();
console.log('DEC count:', decCards);
console.log('DEC severity=warning:', decSeverityWarning);
console.log('DEC severity=critical:', decSeverityCritical, '(should be 0 in BRIEFING)');

await ctx.close(); await browser.close();
console.log('OK', OUT);
