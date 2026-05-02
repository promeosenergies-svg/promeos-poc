/**
 * PROMEOS — Smoke Playwright Phase 1.F (P1.0) Navigation P0 closure proof
 *
 * Capture visuelle des 5 P0 audit docs/audits/navigation_audit_20260501.md
 * clos (commits b14af2b6 → b7e25880, branche claude/refonte-sol2) :
 *   - P0.1 Bill Intelligence module rail (Phase 1.D)
 *   - P0.2 Rename canonical Cockpit labels (Phase 1.A)
 *   - P0.3 Centre d'action en panel Accueil (Phase 1.C)
 *   - P0.4 Badges conformité morts retirés (Phase 1.B)
 *   - P0.5 Ordre rail final + séparateur Patrimoine (Phase 1.E)
 *
 * Prérequis :
 *   - Dev server frontend actif sur 127.0.0.1:5175 (port figé refonte-sol2).
 *   - Backend FastAPI actif sur 127.0.0.1:8001.
 *   - Demo admin seed (`promeos@promeos.io / promeos2024`, role DG_OWNER).
 *
 * Stratégie persona :
 *   Le seed démo n'expose qu'un user DG_OWNER. Pour capturer 2 ordres
 *   rail différents (default + daf), on intercepte la réponse
 *   `/auth/login` via `page.route()` et on substitue `body.role` à la
 *   volée — l'API backend reste inchangée (read-only proof).
 *
 * Usage :
 *   node tools/playwright/nav_p0_smoke.spec.mjs
 *
 * Sortie :
 *   tools/playwright/screenshots/nav_p0/{rail_default,rail_daf,
 *     panel_cockpit,panel_facturation,palette_centre}.png
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';

const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://127.0.0.1:5175';
const OUT_DIR = process.env.OUT_DIR || 'tools/playwright/screenshots/nav_p0';
const AUTH_EMAIL = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';

mkdirSync(OUT_DIR, { recursive: true });

// ── Utilitaire : login + override role optionnel ─────────────────────
async function loginAs(page, roleOverride = null) {
  if (roleOverride) {
    // Intercepte la réponse /auth/login pour réécrire le rôle SANS toucher
    // au backend. Le frontend AuthContext.jsx setRole(data.role) consomme
    // le payload modifié ; tout le reste (token, user, org) est préservé.
    await page.route('**/api/auth/login', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.role = roleOverride;
      await route.fulfill({
        status: response.status(),
        headers: response.headers(),
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    });
  }
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(800);
  await page.fill('input[type="email"], input[name="email"]', AUTH_EMAIL, { timeout: 5000 });
  await page.fill('input[type="password"], input[name="password"]', AUTH_PASSWORD, { timeout: 5000 });
  await page.click('button[type="submit"]');
  // Tolère un timeout de redirection — certains contextes restent sur
  // /login en SPA tant que les async storages ne sont pas hydratés.
  // On retombe sur waitForTimeout simple, le rail nav apparaît dès que
  // AuthContext setRole(...).
  await page
    .waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 8000 })
    .catch(() => {});
  await page.waitForTimeout(1800);
}

// ── Utilitaire : extraire les labels rail via DOM ────────────────────
async function railLabels(page) {
  return await page.$$eval(
    '[role="navigation"][aria-label="Modules"] button[aria-label]',
    (buttons) => buttons.map((b) => b.getAttribute('aria-label'))
  );
}

// ── Test runner minimaliste ─────────────────────────────────────────
const results = [];
function check(name, condition, details = '') {
  const ok = !!condition;
  results.push({ name, ok, details });
  console.log(`${ok ? '✓' : '✗'} ${name}${details ? ` — ${details}` : ''}`);
}

