#!/usr/bin/env node
/**
 * Audit postfix — Conformité P2-A simplification visuelle (2026-05-25).
 *
 * Vérifie :
 * 1. /conformite charge OK (login démo + 200).
 * 2. ConformiteSyntheseCompacte rend les 4 cartes ATF (Score · Échéance ·
 *    Actions · Preuves manquantes) avec testids stables.
 * 3. Le libellé périmètre « X sites évalués sur Y » est rendu si divergent.
 * 4. Le risque financier est « à qualifier » OU un montant formaté (jamais "0 €").
 * 5. La frise réglementaire est repliée par défaut (<details> fermé).
 * 6. Le briefing éditorial est replié par défaut.
 * 7. 0 RiskBadge dupliqué dans le rendu de /conformite.
 * 8. APER apparaît une seule fois (régression hotfix #301).
 * 9. 0 console error bloquant.
 * 10. 0 network 5xx bloquant.
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
  // Login + naviguer
  const loginRes = await page.request.post(`${FE}/api/auth/demo-login`);
  const { access_token } = await loginRes.json();
  await page.goto(`${FE}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), access_token);

  const resp = await page.goto(`${FE}/conformite`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  await page.waitForTimeout(3000);
  record(`1. /conformite HTTP ${resp?.status()}`, resp?.status() === 200);

  // 2. Synthèse compacte
  const synthese = page.locator('[data-testid="conformite-synthese-compacte"]');
  const syntheseVisible = await synthese.isVisible().catch(() => false);
  record('2. Synthèse compacte ATF visible (above-the-fold)', syntheseVisible);

  for (const id of ['score', 'echeance', 'actions', 'preuves']) {
    const card = page.locator(`[data-testid="synthese-card-${id}"]`);
    record(
      `2.${id} Carte ${id} rendue`,
      await card.isVisible().catch(() => false)
    );
  }

  // 3. Libellé périmètre
  const perimetre = await page.locator('[data-testid="synthese-perimetre"]').textContent().catch(() => '');
  record(
    `3. Libellé périmètre clair : "${perimetre.trim()}"`,
    /sites?/.test(perimetre) && /périmètre/.test(perimetre)
  );

  // 4. Risque financier
  const risque = await page.locator('[data-testid="synthese-risque"]').textContent().catch(() => '');
  record(
    `4. Risque financier rendu : "${risque.trim().slice(0, 80)}"`,
    /à qualifier|€/.test(risque) && !/^Risque financier\s*:\s*0\s*€/.test(risque.trim())
  );

  // 5. Frise réglementaire repliée par défaut
  const frise = page.locator('[data-testid="frise-reglementaire-summary"]');
  const friseExists = await frise.isVisible().catch(() => false);
  const friseParent = await frise.evaluateHandle((el) => el.closest('details'));
  const friseOpen = await page.evaluate((d) => d?.open, friseParent).catch(() => null);
  record(
    `5. Frise réglementaire repliée par défaut (visible: ${friseExists}, open: ${friseOpen})`,
    friseExists && friseOpen === false
  );

  // 6. Briefing éditorial dans <details> replié
  const briefingDetails = await page
    .locator('details', { hasText: 'Contexte éditorial' })
    .first();
  const briefingOpen = await briefingDetails.evaluate((el) => el.open).catch(() => null);
  record(
    `6. Briefing éditorial replié par défaut (open: ${briefingOpen})`,
    briefingOpen === false
  );

  // 7. Pas de RiskBadge dupliqué
  const riskBadgeOld = page.locator('[data-testid="conformite-risk-badge"]');
  const oldBadgeVisible = await riskBadgeOld.isVisible().catch(() => false);
  record('7. RiskBadge dupliqué retiré (data-testid="conformite-risk-badge" absent)', !oldBadgeVisible);

  // 8. APER une seule fois dans les labels frameworks
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
  record(
    `8. APER apparaît ${aperCount} fois (max 1 attendu)`,
    aperCount <= 1,
    `labels=${JSON.stringify(labels)}`
  );

  // 9-10. Console + Network
  const blockingErrors = consoleErrors.filter(
    (e) => !e.includes('React Router Future Flag') && !e.includes('Download the React DevTools')
  );
  record(
    `9. 0 console error bloquant (${blockingErrors.length} / ${consoleErrors.length} total)`,
    blockingErrors.length === 0,
    blockingErrors.slice(0, 3).join(' | ')
  );
  const blocking5xx = networkFailures.filter((f) => /^5\d\d /.test(f));
  record(
    `10. 0 network 5xx bloquant (${blocking5xx.length} / ${networkFailures.length} total)`,
    blocking5xx.length === 0,
    blocking5xx.slice(0, 3).join(' | ')
  );
} catch (e) {
  record('Audit terminé sans crash', false, e.message);
} finally {
  console.log('\n─── BILAN ───');
  console.log(`Passed: ${results.filter((r) => r.ok).length}/${results.length}`);
  await browser.close();
  process.exit(exitCode);
}
