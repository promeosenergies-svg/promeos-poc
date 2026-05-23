// M2-5.10.A — Audit capture multi-états (UX + UI + CX + CS).
// Démo login HELIOS (Marie Dupont) → /action-center-v4 → 8 captures.
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const OUT = 'tools/playwright/captures/m2_5_10a_audit';
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
  await shoot(page, '01-login-page');

  // Bouton « Connexion démo HELIOS » (surface M2-5.8.A.bis sur LoginPage).
  // On attend la fin de la requête + la redirection hors de /login avant
  // toute navigation : sinon goto() supplante l'écriture du JWT en cours.
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 10000 }),
    page.getByRole('button', { name: /connexion démo helios/i }).click(),
  ]);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);

  console.log('2. Navigate to /action-center-v4');
  await page.goto(`${FE}/action-center-v4`, { waitUntil: 'networkidle' });
  // L'écran liste lance un fetch /items — attendre que la table soit là.
  await page.waitForSelector('tbody tr', { timeout: 10000 });
  await page.waitForTimeout(300);
  await shoot(page, '02-referentiel-default');

  console.log('3. Hover sur 1ère ligne (table interaction)');
  const firstRow = page.locator('tbody tr').first();
  await firstRow.hover();
  await page.waitForTimeout(200);
  await shoot(page, '03-referentiel-row-hover');

  console.log('4. Filtre kind = Anomalie');
  await page.getByRole('button', { name: /filtrer par anomalie/i }).click();
  await page.waitForTimeout(300);
  await shoot(page, '04-filter-kind-anomalie');

  console.log('5. Filtre lifecycle = closed (vide possible)');
  await page.getByLabel(/état/i).selectOption('closed');
  await page.waitForTimeout(300);
  await shoot(page, '05-filter-kind-anomalie-state-closed');

  console.log('6. Réinitialiser filtres');
  await page.getByRole('button', { name: /réinitialiser les filtres/i }).click();
  await page.waitForTimeout(300);
  await shoot(page, '06-reset-filters');

  console.log('7. Ouverture drawer détail (clic 1ère ligne)');
  await firstRow.click();
  await page.waitForTimeout(500);
  await shoot(page, '07-drawer-open-default');

  console.log('8. Focus clavier (Tab + Enter sur une ligne)');
  // Ferme drawer si encore ouvert.
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  await page.locator('tbody tr').nth(1).focus();
  await page.waitForTimeout(200);
  await shoot(page, '08-keyboard-focus-row');

  await browser.close();
  console.log(`\n✓ 8 captures dans ${OUT}/`);
})();
