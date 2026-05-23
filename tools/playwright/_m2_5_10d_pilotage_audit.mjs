// M2-5.10.D — Capture audit page Pilotage / File prioritaire.
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const OUT = 'tools/playwright/captures/m2_5_10d_pilotage_audit';
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

  console.log('2. Navigate to Pilotage');
  await page.goto(`${FE}/action-center-v4/pilotage`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shoot(page, '01-pilotage-default');

  console.log('3. Switch to Référentiel via tab');
  await page.getByRole('tab', { name: /référentiel/i }).click();
  await page.waitForTimeout(500);
  await shoot(page, '02-tab-referentiel');

  console.log('4. Switch back to Pilotage');
  await page.getByRole('tab', { name: /pilotage/i }).click();
  await page.waitForTimeout(500);
  await shoot(page, '03-tab-pilotage');

  console.log('5. Click 1st priority card → opens drawer');
  await page.locator('[role="button"][aria-label*="Ouvrir"]').first().click();
  await page.waitForTimeout(500);
  await shoot(page, '04-pilotage-drawer-open');

  await browser.close();
  console.log(`\n✓ Captures dans ${OUT}/`);
})();
