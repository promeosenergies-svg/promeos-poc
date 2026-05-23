/**
 * M2-5.8.B Phase 0 — walkthrough navigateur (STOP gate). Scratch, non commité.
 * Usage : node tools/playwright/_m2_5_8b_phase0.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://127.0.0.1:5176';
const OUT = 'tools/playwright/captures/m2_5_8b_phase0';
mkdirSync(OUT, { recursive: true });

const results = [];
const consoleErrors = [];
const failedRequests = [];
const v4_401 = [];
let postLogin = false;

function rec(n, label, ok, note) {
  results.push({ n, ok });
  console.log(`  ${ok ? 'OK' : 'KO'}  [${n}] ${label}${note ? ' — ' + note : ''}`);
}

const browser = await chromium.launch();
const page = await browser.newPage();

page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text());
});
page.on('requestfailed', (r) => failedRequests.push(`${r.url()} :: ${r.failure()?.errorText}`));
page.on('response', (r) => {
  if (r.status() === 401 && r.url().includes('/api/v4/')) {
    v4_401.push({ url: r.url(), postLogin });
  }
});

try {
  // ── Étape 1 — page sans token → DemoLoginPrompt ──
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: `${OUT}/01-no-token.png`, fullPage: true });
  const promptVisible = await page
    .getByText('Mode démo HELIOS')
    .isVisible()
    .catch(() => false);
  const btnVisible = await page
    .getByRole('button', { name: /se connecter/i })
    .isVisible()
    .catch(() => false);
  rec(1, 'Page sans token → DemoLoginPrompt', promptVisible && btnVisible, `prompt=${promptVisible} bouton=${btnVisible}`);

  // ── Étape 2 — clic "Se connecter (démo)" ──
  postLogin = true;
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page
    .getByText('Mode démo HELIOS')
    .waitFor({ state: 'hidden', timeout: 12000 })
    .catch(() => {});
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `${OUT}/02-after-login.png`, fullPage: true });
  const promptGone = !(await page
    .getByText('Mode démo HELIOS')
    .isVisible()
    .catch(() => false));
  rec(2, 'Clic "Se connecter" → prompt disparaît', promptGone, `prompt_gone=${promptGone}`);

  // ── Étape 3 — liste affichée, 9 items ──
  const rowCount = await page.locator('tbody tr').count();
  rec(3, 'Liste affichée (9 items HELIOS)', rowCount === 9, `lignes=${rowCount}`);

  // ── Étape 4 — clic ligne OPERAT → drawer (item riche : 8 events) ──
  const operatRow = page.locator('tbody tr', { hasText: 'Déclaration OPERAT 2025' });
  await operatRow.first().click();
  const dialog = page.getByRole('dialog');
  const dialogVisible = await dialog.isVisible().catch(() => false);
  await page.screenshot({ path: `${OUT}/03-drawer.png`, fullPage: true });
  rec(4, 'Clic ligne → drawer ouvert', dialogVisible, `dialog=${dialogVisible}`);

  // ── Étape 5 — onglet Timeline : events affichés ──
  const tlTab = page.getByRole('button', { name: /timeline|chronologie|journal/i });
  if (await tlTab.first().isVisible().catch(() => false)) {
    await tlTab.first().click().catch(() => {});
  }
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/04-timeline.png`, fullPage: true });
  const dialogText = await page
    .getByRole('dialog')
    .innerText()
    .catch(() => '');
  const hasEvents = /Marie Dupont/.test(dialogText);
  rec(5, 'Onglet Timeline — events affichés (actor visible)', hasEvents, `"Marie Dupont" détecté=${hasEvents}`);

  // ── Étape 6 — F5 → liste persiste ──
  await page.reload({ waitUntil: 'networkidle' });
  await page.screenshot({ path: `${OUT}/05-after-reload.png`, fullPage: true });
  const rowsAfter = await page.locator('tbody tr').count();
  const promptAfter = await page
    .getByText('Mode démo HELIOS')
    .isVisible()
    .catch(() => false);
  rec(6, 'F5 → liste persiste (token survit)', rowsAfter > 0 && !promptAfter, `lignes=${rowsAfter} prompt=${promptAfter}`);

  // ── Bonus — focus clavier (P0-4 attendu : lignes NON focusables) ──
  await page.locator('body').click();
  for (let i = 0; i < 4; i++) await page.keyboard.press('Tab');
  const focused = await page.evaluate(() => {
    const el = document.activeElement;
    return el ? `${el.tagName}${el.getAttribute('role') ? `[role=${el.getAttribute('role')}]` : ''}` : 'none';
  });
  console.log(`\n  bonus — focus après 4×Tab : ${focused} (attendu : pas un TR → P0-4 à fixer)`);
} catch (e) {
  console.log('ERREUR walkthrough :', e.message);
} finally {
  console.log('');
  console.log(`Console errors React : ${consoleErrors.length}`);
  consoleErrors.slice(0, 6).forEach((e) => console.log(`  - ${e.slice(0, 180)}`));
  console.log(`Requêtes en échec : ${failedRequests.length}`);
  failedRequests.slice(0, 6).forEach((e) => console.log(`  - ${e}`));
  const pre = v4_401.filter((x) => !x.postLogin).length;
  const post = v4_401.filter((x) => x.postLogin).length;
  console.log(`401 sur /api/v4/ : ${pre} avant login (attendu), ${post} après login (doit être 0)`);
  const ok = results.filter((r) => r.ok).length;
  console.log(`\n═══ Phase 0 walkthrough : ${ok}/6 ═══`);
  await browser.close();
  process.exit(ok === 6 ? 0 : 1);
}
