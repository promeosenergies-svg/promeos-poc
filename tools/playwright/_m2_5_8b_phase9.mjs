/** M2-5.8.B Phase 9 — smoke navigateur post-impl. Scratch, non commité. */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://127.0.0.1:5176';
const OUT = 'tools/playwright/captures/m2_5_8b_phase9';
mkdirSync(OUT, { recursive: true });

const results = [];
function rec(n, label, ok, note) {
  results.push(ok);
  console.log(`  ${ok ? 'OK' : 'KO'}  [${n}] ${label}${note ? ' — ' + note : ''}`);
}

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

  // 1 — colonnes Priorité + Type dans l'en-tête
  const headers = await page.locator('thead th').allInnerTexts();
  const hasPrio = headers.some((h) => /priorité/i.test(h));
  const hasType = headers.some((h) => /type/i.test(h));
  await page.screenshot({ path: `${OUT}/01-table.png`, fullPage: true });
  rec(1, 'En-tête : colonnes Priorité + Type', hasPrio && hasType, `headers=[${headers.join(', ')}]`);

  // 2 — badges de priorité visibles
  const bodyText = await page.locator('tbody').innerText();
  const prioBadge = /(Critique|Élevée|Standard|Faible)/.test(bodyText);
  rec(2, 'Badges de priorité affichés', prioBadge, `détecté=${prioBadge}`);

  // 3 — kind affiché en FR (pas brut)
  const kindFR = /(Anomalie|Échéance|Décision|Recommandation|Action)/.test(bodyText);
  const kindRaw = /\b(anomaly|deadline|decision|recommendation)\b/.test(bodyText);
  rec(3, 'Kind affiché en FR, pas brut', kindFR && !kindRaw, `FR=${kindFR} brut=${kindRaw}`);

  // 4 — ligne focusable au clavier + Enter ouvre le drawer
  const firstRow = page.locator('tbody tr').first();
  await firstRow.focus();
  const focusInfo = await page.evaluate(() => {
    const el = document.activeElement;
    return {
      tag: el?.tagName,
      role: el?.getAttribute('role'),
      tabindex: el?.getAttribute('tabindex'),
    };
  });
  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);
  const dialogOpen = await page.getByRole('dialog').isVisible().catch(() => false);
  await page.screenshot({ path: `${OUT}/02-keyboard-drawer.png`, fullPage: true });
  rec(
    4,
    'Ligne focusable clavier + Enter ouvre le drawer',
    focusInfo.tag === 'TR' && focusInfo.tabindex === '0' && dialogOpen,
    `focus=${focusInfo.tag}[role=${focusInfo.role},tabindex=${focusInfo.tabindex}] dialog=${dialogOpen}`
  );
} catch (e) {
  console.log('ERREUR :', e.message);
} finally {
  const ok = results.filter(Boolean).length;
  console.log(`\n═══ Phase 9 smoke post-impl : ${ok}/4 ═══`);
  await browser.close();
  process.exit(ok === 4 ? 0 : 1);
}
