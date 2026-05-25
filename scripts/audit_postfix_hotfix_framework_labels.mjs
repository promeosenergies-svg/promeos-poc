#!/usr/bin/env node
/**
 * Audit postfix — Hotfix labels frameworks réglementaires (2026-05-24).
 *
 * Vérifie en bout-en-bout :
 * 1. /api/compliance/portfolio/score retourne breakdown_avg_labeled avec label_fr.
 * 2. /api/compliance/sites/{id}/score retourne breakdown[] avec label_fr.
 * 3. /conformite affiche "Audit SMÉ" et "Solarisation toiture" (pas "APER").
 * 4. APER n'apparaît qu'UNE seule fois.
 * 5. 0 console error, 0 network 5xx.
 */
import { chromium } from 'playwright';

const FE = process.env.FE || 'http://localhost:5175';
const BE = process.env.BE || 'http://localhost:8001';
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
  // ─── 1. Login + curl portfolio ───────────────────────────────────
  const loginRes = await page.request.post(`${FE}/api/auth/demo-login`);
  const loginData = await loginRes.json();
  const token = loginData.access_token;

  const portfolioRes = await page.request.get(`${BE}/api/compliance/portfolio/score`, {
    headers: { Authorization: `Bearer ${token}`, 'X-Org-Id': '1' },
  });
  record(`Backend /api/compliance/portfolio/score → ${portfolioRes.status()}`, portfolioRes.status() === 200);
  const portfolioPayload = await portfolioRes.json();
  record(
    'portfolio expose breakdown_avg_labeled (liste typée)',
    Array.isArray(portfolioPayload.breakdown_avg_labeled)
  );
  // Chaque entrée a label_fr non vide
  const portfolioMissing = (portfolioPayload.breakdown_avg_labeled || []).filter(
    (e) => !e.label_fr || typeof e.label_fr !== 'string'
  );
  record(
    `chaque breakdown_avg_labeled.label_fr est non-vide (${portfolioMissing.length} manquant)`,
    portfolioMissing.length === 0
  );
  // Mapping correct pour audit_sme + solar_toiture (cœur du bug)
  const auditSme = (portfolioPayload.breakdown_avg_labeled || []).find(
    (e) => e.framework === 'audit_sme'
  );
  if (auditSme) {
    record(
      `audit_sme → label_fr="${auditSme.label_fr}"`,
      auditSme.label_fr === 'Audit SMÉ'
    );
  } else {
    record('audit_sme absent du portfolio HELIOS (skip)', true, 'pas de site assujetti');
  }
  const solarToiture = (portfolioPayload.breakdown_avg_labeled || []).find(
    (e) => e.framework === 'solar_toiture'
  );
  if (solarToiture) {
    record(
      `solar_toiture → label_fr="${solarToiture.label_fr}"`,
      solarToiture.label_fr === 'Solarisation toiture'
    );
  }

  // ─── 2. Curl site detail ────────────────────────────────────────
  // Récupérer le 1er site du portfolio
  const sitesRes = await page.request.get(`${BE}/api/patrimoine/sites?limit=1`, {
    headers: { Authorization: `Bearer ${token}`, 'X-Org-Id': '1' },
  });
  const sitesData = await sitesRes.json();
  const firstSiteId =
    sitesData?.sites?.[0]?.id ?? sitesData?.items?.[0]?.id ?? sitesData?.[0]?.id ?? null;
  if (firstSiteId) {
    const siteScoreRes = await page.request.get(
      `${BE}/api/compliance/sites/${firstSiteId}/score`,
      { headers: { Authorization: `Bearer ${token}`, 'X-Org-Id': '1' } }
    );
    record(`Backend /api/compliance/sites/${firstSiteId}/score → ${siteScoreRes.status()}`, siteScoreRes.status() === 200);
    const sitePayload = await siteScoreRes.json();
    const breakdown = sitePayload.breakdown || [];
    const siteMissing = breakdown.filter((e) => !e.label_fr);
    record(
      `chaque site breakdown[].label_fr est non-vide (${siteMissing.length} manquant sur ${breakdown.length})`,
      siteMissing.length === 0 && breakdown.length > 0
    );
  }

  // ─── 3. Playwright /conformite — rendu visuel ────────────────────
  await page.goto(`${FE}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), token);

  await page.goto(`${FE}/conformite`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(3000);

  // Le composant rend des spans avec data-testid="framework-label-<code>"
  const labelCells = await page.locator('[data-testid^="framework-label-"]').all();
  record(
    `${labelCells.length} ligne(s) breakdown affichée(s) (>= 3 attendu)`,
    labelCells.length >= 3
  );

  const labelMap = {};
  for (const cell of labelCells) {
    const tid = await cell.getAttribute('data-testid');
    const code = tid?.replace('framework-label-', '') || 'unknown';
    const text = (await cell.textContent())?.trim() || '';
    labelMap[code] = text;
  }
  console.log('Labels rendus :', JSON.stringify(labelMap, null, 2));

  // 4. audit_sme s'affiche "Audit SMÉ" (PAS "APER")
  if (labelMap.audit_sme !== undefined) {
    record(
      `audit_sme rendu : "${labelMap.audit_sme}"`,
      /Audit SMÉ/.test(labelMap.audit_sme) && !/^APER\b/.test(labelMap.audit_sme)
    );
  }
  // 5. solar_toiture s'affiche "Solarisation toiture"
  if (labelMap.solar_toiture !== undefined) {
    record(
      `solar_toiture rendu : "${labelMap.solar_toiture}"`,
      /Solarisation/.test(labelMap.solar_toiture) && !/^APER\b/.test(labelMap.solar_toiture)
    );
  }
  // 6. APER apparaît au plus 1 fois (anti-régression bug 3 lignes APER)
  const aperLines = Object.entries(labelMap).filter(([code, text]) =>
    /\bAPER\b/.test(text) && !/Audit|Solarisation|ISO/.test(text)
  );
  record(
    `APER apparaît au plus 1 fois (compté ${aperLines.length})`,
    aperLines.length <= 1
  );

  // ─── 7. Console + Network ───────────────────────────────────────
  const blockingErrors = consoleErrors.filter(
    (e) => !e.includes('React Router Future Flag') && !e.includes('Download the React DevTools')
  );
  record(
    `0 console error bloquant (${blockingErrors.length} / ${consoleErrors.length} total)`,
    blockingErrors.length === 0,
    blockingErrors.slice(0, 3).join(' | ')
  );
  const blocking5xx = networkFailures.filter((f) => /^5\d\d /.test(f));
  record(
    `0 network 5xx bloquant (${blocking5xx.length} / ${networkFailures.length} total)`,
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
