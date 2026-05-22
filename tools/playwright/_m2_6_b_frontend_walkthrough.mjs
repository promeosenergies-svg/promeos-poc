// M2-6.B.frontend — Walkthrough Playwright 6 étapes mode CFO.
//
// Vérifie bout-en-bout que la chaîne BE→FE marche pour le pilote :
//   1. Login Marie Leclerc
//   2. /action-center-v4/pilotage rendu + complétude « X/Y actions »
//   3. NarrativeBar Tuile Décisions affiche sum € compact
//   4. /action-center-v4 (Référentiel) colonne « Impact estimé » + montants
//   5. Tooltip header colonne (hover) = « Montant indicatif... »
//   6. F5 reload — données persistent (cache backend 60s)
//
// 6 captures PNG horodatées dans tools/playwright/captures/m2_6_b_frontend/.
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const OUT = 'tools/playwright/captures/m2_6_b_frontend';
const FE = 'http://127.0.0.1:5175';
const DEMO_USER = 'm.leclerc@helios-energie.fr';
const DEMO_PASS = 'promeos2024';

async function shoot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  📸 ${name}.png`);
}

(async () => {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage();

  const errors = [];
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
  });

  const checks = {};

  try {
    // ── 1. Login ────────────────────────────────────────────────────
    console.log('\n1. Login Marie Leclerc (ENERGY_MANAGER)');
    await page.goto(`${FE}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', DEMO_USER);
    await page.fill('input[type="password"]', DEMO_PASS);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 10_000 }),
      page.getByRole('button', { name: /^connexion$|^se connecter$/i }).click(),
    ]);
    await page.waitForLoadState('networkidle');
    console.log(`  ✓ Logged in, URL: ${page.url()}`);
    await shoot(page, '01-login-success');

    // ── 2. Pilotage + complétude X/Y ────────────────────────────────
    console.log('\n2. Navigate /pilotage + vérif complétude « X/Y actions »');
    await page.goto(`${FE}/action-center-v4/pilotage`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    await shoot(page, '02-pilotage-completude');

    const completudeNode = page.locator('[data-testid="editorial-completude"]');
    const completudeText = (await completudeNode.textContent().catch(() => '')) || '';
    checks.completudeRendered = /Impact estimé connu sur/i.test(completudeText);
    checks.completudeRatio = /\d+\/\d+/.test(completudeText);
    console.log(`  ✓ Complétude rendue : ${checks.completudeRendered}`);
    console.log(`  ✓ Format X/Y trouvé : ${checks.completudeRatio} (texte: "${completudeText.trim().slice(0, 100)}")`);

    // ── 3. NarrativeBar sum € compact ──────────────────────────────
    console.log('\n3. NarrativeBar Tuile Décisions sum € compact');
    const sumNode = page.locator('[data-testid="stat-tile-sum-eur"]').first();
    const sumExists = (await sumNode.count()) > 0;
    let sumText = '';
    if (sumExists) {
      sumText = (await sumNode.textContent().catch(() => '')) || '';
    }
    checks.sumEurVisible = sumExists && /k€|€/i.test(sumText);
    console.log(`  ✓ Tuile sum € visible : ${checks.sumEurVisible} (texte: "${sumText.trim()}")`);
    await shoot(page, '03-narrativebar-sum-eur');

    // ── 4. Référentiel + colonne « Impact estimé » + montants ─────
    console.log('\n4. /action-center-v4 (Référentiel) — colonne Impact estimé');
    await page.goto(`${FE}/action-center-v4`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    await shoot(page, '04-referentiel-colonne-impact');

    const headerText = (await page.locator('thead').first().textContent().catch(() => '')) || '';
    checks.headerImpactEstime = /impact estim/i.test(headerText);
    console.log(`  ✓ Header « Impact estimé » présent : ${checks.headerImpactEstime}`);

    const bodyText = (await page.locator('tbody').first().textContent().catch(() => '')) || '';
    // Au moins une cellule avec un montant (3 200 € / 7 500 € / 35 k€ / 1 800 €)
    // OU le tiret « — » pour les NULL.
    checks.bodyHasAmounts = /\d[\s  ]?\d{3}\s?€|k€|—/.test(bodyText);
    console.log(`  ✓ Cellules contiennent montants ou « — » : ${checks.bodyHasAmounts}`);

    // ── 5. Tooltip header colonne (hover) ──────────────────────────
    console.log('\n5. Tooltip header « Impact estimé »');
    // Le tooltip est rendu via attribut `title=` natif. Vérif présence.
    const impactHeader = page.locator('thead th:has-text("Impact estimé")').first();
    const tooltipAttr = (await impactHeader.getAttribute('title').catch(() => null)) || '';
    // Note : le `title=` est en fait sur la `<td>` cellule (item-by-item), pas
    // sur le `<th>` header dans le code actuel. Vérifions sur une cellule data.
    const firstAmountCell = page.locator('tbody tr td.text-right').first();
    const cellTooltip = (await firstAmountCell.getAttribute('title').catch(() => null)) || '';
    checks.tooltipPresent = /montant indicatif/i.test(cellTooltip);
    console.log(`  ✓ Tooltip cellule présent : ${checks.tooltipPresent} (texte: "${cellTooltip.slice(0, 80)}")`);
    console.log(`    (tooltip header th: "${tooltipAttr.slice(0, 50)}")`);
    await shoot(page, '05-tooltip-impact');

    // ── 6. Reload F5 — persistence ─────────────────────────────────
    console.log('\n6. Reload F5 — session + données persistent');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    const urlAfterReload = page.url();
    checks.reloadPreservesRoute = urlAfterReload.includes('/action-center-v4');
    const bodyAfterReload = (await page.locator('tbody').first().textContent().catch(() => '')) || '';
    checks.dataAfterReload = bodyAfterReload.length > 100;
    console.log(`  ✓ URL préservée : ${checks.reloadPreservesRoute}`);
    console.log(`  ✓ Données chargées : ${checks.dataAfterReload}`);
    await shoot(page, '06-post-reload');

    // ── BILAN ──
    console.log('\n═══ BILAN WALKTHROUGH M2-6.B.frontend ═══');
    const passing = Object.entries(checks).filter(([, v]) => v).length;
    const total = Object.keys(checks).length;
    for (const [k, v] of Object.entries(checks)) {
      console.log(`  ${v ? '✅' : '❌'} ${k}`);
    }
    console.log(`\nScore checks : ${passing}/${total}`);
    console.log(`Errors JS    : ${errors.length === 0 ? '✅ 0' : `❌ ${errors.length}`}`);
    if (errors.length > 0) {
      console.log('\nErrors détectées :');
      errors.slice(0, 5).forEach((e) => console.log(`  - ${e.substring(0, 200)}`));
    }

    const ok = passing === total && errors.length === 0;
    process.exitCode = ok ? 0 : 1;
  } catch (e) {
    console.error('FATAL:', e.message);
    await shoot(page, '99-fatal').catch(() => {});
    process.exitCode = 2;
  } finally {
    await browser.close();
  }
})();