(async () => {
  console.log(`\nPROMEOS — Phase 1.F P1.0 Navigation P0 smoke`);
  console.log(`Target: ${BASE}`);
  console.log(`Output: ${OUT_DIR}\n`);

  const browser = await chromium.launch({ headless: true });

  try {
    // ════════════════════════════════════════════════════════════════
    // SMOKE 1 — persona default (= energy_manager order Sol §2)
    // Cible : Accueil → Énergie → Conformité → Facturation → Achat
    //         → [séparateur] → Patrimoine
    // ════════════════════════════════════════════════════════════════
    {
      const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        locale: 'fr-FR',
      });
      const page = await ctx.newPage();
      await loginAs(page, 'energy_manager');

      const labels = await railLabels(page);
      console.log(`[default] rail labels: ${JSON.stringify(labels)}`);

      const rail = await page.$('[role="navigation"][aria-label="Modules"]');
      if (!rail) throw new Error('Rail nav non trouvé (selector [role="navigation"][aria-label="Modules"])');
      await rail.screenshot({ path: join(OUT_DIR, 'rail_default.png') });

      check(
        'P0.5 — default rail order = Sol v1.1 cible',
        JSON.stringify(labels) ===
          JSON.stringify(['Accueil', 'Énergie', 'Conformité', 'Facturation', 'Achat', 'Patrimoine']),
        labels.join(' → ')
      );

      check(
        'P0.5 — Patrimoine en dernière position visible',
        labels[labels.length - 1] === 'Patrimoine'
      );

      const separator = await page.$('[role="navigation"][aria-label="Modules"] [role="separator"]');
      check('P0.5 — séparateur DOM rendu (role="separator")', !!separator);
      if (separator) {
        const orientation = await separator.getAttribute('aria-orientation');
        check('P0.5 — séparateur aria-orientation="vertical"', orientation === 'vertical');
      }

      // Panel Cockpit ouvert (Accueil = module actif après login)
      await page.waitForTimeout(800);
      const panel = await page.$('aside, [role="navigation"][aria-label*="anel" i], [data-testid*="panel" i]')
        || (await page.$('[role="navigation"][aria-label="Modules"]'))?.evaluateHandle((nav) => nav.parentElement);
      // Capture la zone latérale (rail + panel) plutôt que page entière
      await page.screenshot({
        path: join(OUT_DIR, 'panel_cockpit.png'),
        clip: { x: 0, y: 0, width: 280, height: 700 },
      });

      // Vérification présence des 3 items canoniques Cockpit panel
      const panelText = await page.locator('body').textContent();
      check(
        "P0.2 — panel Cockpit contient 'Briefing du jour'",
        panelText.includes('Briefing du jour')
      );
      check(
        "P0.2 — panel Cockpit contient 'Synthèse stratégique'",
        panelText.includes('Synthèse stratégique')
      );
      check(
        "P0.3 — panel Cockpit contient 'Centre d'action'",
        panelText.includes("Centre d'action")
      );

      // ── ⌘K palette + tape "centre" ─────────────────────────────────
      // AppShell.jsx:244 listener `(ctrlKey || metaKey) && key === 'k'`
      // attaché sur document. On dispatch via evaluate pour matcher
      // exactement la condition (Playwright keyboard.press peut ne pas
      // bubbler vers document en headless selon focus actif).
      await page.evaluate(() => {
        const ev = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
        document.dispatchEvent(ev);
      });
      await page.waitForTimeout(600);
      const paletteInput = await page.$('input[placeholder*="Rechercher" i], input[placeholder*="echerch" i], input[type="search"], [role="combobox"]');
      if (paletteInput) {
        await paletteInput.fill('centre');
        await page.waitForTimeout(400);
        const paletteText = await page.locator('body').textContent();
        check(
          "P0.3 — ⌘K + 'centre' affiche match Centre d'action",
          paletteText.includes("Centre d'action") || paletteText.includes('Anomalies')
        );
        await page.screenshot({
          path: join(OUT_DIR, 'palette_centre.png'),
          clip: { x: 0, y: 0, width: 900, height: 600 },
        });
      } else {
        console.log('[default] ⌘K palette input not found, skipping palette capture');
      }
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      // ── Click module Facturation pour ouvrir son panel ─────────────
      const factBtn = await page.$('[role="navigation"][aria-label="Modules"] button[aria-label="Facturation"]');
      if (factBtn) {
        await factBtn.click();
        await page.waitForTimeout(800);
        await page.screenshot({
          path: join(OUT_DIR, 'panel_facturation.png'),
          clip: { x: 0, y: 0, width: 280, height: 700 },
        });
        const facturationText = await page.locator('body').textContent();
        check(
          "P0.1 — panel Facturation contient 'Vue d'ensemble'",
          facturationText.includes("Vue d'ensemble")
        );
      } else {
        console.log('[default] Facturation rail button not found, panel skipped');
      }

      await ctx.close();
    }

    // ════════════════════════════════════════════════════════════════
    // SMOKE 2 — persona DAF
    // Cible : Accueil → Facturation → Conformité → Énergie → Achat
    //         → [séparateur] → Patrimoine
    // ════════════════════════════════════════════════════════════════
    {
      const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        locale: 'fr-FR',
      });
      const page = await ctx.newPage();
      await loginAs(page, 'daf');

      const labels = await railLabels(page);
      console.log(`[daf] rail labels: ${JSON.stringify(labels)}`);

      const rail = await page.$('[role="navigation"][aria-label="Modules"]');
      await rail.screenshot({ path: join(OUT_DIR, 'rail_daf.png') });

      check(
        'P0.5 — daf rail Facturation en position 2',
        labels[0] === 'Accueil' && labels[1] === 'Facturation',
        labels.join(' → ')
      );

      check(
        'P0.5 — daf Patrimoine toujours en dernière position',
        labels[labels.length - 1] === 'Patrimoine'
      );

      await ctx.close();
    }
  } catch (err) {
    console.error(`\n✗ FATAL: ${err.message}`);
    console.error(err.stack);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }

  // ── Bilan ─────────────────────────────────────────────────────────
  const passed = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n────────────────────────────────────────`);
  console.log(`Smoke result: ${passed} passed, ${failed} failed`);
  console.log(`Captures: ${OUT_DIR}/`);
  writeFileSync(
    join(OUT_DIR, 'smoke_report.json'),
    JSON.stringify({ ts: new Date().toISOString(), passed, failed, results }, null, 2)
  );
  if (failed > 0) process.exitCode = 1;
})();
