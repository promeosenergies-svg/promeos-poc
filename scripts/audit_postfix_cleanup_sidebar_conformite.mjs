#!/usr/bin/env node
/**
 * Audit postfix — Cleanup sidebar Conformité (2026-05-24).
 *
 * Vérifie via Playwright (bare API, pas @playwright/test) :
 * 1. Sidebar n'expose plus que /conformite (pas de sous-items DT/APER).
 * 2. /conformite affiche la barre de chips réglementaires (5 chips).
 * 3. Cliquer chip DT met à jour ?regulation=dt + aria-selected=true.
 * 4. Routes /conformite/tertiaire et /conformite/aper restent
 *    accessibles en deep-link (200 OK + 0 erreur 5xx bloquante).
 * 5. 0 console error pendant la navigation golden path.
 *
 * Lancement :
 *   FE=http://localhost:5175 node scripts/audit_postfix_cleanup_sidebar_conformite.mjs
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

async function loginDemo() {
  // Approche directe : POST /api/auth/demo-login → injecter le token dans
  // localStorage, puis recharger. Évite l'animation/render de la LoginPage.
  const res = await page.request.post(`${FE}/api/auth/demo-login`);
  if (!res.ok()) throw new Error(`demo-login HTTP ${res.status()}`);
  const data = await res.json();
  await page.goto(`${FE}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((token) => {
    localStorage.setItem('promeos_token', token);
  }, data.access_token);
}

try {
  await loginDemo();

  // ─── 1. Sidebar ne montre que /conformite ──────────────────────────
  await page.goto(`${FE}/conformite`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(1500); // attente hydratation + sidebar render
  const navLinks = await page.locator('a[href^="/conformite"]').all();
  const hrefs = (await Promise.all(navLinks.map((a) => a.getAttribute('href')))).filter(Boolean);
  record(
    'Sidebar contient au moins un lien vers /conformite (hub)',
    hrefs.some((h) => h === '/conformite' || h.startsWith('/conformite?'))
  );
  record(
    'Sidebar n\'expose plus /conformite/tertiaire',
    !hrefs.some((h) => h.startsWith('/conformite/tertiaire')),
    `hrefs=${JSON.stringify(hrefs)}`
  );
  record(
    'Sidebar n\'expose plus /conformite/aper',
    !hrefs.some((h) => h.startsWith('/conformite/aper'))
  );

  // ─── 2. Chips réglementaires présentes ─────────────────────────────
  await page.waitForSelector('[data-testid="regulation-chips-bar"]', { timeout: 15_000 });
  for (const k of ['all', 'dt', 'bacs', 'aper', 'audit-sme']) {
    const el = page.locator(`[data-testid="regulation-chip-${k}"]`);
    record(`Chip regulation-chip-${k} visible`, await el.isVisible());
  }
  const barText = (await page.locator('[data-testid="regulation-chips-bar"]').textContent()) || '';
  for (const label of [
    "Vue d'ensemble",
    'Décret Tertiaire / OPERAT',
    'BACS',
    'APER',
    'SMÉ / BEGES',
  ]) {
    record(`Label « ${label} » présent dans la barre`, barText.includes(label));
  }

  // ─── 3. Clic chip DT → ?regulation=dt + aria-selected ──────────────
  await page.locator('[data-testid="regulation-chip-dt"]').click();
  await page.waitForFunction(() => /[?&]regulation=dt/.test(location.href), { timeout: 5000 });
  const dtSelected = await page
    .locator('[data-testid="regulation-chip-dt"]')
    .getAttribute('aria-selected');
  record('Chip DT cliquée → aria-selected=true', dtSelected === 'true');
  record('URL contient ?regulation=dt', /[?&]regulation=dt/.test(page.url()));

  // Retour Vue d'ensemble → param retiré
  await page.locator('[data-testid="regulation-chip-all"]').click();
  await page.waitForFunction(() => !/[?&]regulation=/.test(location.href), { timeout: 5000 });
  record('Chip Vue d\'ensemble retire le ?regulation= du URL', !/[?&]regulation=/.test(page.url()));

  // ─── 4. Deep-links /conformite/tertiaire et /conformite/aper ───────
  const tert = await page.goto(`${FE}/conformite/tertiaire`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  record(`/conformite/tertiaire deep-link → ${tert?.status()}`, tert?.status() === 200);

  const aper = await page.goto(`${FE}/conformite/aper`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  record(`/conformite/aper deep-link → ${aper?.status()}`, aper?.status() === 200);

  // ─── 5. Aucun menu fantôme ACC / PMO / Partner Hub ─────────────────
  await page.goto(`${FE}/cockpit`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  const cockpitText = (await page.locator('body').textContent()) || '';
  record('Pas de menu Partner Hub', !/\bPartner Hub\b/i.test(cockpitText));
  record('Pas de menu PMO', !/\bPMO\b/.test(cockpitText));
} catch (e) {
  record('Audit terminé sans crash', false, e.message);
} finally {
  // ─── 6. Console errors / network 5xx ─────────────────────────────
  record(
    `0 console error (collected ${consoleErrors.length})`,
    consoleErrors.length === 0,
    consoleErrors.slice(0, 3).join(' | ')
  );
  const blocking5xx = networkFailures.filter((f) => /^5\d\d /.test(f));
  record(
    `0 network 5xx bloquant (collected ${blocking5xx.length})`,
    blocking5xx.length === 0,
    blocking5xx.slice(0, 3).join(' | ')
  );

  console.log('\n─── BILAN ───');
  console.log(`Passed: ${results.filter((r) => r.ok).length}/${results.length}`);
  await browser.close();
  process.exit(exitCode);
}
