/**
 * Playwright Sprint P3 — Workflow Continuity + Executive Demo Flow
 * Tests: cockpit→action, conformité→action, anomalie→action, achat→action,
 *        detail→preuve, detail→clôture, retour contexte source, notifications→action
 */
import { chromium } from 'playwright';

const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const OUT = 'artifacts/playwright/sprint-p3-demo';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Login
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // 1. Cockpit — risk panel with "Créer action" CTA
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/01-cockpit-action-cta.png`, fullPage: false });

  // 2. Cockpit → click "Créer action" from risk panel
  const cockpitCTA = page.locator('[data-testid="cta-cockpit-create-action"]').first();
  if (await cockpitCTA.isVisible({ timeout: 3000 }).catch(() => false)) {
    await cockpitCTA.click({ force: true });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/02-cockpit-create-action-drawer.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 3. Conformité → action
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(3000);
  const confCTA = page.locator('button:has-text("Créer action"), button:has-text("Nouvelle action")').first();
  if (await confCTA.isVisible({ timeout: 3000 }).catch(() => false)) {
    await confCTA.click({ force: true });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/03-conformite-create-action.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 4. Anomalies → action
  await page.goto(`${BASE}/anomalies`);
  await page.waitForTimeout(3000);
  const anomCTA = page.locator('button:has-text("Créer action")').first();
  if (await anomCTA.isVisible({ timeout: 3000 }).catch(() => false)) {
    await anomCTA.click({ force: true });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/04-anomalie-create-action.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  } else {
    await page.screenshot({ path: `${OUT}/04-anomalie-page.png`, fullPage: false });
  }

  // 5. Achat → action (new CTA)
  await page.goto(`${BASE}/achat`);
  await page.waitForTimeout(3000);
  const purchaseCTA = page.locator('[data-testid="cta-creer-action-purchase"]').first();
  if (await purchaseCTA.isVisible({ timeout: 3000 }).catch(() => false)) {
    await purchaseCTA.click({ force: true });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/05-achat-create-action.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  } else {
    await page.screenshot({ path: `${OUT}/05-achat-page.png`, fullPage: false });
  }

  // 6. Actions page — detail drawer with owner edit
  await page.goto(`${BASE}/actions`);
  await page.waitForTimeout(3000);
  const firstRow = page.locator('tr').nth(1);
  if (await firstRow.isVisible().catch(() => false)) {
    await firstRow.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/06-action-detail-owner.png`, fullPage: false });

    // 7. Evidence tab
    const evidenceTab = page.locator('button:has-text("Pièces jointes")').first();
    if (await evidenceTab.isVisible().catch(() => false)) {
      await evidenceTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${OUT}/07-action-evidence.png`, fullPage: false });
    }

    // 8. Back to detail — try close flow
    const detailTab = page.locator('button:has-text("Détail")').first();
    if (await detailTab.isVisible().catch(() => false)) {
      await detailTab.click({ force: true });
      await page.waitForTimeout(500);
    }
    const doneBtn = page.locator('button:has-text("Terminée"):not([disabled])').first();
    if (await doneBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await doneBtn.click({ force: true });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${OUT}/08-action-close-flow.png`, fullPage: false });
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 9. Notifications page — "Créer action" CTA
  await page.goto(`${BASE}/notifications`);
  await page.waitForTimeout(3000);
  // Click first notification to open drawer
  const firstNotif = page.locator('tr').nth(1);
  if (await firstNotif.isVisible().catch(() => false)) {
    await firstNotif.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/09-notification-action-cta.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 10. Bill Intel → action
  await page.goto(`${BASE}/bill-intel`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/10-bill-intel.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
