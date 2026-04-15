/**
 * Playwright Sprint P2 Workflow — BEFORE screenshots
 */
import { chromium } from 'playwright';

const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const OUT = 'artifacts/playwright/sprint-p2-workflow-before';

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

  // 1. Actions page — kanban view
  await page.goto(`${BASE}/actions`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-actions-list.png`, fullPage: false });

  // Try to click kanban toggle if available
  const kanbanBtn = page.locator('button:has-text("Kanban"), [data-testid="kanban-toggle"]').first();
  if (await kanbanBtn.isVisible().catch(() => false)) {
    await kanbanBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${OUT}/02-actions-kanban.png`, fullPage: false });
  }

  // 2. Click first action to open detail drawer
  const firstAction = page.locator('tr[class*="cursor"], [data-testid*="action-row"]').first();
  if (await firstAction.isVisible().catch(() => false)) {
    await firstAction.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/03-action-detail-drawer.png`, fullPage: false });

    // Click evidence tab
    const evidenceTab = page.locator('button:has-text("Pièces jointes")').first();
    if (await evidenceTab.isVisible().catch(() => false)) {
      await evidenceTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${OUT}/04-action-evidence-tab.png`, fullPage: false });
    }

    // Click history tab
    const historyTab = page.locator('button:has-text("Historique")').first();
    if (await historyTab.isVisible().catch(() => false)) {
      await historyTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${OUT}/05-action-history-tab.png`, fullPage: false });
    }

    // Close drawer
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  // 3. Cockpit — check CTA to actions
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/06-cockpit-actions-cta.png`, fullPage: false });

  // 4. Monitoring — check action creation
  await page.goto(`${BASE}/sites/1`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/07-site-detail-actions.png`, fullPage: false });

  // 5. Conformité — check action CTA
  await page.goto(`${BASE}/conformite`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/08-conformite-actions.png`, fullPage: false });

  await browser.close();
  console.log(`Done — screenshots saved to ${OUT}/`);
}

run().catch((e) => { console.error(e); process.exit(1); });
