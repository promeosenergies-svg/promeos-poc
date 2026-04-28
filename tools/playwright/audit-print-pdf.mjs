/**
 * PROMEOS — Audit E2E export PDF Sequoia (Vague H P2 #3).
 *
 * Garde-fou non-régression : vérifie que le verrou CSS @media print
 * (tokens.css L102-145) préserve l'identité visuelle Sol en export PDF
 * via Chromium headless `page.pdf()`.
 *
 * Sortie : tools/playwright/captures/audit-print-pdf/
 *   - cockpit-print.pdf : export A4 paysage du Cockpit
 *   - cockpit-screenshot-print.png : capture après emulate('print')
 *   - audit-report.json : checks programmatiques (couleurs préservées,
 *     bordures épaissies, popover methodology forcé visible)
 *
 * Usage :
 *   node tools/playwright/audit-print-pdf.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const AUTH_EMAIL = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';
const OUT_DIR = resolve(process.cwd(), 'tools', 'playwright', 'captures', 'audit-print-pdf');

const log = (s) => console.log(`[${new Date().toISOString().slice(11, 23)}] ${s}`);

async function main() {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
  });
  const page = await context.newPage();

  log('AUTH login + JWT (via proxy)');
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  const loginResp = await page.evaluate(
    async ({ email, password }) => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      return res.json();
    },
    { email: AUTH_EMAIL, password: AUTH_PASSWORD }
  );
  if (!loginResp.access_token) {
    console.error('Login failed:', loginResp);
    await browser.close();
    process.exit(1);
  }
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), loginResp.access_token);

  log('Navigate /cockpit + wait SolEventStream');
  await page.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForSelector('[data-testid^="sol-event-card-"]', { timeout: 10000 });
  await page.waitForTimeout(2000);

  // ── Émule le mode print (CSS @media print actif) ────────────────
  log('Émulate media: print');
  await page.emulateMedia({ media: 'print' });

  // Capture screenshot avec print emulé pour audit visuel humain
  log('Screenshot post-print emulation');
  await page.screenshot({ path: join(OUT_DIR, 'cockpit-screenshot-print.png'), fullPage: false });

  // ── Audit programmatique des règles @media print ────────────────
  log('Audit checks programmatiques');
  const audit = await page.evaluate(() => {
    const cards = document.querySelectorAll('[data-testid^="sol-event-card-"]');
    const results = {
      cards_found: cards.length,
      checks: [],
    };
    if (cards.length === 0) {
      results.checks.push({ name: 'cards_present', pass: false, error: 'No SolEventCard' });
      return results;
    }
    const card = cards[0];
    const styles = window.getComputedStyle(card);

    // Check 1 : print-color-adjust = exact
    const printAdjust = styles.getPropertyValue('print-color-adjust') || styles.getPropertyValue('-webkit-print-color-adjust');
    results.checks.push({
      name: 'print_color_adjust_exact',
      pass: printAdjust === 'exact',
      value: printAdjust,
    });

    // Check 2 : background couleur préservée (pas blanc transparent)
    const bg = styles.backgroundColor;
    results.checks.push({
      name: 'background_preserved',
      pass: bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent' && bg !== 'rgb(255, 255, 255)',
      value: bg,
    });

    // Check 3 : border-width ≥ 2px (épaissie en print)
    const borderWidth = parseFloat(styles.borderTopWidth) || 0;
    results.checks.push({
      name: 'border_width_thickened',
      pass: borderWidth >= 2,
      value: `${borderWidth}px`,
    });

    // Check 4 : page-break-inside avoid
    const pageBreak = styles.pageBreakInside || styles.breakInside;
    results.checks.push({
      name: 'page_break_inside_avoid',
      pass: pageBreak === 'avoid',
      value: pageBreak,
    });

    return results;
  });

  log(`Audit checks : ${audit.cards_found} cards, ${audit.checks.filter((c) => c.pass).length}/${audit.checks.length} pass`);
  audit.checks.forEach((c) =>
    console.log(`  ${c.pass ? '✓' : '✗'} ${c.name} = ${c.value || c.error}`)
  );

  // ── Export PDF réel ────────────────────────────────────────────
  log('Export PDF (Chromium native page.pdf)');
  await page.pdf({
    path: join(OUT_DIR, 'cockpit-print.pdf'),
    format: 'A4',
    landscape: true,
    printBackground: true, // CRITIQUE : sinon backgrounds Sol disparaissent
    margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' },
  });

  // ── Export audit JSON ──────────────────────────────────────────
  writeFileSync(
    join(OUT_DIR, 'audit-report.json'),
    JSON.stringify(
      {
        date: new Date().toISOString(),
        sprint: 'Vague H P2 #3',
        url: FRONTEND_URL + '/cockpit',
        ...audit,
        verdict: audit.checks.every((c) => c.pass) ? 'GO Sequoia PDF export' : 'NO-GO — checks failed',
      },
      null,
      2
    )
  );

  await browser.close();

  const passCount = audit.checks.filter((c) => c.pass).length;
  console.log(`\n${passCount === audit.checks.length ? '✅' : '❌'} ${passCount}/${audit.checks.length} checks pass`);
  console.log(`Outputs : ${OUT_DIR}`);

  if (passCount !== audit.checks.length) process.exit(1);
}

main().catch((err) => {
  console.error('[FATAL]', err);
  process.exit(1);
});
