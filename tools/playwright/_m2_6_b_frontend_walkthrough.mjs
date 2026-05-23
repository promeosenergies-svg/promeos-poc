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
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

// M2-6.C.P2-cleanup P2-4 — résolution absolue du chemin captures via
// `fileURLToPath(import.meta.url)`. Le script est donc portable depuis
// n'importe quel `cwd` (CI/CD ou exécution manuelle hors racine repo).
// Préféré à `process.env.CLAUDE_PROJECT_DIR` : pas de dépendance env var,
// fonctionne sans configuration supplémentaire.
const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, 'captures', 'm2_6_b_frontend');
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
    // M2-6.B.frontend.bis — format Q19=C closeur :
    // « X actions sur Y portent un impact estimé : Z k€ »
    checks.completudeRendered = /portent un impact estim[eé]|porte un impact estim[eé]/i.test(
      completudeText
    );
    checks.completudeRatio = /\d+\s*actions?\s*sur\s*\d+/i.test(completudeText);

    // M2-6.B.frontend.bis — assertion supplémentaire : le total compact Z k€
    // doit être présent (jamais recalcul FE — pin source-guard SG_AC_V4_MONEY_01).
    const sumCompletudeNode = page.locator('[data-testid="editorial-completude-sum"]');
    const sumCompletudeText =
      (await sumCompletudeNode.textContent().catch(() => '')) || '';
    // Accepte « 47,5 k€ » (NBSP U+202F ou espace régulier) ou « 0 € ».
    checks.completudeSumCfo = /k€|\d\s?€/i.test(sumCompletudeText);

    console.log(`  ✓ Complétude rendue       : ${checks.completudeRendered}`);
    console.log(`  ✓ Format X actions sur Y  : ${checks.completudeRatio} (texte: "${completudeText.trim().slice(0, 120)}")`);
    console.log(`  ✓ Total CFO Z présent     : ${checks.completudeSumCfo} (texte: "${sumCompletudeText.trim()}")`);

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

    // ── 7. M2-6.B.pdf — Click « Exporter COMEX » → download PDF ──────
    console.log('\n7. Click « Exporter COMEX » → download PDF (M2-6.B.pdf)');
    // Retour Pilotage (l'EditorialNarrativeBlock + bouton vivent là).
    await page.goto(`${FE}/action-center-v4/pilotage`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    const exportBtn = page.locator('[data-testid="cta-export-comex"]');
    const exportBtnExists = (await exportBtn.count()) > 0;
    const exportBtnEnabled = exportBtnExists
      ? !(await exportBtn.first().isDisabled())
      : false;
    checks.exportComexButtonActive = exportBtnEnabled;
    console.log(`  ✓ Bouton « Exporter COMEX » présent + enabled : ${exportBtnEnabled}`);

    if (exportBtnEnabled) {
      try {
        const downloadPromise = page.waitForEvent('download', { timeout: 15_000 });
        await exportBtn.first().click();
        const download = await downloadPromise;
        const filename = download.suggestedFilename();
        const filenameOk = /^promeos_comex_.+\.pdf$/i.test(filename);
        checks.exportComexFilenamePattern = filenameOk;
        console.log(`  ✓ Download déclenché : ${filename} (pattern OK : ${filenameOk})`);

        // Sauvegarder le PDF dans captures pour validation manuelle/visuelle.
        const pdfPath = `${OUT}/07-export-${filename}`;
        await download.saveAs(pdfPath);
        checks.exportComexPdfSaved = true;
        console.log(`  ✓ PDF sauvé : ${pdfPath}`);
      } catch (err) {
        console.log(`  ⚠ Download timeout/error : ${err.message.slice(0, 100)}`);
        checks.exportComexFilenamePattern = false;
        checks.exportComexPdfSaved = false;
      }
    } else {
      // Le bouton est disabled — onExportComex handler probablement absent.
      checks.exportComexFilenamePattern = false;
      checks.exportComexPdfSaved = false;
    }
    await shoot(page, '08-post-export-click');

    // ── 9. M2-6.C.1-reduit — Modal LifecycleTransition variant warning (Q30=C) ──
    console.log('\n9. LifecycleTransitionModal variant warning (M2-6.C.1-reduit)');
    // Aller au référentiel + ouvrir le drawer du 1er item via clic ligne.
    await page.goto(`${FE}/action-center-v4`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    try {
      // Cliquer la 1ère ligne → ouvre ItemDetailDrawer.
      const firstRow = page.locator('tbody tr[role="button"]').first();
      await firstRow.click({ timeout: 3_000 });
      await page.waitForTimeout(500);

      // Dans le drawer, trouver le bouton « action principale » qui ouvre
      // LifecycleTransitionModal. Le label varie selon `lifecycle_state`
      // (cf. LIFECYCLE_PRIMARY_ACTION_LABEL dans constants.js) :
      // - new       → « Qualifier »
      // - triaged   → « Planifier »
      // - planned   → « Démarrer »
      // - in_progress → « Marquer comme fait »
      // - closed    → « Rouvrir »
      // M2-6.C.1-reduit.bis — regex Playwright simple (anti « Invalid flags »
      // précédent — apostrophe '' U+2019 + backreferences cassaient le parse).
      const transitionBtn = page
        .getByRole('button', { name: /Qualifier|Planifier|Démarrer|Marquer comme fait|Rouvrir/i })
        .first();
      await transitionBtn.click({ timeout: 3_000 });
      await page.waitForTimeout(400);

      // Modal V4Modal apparu — variant data-variant par défaut.
      const modal = page.locator('[data-testid="v4-modal"]');
      const modalVisible = await modal.isVisible({ timeout: 3_000 });
      checks.modalLifecycleOpens = modalVisible;

      const defaultVariant = modalVisible
        ? await modal.getAttribute('data-variant')
        : null;
      checks.modalVariantDefaultInitially = defaultVariant === 'default';
      console.log(`  ✓ Modal ouvert : ${modalVisible} | data-variant initial : ${defaultVariant}`);

      // Sélectionner newState = "closed" → variant doit passer à "warning".
      if (modalVisible) {
        const select = modal.locator('select').first();
        await select.selectOption({ value: 'closed' });
        await page.waitForTimeout(200);
        const warnVariant = await modal.getAttribute('data-variant');
        checks.modalVariantWarningOnClosed = warnVariant === 'warning';
        console.log(`  ✓ Après sélection "closed" : data-variant = ${warnVariant}`);

        await shoot(page, '09-modal-warning-closed');

        // a11y runtime : role=dialog + aria-modal=true
        const role = await modal.getAttribute('role');
        const ariaModal = await modal.getAttribute('aria-modal');
        checks.modalA11yRoleDialog = role === 'dialog';
        checks.modalA11yAriaModal = ariaModal === 'true';

        // Escape doit fermer le modal (a11y runtime cardinal).
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
        const stillOpen = await modal.isVisible().catch(() => false);
        checks.modalEscapeCloses = !stillOpen;
      } else {
        checks.modalVariantWarningOnClosed = false;
        checks.modalA11yRoleDialog = false;
        checks.modalA11yAriaModal = false;
        checks.modalEscapeCloses = false;
      }
    } catch (err) {
      // UX trigger non trouvé — laisser tous les checks à false + reporter.
      // Discipline transparence : pas de masquage.
      console.warn(`  ⚠ Step 9 UX trigger non trouvé : ${err.message.slice(0, 120)}`);
      checks.modalLifecycleOpens = false;
      checks.modalVariantDefaultInitially = false;
      checks.modalVariantWarningOnClosed = false;
      checks.modalA11yRoleDialog = false;
      checks.modalA11yAriaModal = false;
      checks.modalEscapeCloses = false;
    }

    // ── 10. M2-6.C.2 — Tuile « Sans responsable » cliquable → filtre URL ──
    console.log('\n10. Tuile « Sans responsable » cliquable + banner filtre (M2-6.C.2)');
    try {
      // Aller au Pilotage pour avoir la NarrativeBar avec count_without_owner.
      await page.goto(`${FE}/action-center-v4/pilotage`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(600);

      // La tuile cliquable est un <button data-testid="stat-tile-clickable">
      // qui contient le label « Sans responsable ». On filtre par text pour
      // cibler spécifiquement celle-là (pas une autre tuile cliquable future).
      const tuileWithoutOwner = page
        .locator('[data-testid="stat-tile-clickable"]')
        .filter({ hasText: /sans responsable/i })
        .first();
      const tuileExists = (await tuileWithoutOwner.count()) > 0;
      checks.withoutOwnerTuileClickable = tuileExists;

      if (tuileExists) {
        await tuileWithoutOwner.click({ timeout: 3_000 });
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(400);

        // Navigation vers Référentiel avec ?without_owner=true
        const url = page.url();
        checks.withoutOwnerNavigatesReferentiel =
          url.includes('/action-center-v4') &&
          !url.includes('/pilotage') &&
          url.includes('without_owner=true');

        // Banner indicateur filtre actif visible.
        const banner = page.locator('[data-testid="filter-without-owner-banner"]');
        const bannerVisible = await banner.isVisible({ timeout: 2_000 }).catch(() => false);
        checks.withoutOwnerBannerVisible = bannerVisible;

        await shoot(page, '10-without-owner-filter-active');

        // Effacer le filtre via le bouton ×.
        if (bannerVisible) {
          const clearBtn = page.locator('[data-testid="filter-without-owner-clear"]');
          await clearBtn.click();
          await page.waitForTimeout(300);
          const bannerStillVisible = await banner
            .isVisible()
            .catch(() => false);
          checks.withoutOwnerClearWorks = !bannerStillVisible;
        } else {
          checks.withoutOwnerClearWorks = false;
        }
      } else {
        // Tuile non-cliquable (probablement count_without_owner = 0)
        checks.withoutOwnerNavigatesReferentiel = false;
        checks.withoutOwnerBannerVisible = false;
        checks.withoutOwnerClearWorks = false;
      }
    } catch (err) {
      console.warn(`  ⚠ Step 10 « Sans responsable » : ${err.message.slice(0, 120)}`);
      checks.withoutOwnerTuileClickable = false;
      checks.withoutOwnerNavigatesReferentiel = false;
      checks.withoutOwnerBannerVisible = false;
      checks.withoutOwnerClearWorks = false;
    }

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
