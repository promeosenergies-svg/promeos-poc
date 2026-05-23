// M2-5.10.E — Capture audit page Pilotage / Journal.
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const OUT = 'tools/playwright/captures/m2_5_10e_journal_audit';
const FE = 'http://127.0.0.1:5175';

async function shoot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  📸 ${name}.png`);
}

(async () => {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage();

  console.log('1. Login demo HELIOS');
  await page.goto(`${FE}/login`, { waitUntil: 'networkidle' });
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 10000 }),
    page.getByRole('button', { name: /connexion démo helios/i }).click(),
  ]);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);

  console.log('2. Navigate to Journal');
  await page.goto(`${FE}/action-center-v4/pilotage/journal`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shoot(page, '01-journal-default');

  console.log('3. Switch back to Décisions');
  await page.getByRole('tab', { name: /^décisions$/i }).click();
  await page.waitForTimeout(500);
  await shoot(page, '02-switch-to-decisions');

  console.log('4. Switch back to Journal');
  await page.getByRole('tab', { name: /^journal$/i }).click();
  await page.waitForTimeout(500);
  await shoot(page, '03-back-to-journal');

  console.log('5. Click an item title → drawer open');
  await page.locator('button:has-text("Vérifier consommation")').first().click();
  await page.waitForTimeout(500);
  await shoot(page, '04-journal-drawer-from-event');

  await browser.close();
  console.log(`\n✓ Captures dans ${OUT}/`);
})();
