// M2-5.10.B — Audit capture du drawer détail dans tous ses états.
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const OUT = 'tools/playwright/captures/m2_5_10b_drawer_audit';
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

  console.log('2. Navigate to /action-center-v4');
  await page.goto(`${FE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.waitForSelector('tbody tr', { timeout: 10000 });

  console.log('3. Ouvre drawer sur action vedette P0 (1ère ligne)');
  await page.locator('tbody tr').first().click();
  await page.waitForTimeout(500);
  await shoot(page, '01-drawer-default-timeline');

  console.log('4. Onglet Preuves');
  await page.getByText('Preuves', { exact: true }).first().click();
  await page.waitForTimeout(500);
  await shoot(page, '02-drawer-evidences-tab');

  console.log('5. Onglet Blocages');
  await page.getByText('Blocages', { exact: true }).first().click();
  await page.waitForTimeout(500);
  await shoot(page, '03-drawer-blockers-tab');

  console.log('6. Onglet Liens');
  await page.getByText('Liens', { exact: true }).first().click();
  await page.waitForTimeout(500);
  await shoot(page, '04-drawer-links-tab');

  console.log('7. Ouvre menu Plus ▾');
  await page.getByRole('button', { name: /plus d'actions/i }).click();
  await page.waitForTimeout(300);
  await shoot(page, '05-drawer-more-menu-open');

  // Ferme le menu pour ne pas perturber la suite.
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);

  console.log('8. Ferme drawer + ouvre item closed (action 5 ou 6)');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  // Cherche une ligne avec lifecycle closed dans la liste (action 5 ou 6 du seed).
  const closedRow = page.locator('tbody tr[data-priority="P3"]').first();
  if (await closedRow.count()) {
    await closedRow.click();
    await page.waitForTimeout(500);
    await shoot(page, '06-drawer-closed-item-actions-disabled');
  } else {
    console.log('  ⚠ Pas de ligne P3 (closed) trouvée — skip');
  }

  console.log('9. Drawer item P0 (action vedette) onglet timeline avec scroll bas');
  await page.keyboard.press('Escape');
  await page.locator('tbody tr').first().click();
  await page.waitForTimeout(500);
  // Scroll dans le drawer pour voir le footer.
  await page.evaluate(() => {
    const drawer = document.querySelector('[role="dialog"]');
    if (drawer) drawer.scrollTop = drawer.scrollHeight;
  });
  await page.waitForTimeout(300);
  await shoot(page, '07-drawer-footer-scrolled');

  await browser.close();
  console.log(`\n✓ Captures dans ${OUT}/`);
})();
