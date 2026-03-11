/**
 * Audit Conformité V1.1 — Deep zone capture
 * Captures all 8 audit zones: entry page, obligations expanded, expert mode,
 * preuves tab, execution tab, dossier, sidebar navigation, legacy check.
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND = 'http://localhost:5173';
const BACKEND  = 'http://localhost:8001';
const OUT_DIR  = resolve(import.meta.dirname || '.', 'captures', 'deep-v11');

mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Auth
  console.log('[AUTH] Login...');
  const res = await (await fetch(`${BACKEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
  })).json();
  const token = res.token || res.access_token;
  await page.goto(FRONTEND);
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), token);
  console.log('[AUTH] OK');

  // Helper
  const snap = async (name) => {
    await page.waitForTimeout(1500);
    const path = join(OUT_DIR, `${name}.png`);
    await page.screenshot({ path, fullPage: true });
    console.log(`[SNAP] ${name}`);
  };

  // ── ZONE 1: PAGE D'ENTRÉE CONFORMITÉ ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(2000);
  await snap('Z1-conformite-entree');

  // ── ZONE 1bis: Scroll down to see summary banner + top3 urgences ──
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('Z1b-conformite-top');

  // ── ZONE 2: OBLIGATIONS TAB — click first obligation to expand ──
  // Click on "Obligations" tab if not already selected
  const oblTab = page.locator('button:has-text("Obligations")').first();
  if (await oblTab.isVisible()) await oblTab.click();
  await page.waitForTimeout(1500);
  await snap('Z2a-obligations-tab');

  // Expand first obligation card
  const firstObl = page.locator('[class*="border-l-4"]').first();
  if (await firstObl.isVisible()) {
    await firstObl.click();
    await page.waitForTimeout(1000);
  }
  await snap('Z2b-obligation-expanded');

  // Scroll to see full obligation detail (legal basis, options, penalties)
  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(500);
  await snap('Z2c-obligation-detail-scroll');

  // ── ZONE 3: MODE EXPERT ──
  // Toggle expert mode
  const expertToggle = page.locator('button:has-text("Expert"), label:has-text("Expert"), [class*="expert"]').first();
  if (await expertToggle.isVisible()) {
    await expertToggle.click();
    await page.waitForTimeout(1500);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('Z3a-expert-mode-top');

  // Scroll down in expert mode to see audit trail
  await page.evaluate(() => window.scrollTo(0, 800));
  await page.waitForTimeout(500);
  await snap('Z3b-expert-mode-detail');

  // ── ZONE 4: PREUVES TAB ──
  const preuvesTab = page.locator('button:has-text("Preuves")').first();
  if (await preuvesTab.isVisible()) {
    await preuvesTab.click();
    await page.waitForTimeout(1500);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('Z4a-preuves-tab');

  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(500);
  await snap('Z4b-preuves-detail');

  // ── ZONE 5: EXECUTION TAB (Plan d'exécution) ──
  const execTab = page.locator('button:has-text("exécution"), button:has-text("Plan d")').first();
  if (await execTab.isVisible()) {
    await execTab.click();
    await page.waitForTimeout(1500);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('Z5a-execution-tab');

  // Click first action row to expand
  const firstAction = page.locator('[class*="border-gray-200"][class*="rounded-lg"]').first();
  if (await firstAction.isVisible()) {
    await firstAction.click();
    await page.waitForTimeout(1000);
  }
  await snap('Z5b-execution-expanded');

  // ── ZONE 6: DONNEES TAB ──
  const donneesTab = page.locator('button:has-text("Données"), button:has-text("Donn")').first();
  if (await donneesTab.isVisible()) {
    await donneesTab.click();
    await page.waitForTimeout(1500);
  }
  await snap('Z6-donnees-tab');

  // ── ZONE 7: Toggle expert OFF for public view comparison ──
  // Toggle expert back off
  const expertOff = page.locator('button:has-text("Expert"), label:has-text("Expert"), [class*="expert"]').first();
  if (await expertOff.isVisible()) {
    await expertOff.click();
    await page.waitForTimeout(1000);
  }
  // Back to obligations tab in non-expert mode
  const oblTab2 = page.locator('button:has-text("Obligations")').first();
  if (await oblTab2.isVisible()) await oblTab2.click();
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap('Z7-public-mode-obligations');

  // ── ZONE 8: SIDEBAR CHECK — verify no legacy page ──
  // Capture full sidebar
  await page.goto(`${FRONTEND}/patrimoine`);
  await page.waitForTimeout(2000);
  await snap('Z8a-sidebar-patrimoine');

  // Try legacy /compliance route
  await page.goto(`${FRONTEND}/compliance`);
  await page.waitForTimeout(2000);
  await snap('Z8b-legacy-compliance-check');

  // ── ZONE 9: DOSSIER — try to open print view ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(2000);
  // Look for "Dossier" button
  const dossierBtn = page.locator('button:has-text("Dossier"), a:has-text("Dossier")').first();
  if (await dossierBtn.isVisible()) {
    await dossierBtn.click();
    await page.waitForTimeout(2000);
    await snap('Z9-dossier-print');
  } else {
    console.log('[WARN] Dossier button not found on conformite page');
    // Try scrolling to find it
    await page.evaluate(() => window.scrollTo(0, 9999));
    await page.waitForTimeout(1000);
    await snap('Z9-conformite-bottom-no-dossier');
  }

  // ── ZONE 10: CONFORMITE TERTIAIRE subpage ──
  await page.goto(`${FRONTEND}/conformite/tertiaire`);
  await page.waitForTimeout(2000);
  await snap('Z10-conformite-tertiaire');

  await browser.close();
  console.log(`\n=== Done. ${OUT_DIR} ===`);
}

run().catch((e) => { console.error(e); process.exit(1); });
