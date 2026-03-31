/**
 * PROMEOS — Captures Interactives Décret Tertiaire (Phase 7)
 *
 * 4 captures ciblées :
 *   07-mutualisation-section  — scroll + vue section mutualisation
 *   08-modulation-drawer      — clic sur "Simuler une modulation" → drawer ouvert
 *   09-score-explain-bars     — barres de score explain DT/BACS/APER
 *   10-glossaire-tooltip      — hover sur un terme Explain → tooltip visible
 *
 * Usage:
 *   node audit-interactive-dt.mjs
 *
 * Prérequis: backend sur :8001, frontend sur :5173, pack HELIOS seedé
 */

import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = 'http://localhost:5173';
const BACKEND_URL  = 'http://localhost:8001';
const AUTH_EMAIL    = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';
const OUT_DIR       = resolve(import.meta.dirname || '.', 'screenshots');

async function authenticate(page) {
  const r = await page.request.post(`${BACKEND_URL}/api/auth/login`, {
    data: { email: AUTH_EMAIL, password: AUTH_PASSWORD },
  });
  const body = await r.json();
  const token = body.access_token || body.token;
  if (!token) throw new Error('Auth failed: ' + JSON.stringify(body));

  await page.goto(FRONTEND_URL);
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), token);
  console.log('✓ Authentifié');
}

async function run() {
  mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  try {
    await authenticate(page);

    // ── 07. MutualisationSection ──
    console.log('Capture 07: MutualisationSection...');
    await page.goto(`${FRONTEND_URL}/conformite/tertiaire`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Scroll vers la section mutualisation
    const mutSection = page.locator('[data-testid="mutualisation-section"]');
    const mutText = page.getByText('Mutualisation');
    let mutFound = false;

    if (await mutSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mutSection.scrollIntoViewIfNeeded();
      mutFound = true;
    } else if (await mutText.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await mutText.first().scrollIntoViewIfNeeded();
      mutFound = true;
    } else {
      // Scroll to bottom to find the section
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: join(OUT_DIR, '07-mutualisation-section.png'), fullPage: false });
    console.log(`  → ${mutFound ? '✓ Section trouvée' : '⚠ Section non trouvée (screenshot de la page)'}`);

    // ── 08. ModulationDrawer ──
    console.log('Capture 08: ModulationDrawer...');
    // Navigate to tertiaire page and find first EFA link
    await page.goto(`${FRONTEND_URL}/conformite/tertiaire`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Navigate directly to first EFA detail page
    await page.goto(`${FRONTEND_URL}/conformite/tertiaire/efa/1`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    console.log(`  → URL: ${page.url()}`);

    // Try to open modulation drawer
    const btnModulation = page.getByText('Simuler une modulation');
    const btnModulation2 = page.locator('[data-testid="btn-modulation"]');
    const btnModulation3 = page.getByText('modulation', { exact: false });
    let drawerOpened = false;

    if (await btnModulation.isVisible({ timeout: 3000 }).catch(() => false)) {
      await btnModulation.click();
      await page.waitForTimeout(1000);
      drawerOpened = true;
    } else if (await btnModulation2.isVisible({ timeout: 2000 }).catch(() => false)) {
      await btnModulation2.click();
      await page.waitForTimeout(1000);
      drawerOpened = true;
    } else {
      // Scroll down to find the button
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);
      if (await btnModulation3.isVisible({ timeout: 2000 }).catch(() => false)) {
        await btnModulation3.click();
        await page.waitForTimeout(1000);
        drawerOpened = true;
      }
    }

    await page.screenshot({ path: join(OUT_DIR, '08-modulation-drawer.png'), fullPage: false });
    console.log(`  → ${drawerOpened ? '✓ Drawer ouvert' : '⚠ Bouton modulation non trouvé (screenshot EFA detail)'}`);

    // ── 09. Score Explain ──
    console.log('Capture 09: Score Explain bars...');
    await page.goto(`${FRONTEND_URL}/conformite`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for score explain bars or compliance breakdown
    const scoreSection = page.locator('[data-testid="score-explain"], [data-testid="compliance-breakdown"]');
    if (await scoreSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await scoreSection.scrollIntoViewIfNeeded();
    }
    await page.screenshot({ path: join(OUT_DIR, '09-score-explain-bars.png'), fullPage: false });
    console.log('  → ✓ Captured');

    // ── 10. Glossaire Tooltip ──
    console.log('Capture 10: Glossaire tooltip...');
    await page.goto(`${FRONTEND_URL}/conformite/tertiaire`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const explain = page.locator('[data-glossary], [data-testid="explain"]').first();
    let tooltipVisible = false;

    if (await explain.isVisible({ timeout: 3000 }).catch(() => false)) {
      await explain.hover();
      await page.waitForTimeout(500);
      tooltipVisible = true;
    } else {
      // Fallback: look for any dotted-underline text (typical Explain style)
      const dottedText = page.locator('.border-dashed, [style*="dotted"]').first();
      if (await dottedText.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dottedText.hover();
        await page.waitForTimeout(500);
        tooltipVisible = true;
      }
    }
    await page.screenshot({ path: join(OUT_DIR, '10-glossaire-tooltip.png'), fullPage: false });
    console.log(`  → ${tooltipVisible ? '✓ Tooltip visible' : '⚠ Aucun terme Explain trouvé'}`);

    console.log(`\n✓ 4 captures dans ${OUT_DIR}/`);
  } catch (err) {
    console.error('✗ Erreur:', err.message);
    await page.screenshot({ path: join(OUT_DIR, 'ERROR.png') }).catch(() => {});
  } finally {
    await browser.close();
  }
}

run().catch(console.error);
