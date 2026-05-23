/** M2-5.8.C Phase 9 — walkthrough post-impl. Scratch, non commité. */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://127.0.0.1:5176';
const OUT = 'tools/playwright/captures/m2_5_8c_phase9';
mkdirSync(OUT, { recursive: true });

const results = [];
function rec(n, label, ok, note) {
  results.push(ok);
  console.log(`  ${ok ? 'OK' : 'KO'}  [${n}] ${label}${note ? ' — ' + note : ''}`);
}
const closeDrawer = async (page) => {
  await page.getByLabel('Fermer').click().catch(() => {});
  await page.waitForTimeout(300);
};

const browser = await chromium.launch();
const page = await browser.newPage();

try {
  // Connexion démo → /action-center-v4
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${BASE}/action-center-v4`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /connexion démo helios/i }).click();
  await page.waitForURL((u) => u.pathname === '/action-center-v4', { timeout: 15000 }).catch(() => {});
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  // 1 — table 9 items
  const rows = await page.locator('tbody tr').count();
  rec(1, 'Table /action-center-v4 — 9 items', rows === 9, `lignes=${rows}`);

  // 2 — badge "Critique" (P0) sur l'action vedette
  const vedetteRow = page.locator('tbody tr', { hasText: 'Vérifier consommation HP/HC Q3' });
  const vedetteText = await vedetteRow.first().innerText().catch(() => '');
  await page.screenshot({ path: `${OUT}/01-table.png`, fullPage: true });
  rec(2, 'Action vedette → badge "Critique" (P0)', /Critique/.test(vedetteText), `texte_ligne="${vedetteText.replace(/\s+/g, ' ').trim()}"`);

  // 3 — clic vedette → drawer
  await vedetteRow.first().click();
  const dialogVisible = await page.getByRole('dialog').isVisible().catch(() => false);
  rec(3, 'Clic action vedette → drawer ouvert', dialogVisible, `dialog=${dialogVisible}`);

  // 4 — Timeline : label "Créé" (pas "created" brut)
  const tlTab = page.getByRole('button', { name: /timeline|chronologie/i });
  if (await tlTab.first().isVisible().catch(() => false)) await tlTab.first().click().catch(() => {});
  await page.waitForTimeout(700);
  const drawerText = await page.getByRole('dialog').innerText().catch(() => '');
  await page.screenshot({ path: `${OUT}/02-timeline.png`, fullPage: true });
  rec(4, 'Timeline — label "Créé" affiché (pas brut)', /Créé/.test(drawerText) && !/\bcreated\b/.test(drawerText), `Créé=${/Créé/.test(drawerText)} created_brut=${/\bcreated\b/.test(drawerText)}`);
  await closeDrawer(page);

  // 5 — action 3 : titre "Audit énergétique réglementaire" (pas "SMÉ")
  const audit3 = page.locator('tbody tr', { hasText: 'Audit énergétique réglementaire — Nice Hôtel' });
  const audit3Visible = await audit3.first().isVisible().catch(() => false);
  const smeAbsent = !(await page.getByText('Audit SMÉ obligatoire').isVisible().catch(() => false));
  rec(5, 'Action 3 — titre "Audit énergétique réglementaire" (pas SMÉ)', audit3Visible && smeAbsent, `titre_ok=${audit3Visible} sme_absent=${smeAbsent}`);

  // 6 — description action 3 : L. 233-1 + 2,75 GWh + ISO 50001
  await audit3.first().click();
  await page.waitForTimeout(600);
  const d3Text = await page.getByRole('dialog').innerText().catch(() => '');
  await page.screenshot({ path: `${OUT}/03-action3-desc.png`, fullPage: true });
  const refs = /233-1/.test(d3Text) && /2,75\s*GWh/.test(d3Text) && /ISO 50001/.test(d3Text);
  rec(6, 'Description action 3 — L. 233-1 + 2,75 GWh + ISO 50001', refs,
      `233-1=${/233-1/.test(d3Text)} 2,75GWh=${/2,75\s*GWh/.test(d3Text)} ISO50001=${/ISO 50001/.test(d3Text)}`);
} catch (e) {
  console.log('ERREUR walkthrough :', e.message);
} finally {
  const ok = results.filter(Boolean).length;
  console.log(`\n═══ Phase 9 walkthrough : ${ok}/6 ═══`);
  await browser.close();
  process.exit(ok === 6 ? 0 : 1);
}
