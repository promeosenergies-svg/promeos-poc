/**
 * Phase 13.D — Audit nav démo CFO + footer signaux moat.
 *
 * 1. Vérifie que la sidebar place "Vue exécutive" AVANT "Tableau de bord"
 * 2. Vérifie que /cockpit redirige sur /cockpit/strategique (et plus /jour)
 * 3. Vérifie que le footer signaux moat (VNU/TURPE 7/APER) est rendu sur
 *    /cockpit/strategique
 * 4. Capture screenshot pleine page pour validation visuelle
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const FRONT = 'http://localhost:5175';
const OUT_DIR = 'tools/playwright/captures';
const SHOT_PATH = `${OUT_DIR}/phase13d_nav_moat.png`;
const FOOTER_SHOT = `${OUT_DIR}/phase13d_moat_footer.png`;

mkdirSync(OUT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

// Login
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

// Test 1 : /cockpit redirige sur strategique (Phase 13.D)
console.log('\n→ Test 1 : redirect /cockpit → /cockpit/strategique');
await page.goto(`${FRONT}/cockpit`, { waitUntil: 'networkidle' });
const finalUrl1 = page.url();
const redirect_ok = finalUrl1.endsWith('/cockpit/strategique');
console.log(`  URL finale = ${finalUrl1} → ${redirect_ok ? '✓ OK' : '✗ FAIL (attendu /cockpit/strategique)'}`);

// Test 2 : sidebar place "Vue exécutive" AVANT "Tableau de bord"
console.log('\n→ Test 2 : ordre sidebar (Vue exécutive en premier)');
const navLabels = await page.evaluate(() => {
  // Filtre par module Cockpit (Accueil) — premiers 2 items
  const items = Array.from(document.querySelectorAll('a[href*="/cockpit"]'));
  return items
    .map((el) => el.textContent?.trim() || '')
    .filter((t) => /Vue ex|Tableau de bord/i.test(t))
    .slice(0, 2);
});
const order_ok = navLabels[0]?.includes('Vue exécutive') && navLabels[1]?.includes('Tableau de bord');
console.log(`  navLabels = ${JSON.stringify(navLabels)} → ${order_ok ? '✓ OK' : '✗ FAIL'}`);

// Test 3 : footer signaux moat rendu
console.log('\n→ Test 3 : footer signaux moat (VNU + TURPE 7 + APER)');
await page.waitForTimeout(1500); // laisser fetchs se résoudre
const moatChecks = await page.evaluate(() => {
  const text = document.body.innerText || '';
  return {
    has_label: /Suivi exclusif post-ARENH/i.test(text),
    has_vnu: /VNU/.test(text) && /seuil 78\s?€\/MWh/i.test(text),
    has_turpe: /TURPE 7/.test(text) && /HC méridiennes/i.test(text),
    has_aper: /APER/.test(text) && /1\s?500 m²/i.test(text),
  };
});
const moat_ok =
  moatChecks.has_label && moatChecks.has_vnu && moatChecks.has_turpe && moatChecks.has_aper;
console.log(`  ${JSON.stringify(moatChecks)} → ${moat_ok ? '✓ OK' : '✗ FAIL'}`);

// Capture pleine page
await page.screenshot({ path: SHOT_PATH, fullPage: true });
console.log(`\n✓ Full page capture → ${SHOT_PATH}`);

// Capture moat footer (scroll jusqu'au footer puis screenshot ciblé)
const moatLocator = page.locator('[data-print-hide]').last();
try {
  await moatLocator.scrollIntoViewIfNeeded();
  await moatLocator.screenshot({ path: FOOTER_SHOT });
  console.log(`✓ Moat footer capture → ${FOOTER_SHOT}`);
} catch (e) {
  console.log(`  (moat element scroll failed: ${e.message})`);
}

// Verdict global
const ok = redirect_ok && order_ok && moat_ok;
console.log(`\n${ok ? '✅ PASS' : '❌ FAIL'} — Phase 13.D nav démo CFO + footer signaux moat`);

await browser.close();
process.exit(ok ? 0 : 1);
