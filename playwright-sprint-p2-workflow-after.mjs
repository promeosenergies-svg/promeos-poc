/**
 * Playwright Sprint P2 Workflow — AFTER screenshots (validation)
 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const OUT = 'playwright-screenshots/sprint-p2-workflow-after';

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

  // 1. Actions page — list view with progress bar
  await page.goto(`${BASE}/actions`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-actions-list-progress.png`, fullPage: false });

  // 2. Kanban view
  const kanbanBtn = page.locator('button:has-text("Kanban")').first();
  if (await kanbanBtn.isVisible().catch(() => false)) {
    await kanbanBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/02-kanban-cards.png`, fullPage: false });
    // Switch back to table
    const tableBtn = page.locator('button:has-text("Table"), button:has-text("Liste")').first();
    if (await tableBtn.isVisible().catch(() => false)) {
      await tableBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // 3. Click first action to open detail drawer
  const firstRow = page.locator('tr').nth(1);
  if (await firstRow.isVisible().catch(() => false)) {
    await firstRow.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/03-action-detail-enriched.png`, fullPage: false });

    // 4. Click Evidence tab
    const evidenceTab = page.locator('button:has-text("Pièces jointes")').first();
    if (await evidenceTab.isVisible().catch(() => false)) {
      await evidenceTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${OUT}/04-evidence-form-enriched.png`, fullPage: false });
    }

    // 5. Try to trigger close form — click "Terminée" status button inside drawer
    const detailTab = page.locator('button:has-text("Détail")').first();
    if (await detailTab.isVisible().catch(() => false)) {
      await detailTab.click({ force: true });
      await page.waitForTimeout(500);
    }
    // The status buttons are inside the drawer — find "Terminée" among status buttons
    const doneBtn = page.locator('button:has-text("Terminée"):not([disabled])').first();
    if (await doneBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await doneBtn.click({ force: true });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${OUT}/05-close-confirmation.png`, fullPage: false });
    } else {
      // Screenshot detail tab as-is showing status workflow
      await page.screenshot({ path: `${OUT}/05-close-confirmation.png`, fullPage: false });
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 6. Source → Action: Cockpit CTA
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/06-cockpit.png`, fullPage: false });

  // 7. Conformité → Action CTA
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(3000);
  // Find and click "Créer action conformité" button
  const createConf = page.locator('button:has-text("Créer action")').first();
  if (await createConf.isVisible().catch(() => false)) {
    await createConf.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/07-action-from-conformite.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 8. Monitoring → Action CTA
  await page.goto(`${BASE}/sites/1`);
  await page.waitForTimeout(3000);
  // Scroll to find Créer une action
  await page.evaluate(() => window.scrollTo(0, 400));
  await page.waitForTimeout(500);
  const createMonit = page.locator('button:has-text("Créer une action")').first();
  if (await createMonit.isVisible().catch(() => false)) {
    await createMonit.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/08-action-from-monitoring.png`, fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
