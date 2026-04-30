/** Capture ciblée de la courbe de charge Pilotage (régression Phase 14.bis). */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const FRONT = 'http://localhost:5175';
mkdirSync('tools/playwright/captures/phase13_audit', { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

await page.goto(`${FRONT}/login`, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
const emailField = await page.$('input[type=email]');
if (emailField) {
  await page.fill('input[type=email]', 'promeos@promeos.io');
  await page.fill('input[type=password]', 'promeos2024');
  await Promise.all([
    page.waitForLoadState('networkidle').catch(() => {}),
    page.press('input[type=password]', 'Enter'),
  ]);
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 8000 }).catch(() => {});
}

await page.goto(`${FRONT}/cockpit/jour`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);

// Trouver la courbe via aria-label
const courbe = page.locator('svg[aria-label="Courbe de charge J moins 1 du groupe"]').first();
try {
  await courbe.scrollIntoViewIfNeeded();
  await courbe.screenshot({ path: 'tools/playwright/captures/phase13_audit/courbe_charge_fix.png' });
  console.log('✓ Courbe charge capturée');
} catch (e) {
  console.log(`✗ ${e.message}`);
}

// Capture la card complète (label + svg + footer)
const card = courbe.locator('xpath=ancestor::div[contains(@class, "rounded-md")]').first();
try {
  await card.screenshot({ path: 'tools/playwright/captures/phase13_audit/courbe_charge_card.png' });
  console.log('✓ Card complète capturée');
} catch (e) {
  console.log(`✗ Card: ${e.message}`);
}

await browser.close();
