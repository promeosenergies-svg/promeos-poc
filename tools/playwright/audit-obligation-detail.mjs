/**
 * Audit — Obligation detail expansion (base légale, options, pénalités, audit trail)
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
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 2400 } }); // tall viewport
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

  // ── Public mode first ──
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // Click Obligations tab
  const oblTab = page.locator('button').filter({ hasText: 'Obligations' }).last();
  await oblTab.click();
  await page.waitForTimeout(2000);

  // Try clicking the first obligation card (border-l-4 cards)
  const cards = page.locator('[class*="border-l-4"]');
  const cardCount = await cards.count();
  console.log(`Found ${cardCount} obligation cards`);

  if (cardCount > 0) {
    // Click BACS card specifically
    const bacsCard = page.locator('text=BACS').first();
    await bacsCard.click();
    await page.waitForTimeout(2000);
    await snap('OBL-01-bacs-expanded-public');

    // Try clicking on "Voir le détail" or expand button
    const detailBtn = page.locator('button:has-text("détail"), button:has-text("Voir"), [class*="chevron"]').first();
    if (await detailBtn.isVisible()) {
      await detailBtn.click();
      await page.waitForTimeout(1500);
      await snap('OBL-01b-bacs-detail-public');
    }
  }

  // ── Expert mode ──
  const expertToggle = page.locator('text=Expert').first();
  if (await expertToggle.isVisible()) {
    await expertToggle.click();
    await page.waitForTimeout(2000);
  }

  // Re-click obligations tab
  const oblTab2 = page.locator('button').filter({ hasText: 'Obligations' }).last();
  await oblTab2.click();
  await page.waitForTimeout(2000);

  // Click BACS card
  const bacsCard2 = page.locator('text=BACS').first();
  if (await bacsCard2.isVisible()) {
    await bacsCard2.click();
    await page.waitForTimeout(2000);
    await snap('OBL-02-bacs-expanded-expert');
  }

  // Try to find and click Décret Tertiaire card
  const dtCard = page.locator('text=Décret Tertiaire').or(page.locator('text=Tertiaire')).first();
  if (await dtCard.isVisible()) {
    await dtCard.click();
    await page.waitForTimeout(2000);
    await snap('OBL-03-dt-expanded-expert');
  }

  // Try Loi APER
  const aperCard = page.locator('text=APER').first();
  if (await aperCard.isVisible()) {
    await aperCard.click();
    await page.waitForTimeout(2000);
    await snap('OBL-04-aper-expanded-expert');
  }

  // ── ExecutionTab within conformité page ──
  // Navigate fresh and click Plan d'exécution tab (the one inside conformité, not navigation)
  await page.goto(`${FRONTEND}/conformite`);
  await page.waitForTimeout(3000);

  // The 5-tab bar: Obligations | Données & Qualité | Plan d'exécution | Preuves & Rapports
  // Need to precisely target the right "Plan d'exécution" — inside tab bar
  const allBtns = page.locator('button');
  const btnCount = await allBtns.count();
  for (let i = 0; i < btnCount; i++) {
    const txt = (await allBtns.nth(i).textContent()).trim();
    if (txt.includes("exécution") || txt.includes("Plan d")) {
      console.log(`  btn[${i}]: "${txt}"`);
    }
  }

  // Try clicking the last occurrence of "Plan d'exécution" (should be in tab bar)
  const execTabs = page.locator('button').filter({ hasText: /Plan d/ });
  const execCount = await execTabs.count();
  console.log(`Found ${execCount} "Plan d" buttons`);
  if (execCount > 0) {
    // The first one is likely in the "PARCOURS" mini tabs, the last in the main tab bar
    await execTabs.last().click();
    await page.waitForTimeout(2000);

    // Check if we're still on /conformite
    const url = page.url();
    console.log(`After click: ${url}`);
    if (url.includes('conformite')) {
      await snap('Z5-execution-in-conformite');
    } else {
      console.log('[WARN] Navigated away from conformite');
      await snap('Z5-execution-navigated-away');
    }
  }

  await browser.close();
  console.log('\n=== Done ===');
}

run().catch((e) => { console.error(e); process.exit(1); });
