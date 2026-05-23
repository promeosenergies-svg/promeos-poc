/** M2-5.8.A.bis Phase 0 — LoginPage legacy email+password. Scratch, non commité. */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://127.0.0.1:5176';
const OUT = 'tools/playwright/captures/m2_5_8abis_phase0';
mkdirSync(OUT, { recursive: true });

const results = [];
function rec(n, label, ok, note) {
  results.push(ok);
  console.log(`  ${ok ? 'OK' : 'KO'}  [${n}] ${label}${note ? ' — ' + note : ''}`);
}

const browser = await chromium.launch();
const page = await browser.newPage();

try {
  // 1 — /login : formulaire visible
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'networkidle' });
  const emailVisible = await page.locator('#login-email').isVisible().catch(() => false);
  const pwdVisible = await page.locator('#login-password').isVisible().catch(() => false);
  const btnVisible = await page.getByRole('button', { name: /se connecter/i }).isVisible().catch(() => false);
  await page.screenshot({ path: `${OUT}/01-login-form.png` });
  rec(1, 'Formulaire login legacy visible', emailVisible && pwdVisible && btnVisible,
      `email=${emailVisible} pwd=${pwdVisible} btn=${btnVisible}`);

  // 2 — login email+password (demo : promeos@promeos.io / promeos2024)
  await page.fill('#login-email', 'promeos@promeos.io');
  await page.fill('#login-password', 'promeos2024');
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 12000 }).catch(() => {});
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `${OUT}/02-after-login.png`, fullPage: true });
  const offLogin = !page.url().includes('/login');
  rec(2, 'Login email+password → quitte /login', offLogin, `url=${page.url()}`);

  // 3 — AppShell présent (rail de nav)
  const navCount = await page.locator('nav, [role=navigation]').count();
  rec(3, 'AppShell / rail de navigation présent', navCount > 0, `nav=${navCount}`);

  // 4 — /action-center-v4 charge la table V4
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  const rows = await page.locator('tbody tr').count();
  await page.screenshot({ path: `${OUT}/03-action-center.png`, fullPage: true });
  rec(4, '/action-center-v4 → table V4 (9 items)', rows === 9, `lignes=${rows}`);

  // 5 — F5 : session persiste
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const rowsAfter = await page.locator('tbody tr').count();
  rec(5, 'F5 → session + table persistent', rowsAfter === 9, `lignes=${rowsAfter}`);
} catch (e) {
  console.log('ERREUR :', e.message);
} finally {
  const ok = results.filter(Boolean).length;
  console.log(`\n═══ Phase 0 (bis) : ${ok}/5 ═══`);
  await browser.close();
  process.exit(ok === 5 ? 0 : 1);
}
