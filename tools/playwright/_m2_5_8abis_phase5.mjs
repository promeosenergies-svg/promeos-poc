/** M2-5.8.A.bis Phase 5 — walkthrough post-fix (parcours démo). Scratch, non commité. */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://127.0.0.1:5176';
const OUT = 'tools/playwright/captures/m2_5_8abis_phase5';
mkdirSync(OUT, { recursive: true });

const results = [];
const consoleErrors = [];
function rec(n, label, ok, note) {
  results.push(ok);
  console.log(`  ${ok ? 'OK' : 'KO'}  [${n}] ${label}${note ? ' — ' + note : ''}`);
}

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text());
});

try {
  // 1 — /action-center-v4 sans token → redirect /login
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  rec(1, 'Sans token → redirect /login', page.url().includes('/login'), `url=${page.url()}`);

  // 2 — LoginPage : formulaire + "OU" + bouton démo + sous-texte
  await page.screenshot({ path: `${OUT}/01-login-demo-button.png`, fullPage: true });
  const formOk = await page.locator('#login-email').isVisible().catch(() => false);
  const demoBtn = page.getByRole('button', { name: /connexion démo helios/i });
  const demoBtnOk = await demoBtn.isVisible().catch(() => false);
  const subTextOk = await page
    .getByText(/Marie Dupont, Energy Manager HELIOS/i)
    .isVisible()
    .catch(() => false);
  rec(2, 'LoginPage : formulaire + bouton démo + sous-texte', formOk && demoBtnOk && subTextOk,
      `form=${formOk} bouton=${demoBtnOk} sous-texte=${subTextOk}`);

  // 3 — clic "Connexion démo HELIOS" → navigation /action-center-v4
  await demoBtn.click();
  await page.waitForURL((u) => u.pathname === '/action-center-v4', { timeout: 15000 }).catch(() => {});
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  rec(3, 'Clic démo → navigation /action-center-v4', page.url().includes('/action-center-v4'), `url=${page.url()}`);

  // 4 — AppShell (rail nav) + 9 items
  const navCount = await page.locator('nav, [role=navigation]').count();
  const rows = await page.locator('tbody tr').count();
  await page.screenshot({ path: `${OUT}/02-action-center-appshell.png`, fullPage: true });
  rec(4, 'AppShell (rail nav) + 9 items HELIOS', navCount > 0 && rows === 9, `nav=${navCount} lignes=${rows}`);

  // 5 — page legacy accessible (session valide partout)
  await page.goto(`${BASE}/cockpit/strategique`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const onCockpit = page.url().includes('/cockpit') && !page.url().includes('/login');
  rec(5, 'Page legacy /cockpit accessible (session valide)', onCockpit, `url=${page.url()}`);

  // 6 — F5 sur /action-center-v4 → session persiste
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(700);
  const rowsAfter = await page.locator('tbody tr').count();
  await page.screenshot({ path: `${OUT}/03-after-reload.png`, fullPage: true });
  rec(6, 'F5 → session + 9 items persistent', rowsAfter === 9, `lignes=${rowsAfter}`);

  // Bonus B2 — localStorage.clear + reload → redirect /login
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  console.log(`\n  bonus B2 — clear token + reload : url=${page.url()} (attendu /login)`);
} catch (e) {
  console.log('ERREUR walkthrough :', e.message);
} finally {
  console.log(`\nConsole errors React : ${consoleErrors.length}`);
  consoleErrors.slice(0, 6).forEach((e) => console.log(`  - ${e.slice(0, 180)}`));
  const ok = results.filter(Boolean).length;
  console.log(`\n═══ Phase 5 walkthrough : ${ok}/6 ═══`);
  await browser.close();
  process.exit(ok === 6 ? 0 : 1);
}
