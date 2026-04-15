/**
 * Audit Conformité V1.1 — Tab-specific captures
 * Stays on /conformite and clicks each tab precisely.
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
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Auth
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

  // Go to conformite
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // Find all tab buttons
  const tabButtons = page.locator('button[role="tab"], [class*="tab"] button, button').filter({ hasText: /Obligations|Données|Plan d|Preuves/ });
  const tabCount = await tabButtons.count();
  console.log(`Found ${tabCount} tab buttons`);

  // List all buttons text for debugging
  for (let i = 0; i < tabCount; i++) {
    const text = await tabButtons.nth(i).textContent();
    console.log(`  Tab ${i}: "${text.trim()}"`);
  }

  // Click "Plan d'exécution" tab
  const planTab = page.getByRole('tab', { name: /plan/i }).or(page.locator('button').filter({ hasText: /Plan d/i })).first();
  if (await planTab.isVisible()) {
    await planTab.click();
    await page.waitForTimeout(2000);
    await snap('Z5-plan-execution-tab');

    // Scroll down
    await page.evaluate(() => window.scrollTo(0, 400));
    await page.waitForTimeout(500);
    await snap('Z5b-plan-execution-scroll');
  } else {
    console.log('[WARN] Plan d execution tab not found');
  }

  // Click "Données & Qualité" tab
  const donneesTab = page.getByRole('tab', { name: /donn/i }).or(page.locator('button').filter({ hasText: /Donn/i })).first();
  if (await donneesTab.isVisible()) {
    await donneesTab.click();
    await page.waitForTimeout(2000);
    await snap('Z6-donnees-qualite-tab');
  } else {
    console.log('[WARN] Données tab not found');
  }

  // Now expand obligation in expert mode to see audit trail detail
  // First go back to Obligations tab + expert mode
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // Enable expert
  const expertToggle = page.locator('text=Expert').first();
  if (await expertToggle.isVisible()) {
    await expertToggle.click();
    await page.waitForTimeout(1500);
  }

  // Click obligations tab
  const oblTab = page.locator('button').filter({ hasText: /Obligations/i }).first();
  if (await oblTab.isVisible()) {
    await oblTab.click();
    await page.waitForTimeout(1500);
  }

  // Scroll to see obligations
  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(500);

  // Click on first obligation card to expand it
  const oblCard = page.locator('text=BACS (GTB/GTC)').first();
  if (await oblCard.isVisible()) {
    await oblCard.click();
    await page.waitForTimeout(1500);
    await snap('Z3c-expert-obligation-expanded');

    // Scroll to see detail (legal basis, options, audit trail)
    await page.evaluate(() => window.scrollTo(0, 900));
    await page.waitForTimeout(500);
    await snap('Z3d-expert-obligation-detail');

    await page.evaluate(() => window.scrollTo(0, 1400));
    await page.waitForTimeout(500);
    await snap('Z3e-expert-obligation-bottom');

    await page.evaluate(() => window.scrollTo(0, 1900));
    await page.waitForTimeout(500);
    await snap('Z3f-expert-obligation-deep');
  }

  // Dossier close-up: click Dossier, then scroll inside
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  const dossierBtn = page.locator('button').filter({ hasText: /Dossier/ }).first();
  if (await dossierBtn.isVisible()) {
    await dossierBtn.click();
    await page.waitForTimeout(2000);
    await snap('Z9a-dossier-top');

    await page.evaluate(() => {
      const modal = document.querySelector('[class*="modal"], [class*="drawer"], [class*="print"], [class*="dossier"]');
      if (modal) modal.scrollTop = 600;
      else window.scrollTo(0, 600);
    });
    await page.waitForTimeout(500);
    await snap('Z9b-dossier-middle');

    await page.evaluate(() => {
      const modal = document.querySelector('[class*="modal"], [class*="drawer"], [class*="print"], [class*="dossier"]');
      if (modal) modal.scrollTop = 1200;
      else window.scrollTo(0, 1200);
    });
    await page.waitForTimeout(500);
    await snap('Z9c-dossier-bottom');
  }

  await browser.close();
  console.log(`\n=== Done. ===`);
}

run().catch((e) => { console.error(e); process.exit(1); });
