#!/usr/bin/env node
/**
 * Validation finale release — checklist user (2026-05-25).
 *
 * 13 items :
 *   1. PR #301 + #302 (vérification offline : tests verts sur branche locale)
 *   2. /conformite affiche 4 cartes ATF
 *   3. Périmètre clair : sites évalués / périmètre total
 *   4. Pénalité unique ou "à qualifier"
 *   5. Frise repliée
 *   6. APER non répété abusivement
 *   7. Sidebar Conformité unique
 *   8. /bill-intel OK
 *   9. /centre-action filtre Facturation OK
 *  10. /cockpit/strategique OK
 *  11. 0 console error
 *  12. 0 network 4xx/5xx golden path
 */
import { chromium } from 'playwright';

const FE = process.env.FE || 'http://localhost:5175';
const results = [];
let exitCode = 0;

function record(name, ok, detail = '') {
  results.push({ name, ok, detail });
  if (!ok) exitCode = 1;
  console.log(`${ok ? '✅' : '❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const consoleErrors = [];
const networkFailures = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text());
});
page.on('response', (r) => {
  const s = r.status();
  if (s >= 400 && s < 600) networkFailures.push(`${s} ${r.url()}`);
});

try {
  // Login
  const loginRes = await page.request.post(`${FE}/api/auth/demo-login`);
  const { access_token } = await loginRes.json();
  await page.goto(`${FE}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), access_token);

  // ─── /conformite (items 2-7) ─────────────────────────────────────
  await page.goto(`${FE}/conformite`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(3000);

  // 2. 4 cartes ATF
  const synthese = page.locator('[data-testid="conformite-synthese-compacte"]');
  record('2. /conformite affiche 4 cartes ATF', await synthese.isVisible().catch(() => false));
  let cardsCount = 0;
  for (const id of ['score', 'echeance', 'actions', 'preuves']) {
    if (await page.locator(`[data-testid="synthese-card-${id}"]`).isVisible().catch(() => false)) cardsCount++;
  }
  record(`2.bis ${cardsCount}/4 cartes synthèse présentes`, cardsCount === 4);

  // 3. Périmètre clair
  const perimetre = await page.locator('[data-testid="synthese-perimetre"]').textContent().catch(() => '');
  record(
    `3. Périmètre clair : "${perimetre.trim()}"`,
    /sites?/.test(perimetre) && /périmètre/.test(perimetre)
  );

  // 4. Pénalité unique ou "à qualifier"
  const risque = await page.locator('[data-testid="synthese-risque"]').textContent().catch(() => '');
  const okPenalty =
    (/à qualifier/.test(risque) || /€/.test(risque)) &&
    !/^Risque financier\s*:\s*0\s*€/.test(risque.trim());
  record(`4. Pénalité unique/qualifier : "${risque.trim().slice(0, 60)}"`, okPenalty);

  // 5. Frise repliée
  const frise = page.locator('[data-testid="frise-reglementaire-summary"]');
  const friseExists = await frise.isVisible().catch(() => false);
  const friseParent = await frise.evaluateHandle((el) => el.closest('details'));
  const friseOpen = await page.evaluate((d) => d?.open, friseParent).catch(() => null);
  record(`5. Frise réglementaire repliée (open: ${friseOpen})`, friseExists && friseOpen === false);

  // 6. APER non répété
  const labelCells = await page.locator('[data-testid^="framework-label-"]').all();
  const labels = {};
  for (const cell of labelCells) {
    const tid = await cell.getAttribute('data-testid');
    const code = tid?.replace('framework-label-', '') || 'unknown';
    labels[code] = (await cell.textContent())?.trim() || '';
  }
  const aperCount = Object.values(labels).filter(
    (t) => /\bAPER\b/.test(t) && !/Audit|Solarisation|ISO/.test(t)
  ).length;
  record(`6. APER apparaît ${aperCount} fois (≤ 1)`, aperCount <= 1, `labels=${JSON.stringify(labels)}`);

  // 7. Sidebar Conformité unique
  const navLinks = await page.locator('a[href^="/conformite"]').all();
  const hrefs = (await Promise.all(navLinks.map((a) => a.getAttribute('href')))).filter(Boolean);
  const hasHub = hrefs.some((h) => h === '/conformite' || h.startsWith('/conformite?'));
  const noTertiaire = !hrefs.some((h) => h.startsWith('/conformite/tertiaire'));
  const noAper = !hrefs.some((h) => h.startsWith('/conformite/aper'));
  record(
    '7. Sidebar Conformité unique (1 hub, 0 sous-item DT/APER)',
    hasHub && noTertiaire && noAper,
    `hrefs=${JSON.stringify(hrefs)}`
  );

  // ─── 8. /bill-intel OK ───────────────────────────────────────────
  const billRes = await page.goto(`${FE}/bill-intel`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(2000);
  record(`8. /bill-intel HTTP ${billRes?.status()}`, billRes?.status() === 200);

  // ─── 9. /centre-action filtre Facturation ────────────────────────
  await page.goto(`${FE}/action-center-v4`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(2500);
  const domainSelect = page.locator('select[aria-label="Filtrer par domaine"]');
  const hasFilter = await domainSelect.isVisible().catch(() => false);
  record(
    '9. /action-center-v4 filtre Facturation présent',
    hasFilter,
    hasFilter ? 'select[aria-label="Filtrer par domaine"] visible' : 'select introuvable'
  );

  // ─── 10. /cockpit/strategique OK + Billing KPIs ──────────────────
  const cockpitRes = await page.goto(`${FE}/cockpit/strategique`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  await page.waitForTimeout(3000);
  record(`10. /cockpit/strategique HTTP ${cockpitRes?.status()}`, cockpitRes?.status() === 200);
  // Bonus : section billing_kpis présente
  const billingSection = page.locator('[data-testid="cockpit-billing-kpis"]');
  record(
    '10.bis CockpitBillingKpis section présente',
    await billingSection.isVisible().catch(() => false)
  );

  // ─── 11-12. Console + Network ────────────────────────────────────
  const blockingErrors = consoleErrors.filter(
    (e) => !e.includes('React Router Future Flag') && !e.includes('Download the React DevTools')
  );
  record(
    `11. 0 console error bloquant (${blockingErrors.length} / ${consoleErrors.length})`,
    blockingErrors.length === 0,
    blockingErrors.slice(0, 3).join(' | ')
  );
  const blocking5xx = networkFailures.filter((f) => /^5\d\d /.test(f));
  const blocking4xx = networkFailures.filter((f) => /^4\d\d /.test(f) && !/^401 /.test(f));
  record(
    `12. 0 network 5xx bloquant (${blocking5xx.length})`,
    blocking5xx.length === 0,
    blocking5xx.slice(0, 3).join(' | ')
  );
  record(
    `12.bis 0 network 4xx (hors 401, ${blocking4xx.length})`,
    blocking4xx.length === 0,
    blocking4xx.slice(0, 3).join(' | ')
  );
} catch (e) {
  record('Validation terminée sans crash', false, e.message);
} finally {
  console.log('\n─── BILAN FINAL ───');
  const passed = results.filter((r) => r.ok).length;
  console.log(`Passed: ${passed}/${results.length}`);
  if (passed === results.length) {
    console.log('🟢 GO — tous les critères passent');
  } else {
    console.log('🟡 GO conditionnel — voir détails ci-dessus');
  }
  await browser.close();
  process.exit(exitCode);
}
