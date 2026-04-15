/**
 * Audit — Force-expand obligation cards to see detail sections
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const BACKEND  = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const OUT_DIR  = resolve(process.cwd(), 'artifacts', 'audits', 'captures', 'deep-v11');
mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 3000 } });
  const page = await ctx.newPage();

  const res = await (await fetch(`${BACKEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
  })).json();
  await page.goto(FRONTEND);
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), res.token || res.access_token);

  const snap = async (name) => {
    await page.waitForTimeout(1500);
    await page.screenshot({ path: join(OUT_DIR, `${name}.png`), fullPage: true });
    console.log(`[SNAP] ${name}`);
  };

  // ── PUBLIC MODE ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // Click Obligations tab (last one with that text)
  await page.locator('button').filter({ hasText: 'Obligations' }).last().click();
  await page.waitForTimeout(2000);

  // Find chevron-down icons inside obligation cards — these are the expand buttons
  // The ObligationsTab uses ChevronDown/ChevronUp for expansion
  const chevrons = page.locator('svg.lucide-chevron-down, [class*="chevron"]');
  const chCount = await chevrons.count();
  console.log(`Found ${chCount} chevron-down icons`);

  // Alternative: find the border-l-4 cards and click the main clickable area
  const oblCards = page.locator('[class*="border-l-4"]');
  const cardCount = await oblCards.count();
  console.log(`Found ${cardCount} obligation cards`);

  // Click each card's header area to expand it
  for (let i = 0; i < Math.min(cardCount, 3); i++) {
    const card = oblCards.nth(i);
    // Find the clickable header div inside
    const clickTarget = card.locator('div[class*="cursor-pointer"], button, div').first();
    try {
      await clickTarget.click();
      await page.waitForTimeout(1000);
      console.log(`  Expanded card ${i}`);
    } catch (e) {
      console.log(`  Failed to expand card ${i}: ${e.message.slice(0, 80)}`);
    }
  }

  await snap('EXPAND-01-all-public');

  // ── EXPERT MODE ──
  await page.locator('text=Expert').first().click();
  await page.waitForTimeout(1500);

  // Re-expand
  for (let i = 0; i < Math.min(cardCount, 3); i++) {
    const card = oblCards.nth(i);
    const clickTarget = card.locator('div').first();
    try {
      await clickTarget.click();
      await page.waitForTimeout(500);
    } catch(e) {}
  }
  await page.waitForTimeout(1000);

  // Actually, the cards might have re-rendered. Let me re-find and expand all.
  const oblCards2 = page.locator('[class*="border-l-4"]');
  const c2 = await oblCards2.count();
  console.log(`Expert: ${c2} obligation cards`);

  // Try to expand all of them by clicking inside each card
  for (let i = 0; i < c2; i++) {
    try {
      // Click the first clickable area in each card
      await oblCards2.nth(i).locator('div').first().click();
      await page.waitForTimeout(500);
    } catch(e) {}
  }

  await snap('EXPAND-02-all-expert');

  // Now try the "force expand all" approach: use page.evaluate to trigger all accordion opens
  await page.evaluate(() => {
    // Click all elements that have chevron-down svg (expand triggers)
    document.querySelectorAll('svg').forEach(svg => {
      const classes = svg.getAttribute('class') || '';
      if (classes.includes('chevron-down') || svg.innerHTML?.includes('polyline')) {
        const parent = svg.closest('button') || svg.closest('div[class*="cursor"]') || svg.parentElement;
        if (parent) parent.click();
      }
    });
  });
  await page.waitForTimeout(2000);
  await snap('EXPAND-03-force-all-expert');

  await browser.close();
  console.log('\n=== Done ===');
}

run().catch((e) => { console.error(e); process.exit(1); });
