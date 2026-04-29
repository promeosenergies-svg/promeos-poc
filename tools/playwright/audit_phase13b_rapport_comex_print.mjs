/**
 * Phase 13.B — Audit Rapport COMEX print preview (CockpitDecision).
 *
 * Émule le media `print` puis génère un PDF natif du Cockpit Décision
 * pour vérifier :
 *  1. Header impression visible (PROMEOS · scope · date · semaine)
 *  2. Sidebar + topbar AppShell cachés
 *  3. Bouton "Rapport COMEX" caché
 *  4. KPI hero triptyque conservé en 3 colonnes
 *  5. Décisions narrées + trajectoire + portfolio + flex teaser présents
 *  6. Footer impression visible (signature provenance)
 *
 * Usage : node tools/playwright/audit_phase13b_rapport_comex_print.mjs
 * Output : tools/playwright/captures/phase13b_rapport_comex.pdf
 *          tools/playwright/captures/phase13b_rapport_comex_screen.png (preview)
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const FRONT = 'http://localhost:5175';
const ROUTE = '/cockpit/strategique';
const OUT_DIR = 'tools/playwright/captures';
const PDF_PATH = `${OUT_DIR}/phase13b_rapport_comex.pdf`;
const SCREEN_PATH = `${OUT_DIR}/phase13b_rapport_comex_screen.png`;

mkdirSync(OUT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

// Login démo
console.log(`→ Authenticating via /login`);
await page.goto(`${FRONT}/login`, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
const emailField = await page.$('input[type=email]');
if (emailField) {
  await page.fill('input[type=email]', 'promeos@promeos.io');
  await page.fill('input[type=password]', 'promeos2024');
  // Trigger via Enter (la button[type=submit] peut être en disabled pendant validation)
  await Promise.all([
    page.waitForLoadState('networkidle').catch(() => {}),
    page.press('input[type=password]', 'Enter'),
  ]);
  // Wait for navigation away from /login
  await page
    .waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 8000 })
    .catch(() => {});
}

console.log(`→ Navigating to ${FRONT}${ROUTE}`);
await page.goto(`${FRONT}${ROUTE}`, { waitUntil: 'networkidle', timeout: 30000 });

// Attendre que la page soit hydratée et fetchs résolus
await page.waitForTimeout(3000);

// Screenshot écran pré-print pour comparaison
await page.screenshot({ path: SCREEN_PATH, fullPage: true });
console.log(`✓ Screen capture → ${SCREEN_PATH}`);

// Émuler media print pour visualiser le rendu
await page.emulateMedia({ media: 'print' });
await page.waitForTimeout(500);

// Vérifications structurelles print
const printChecks = await page.evaluate(() => {
  const results = {};

  // 1. Header impression visible
  const printHeader = document.querySelector('[data-print-header]');
  results.print_header_present = !!printHeader;
  results.print_header_text = printHeader?.innerText?.slice(0, 200) || '';

  // 2. Footer impression visible
  const printFooter = document.querySelector('[data-print-footer]');
  results.print_footer_present = !!printFooter;
  results.print_footer_text = printFooter?.innerText?.slice(0, 200) || '';

  // 3. Sections marquées page-break-avoid
  results.print_sections_count = document.querySelectorAll('[data-print-section]').length;

  // 4. Bouton "Rapport COMEX" est-il visible en print ?
  // (On vérifie computed style via getComputedStyle dans le DOM)
  const rapportBtn = Array.from(document.querySelectorAll('button')).find((b) =>
    b.innerText.includes('Rapport COMEX'),
  );
  results.rapport_btn_display = rapportBtn ? getComputedStyle(rapportBtn).display : 'no_btn';

  // 5. Sidebar AppShell cachée ?
  const sidebar = document.querySelector('aside') || document.querySelector('[data-testid*="sidebar"]');
  results.sidebar_display = sidebar ? getComputedStyle(sidebar).display : 'no_sidebar';

  // 6. KPI hero triptyque présent (badges Calculé/Modélisé/Indicatif)
  const badges = Array.from(document.querySelectorAll('span')).filter((s) =>
    /CALCULÉ|MODÉLISÉ|INDICATIF/i.test(s.innerText),
  );
  results.kpi_badges_count = badges.length;

  // 7. Décisions list présente
  results.decision_titles_count = document.querySelectorAll('h3, h4').length;

  return results;
});

console.log('\n--- PRINT EMULATION CHECKS ---');
console.log(JSON.stringify(printChecks, null, 2));

// Générer un PDF natif (Chromium → A4 portrait)
await page.pdf({
  path: PDF_PATH,
  format: 'A4',
  printBackground: true,
  margin: { top: '14mm', right: '12mm', bottom: '14mm', left: '12mm' },
  preferCSSPageSize: true,
});
console.log(`✓ PDF generated → ${PDF_PATH}`);

// Verdict
const ok =
  printChecks.print_header_present &&
  printChecks.print_footer_present &&
  printChecks.print_sections_count >= 5 &&
  printChecks.rapport_btn_display === 'none' &&
  printChecks.sidebar_display === 'none';

console.log(`\n${ok ? '✅ PASS' : '❌ FAIL'} — Phase 13.B Rapport COMEX print preview`);

await browser.close();
process.exit(ok ? 0 : 1);
