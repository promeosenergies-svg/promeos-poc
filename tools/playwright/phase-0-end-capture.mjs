/**
 * PROMEOS — Audit UX/UI/CX/Nav/Densité/Ergonomie 28/04/2026.
 *
 * Capture les 10 pages doctrine v1.1 + 4 captures d'interactions clés
 * pour audit personas Marie/CFO/EM/Yannick post-Vague E.
 *
 * Auth via proxy Vite (same-origin /api → backend 8001) — évite CORS.
 *
 * Sortie : tools/playwright/captures/phase-0-end/
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const AUTH_EMAIL = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';
const OUT_DIR = resolve(process.cwd(), 'tools', 'playwright', 'captures', 'phase-0-end');

// Pages doctrine v1.1 — couverture nav 100% (10 pages canoniques)
const PAGES = [
  { name: '01-cockpit', path: '/cockpit', section: 'pilotage' },
  { name: '02-patrimoine', path: '/patrimoine', section: 'patrimoine' },
  { name: '03-conformite', path: '/conformite', section: 'patrimoine' },
  { name: '04-bill-intel', path: '/bill-intel', section: 'finance' },
  { name: '05-achat-energie', path: '/achat-energie', section: 'finance' },
  { name: '06-flex', path: '/flex', section: 'pilotage' },
  { name: '07-anomalies', path: '/anomalies', section: 'pilotage' },
  { name: '08-diagnostic-conso', path: '/diagnostic-conso', section: 'energie' },
  { name: '09-plan-actions', path: '/plan-actions', section: 'pilotage' },
  { name: '10-notifications', path: '/notifications', section: 'pilotage' },
];

const log = (s) => console.log(`[${new Date().toISOString().slice(11, 23)}] ${s}`);

async function main() {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  // ── Auth via proxy Vite (same-origin) ───────────────────────────
  log('AUTH login + JWT (via proxy)');
  // Navigate avec networkidle pour s'assurer que JS bundle est chargé
  // avant page.evaluate (sinon fetch peut échouer silencieusement).
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
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

  // ── Capture les 10 pages ────────────────────────────────────────
  // Stratégie wait robuste : domcontentloaded → networkidle (timeout généreux)
  // → wait headings ou main → screenshot. Évite captures "Chargement..." figées.
  const results = { ok: [], fail: [] };
  for (const { name, path, section } of PAGES) {
    process.stdout.write(`[${section.padEnd(10)}] ${name}...`);
    try {
      await page.goto(FRONTEND_URL + path, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
      // Attendre soit un h1, soit data-testid de page chargée, soit fallback 4s
      await Promise.race([
        page.waitForSelector('h1, h2, [data-testid="sol-page-header"], main', { timeout: 10000 }),
        page.waitForTimeout(4000),
      ]).catch(() => {});
      // Tampon final pour les charts Recharts qui mettent ~1s à dessiner
      await page.waitForTimeout(2500);
      await page.screenshot({
        path: join(OUT_DIR, `${name}.png`),
        fullPage: false, // viewport 1920x1080 (premier écran = ce que voit Marie)
      });
      console.log(' ✓');
      results.ok.push(name);
    } catch (err) {
      console.log(` ✗ ${err.message.slice(0, 60)}`);
      results.fail.push({ name, error: err.message });
    }
  }

  // ── Captures d'interactions clés ────────────────────────────────
  log('INTERACTIONS — Cockpit clic SolEventCard popover Info');
  await page.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const infoBtn = page.locator('button[aria-label="Voir la méthodologie de calcul"]').first();
  if (await infoBtn.isVisible().catch(() => false)) {
    await infoBtn.click();
    await page.waitForTimeout(700);
    await page.screenshot({ path: join(OUT_DIR, '11-cockpit-popover-methodology.png') });
    log('  ✓ popover methodology capté');
  }

  log('INTERACTIONS — Cockpit fullPage (audit densité scroll)');
  await page.screenshot({ path: join(OUT_DIR, '12-cockpit-fullpage.png'), fullPage: true });
  log('  ✓ fullpage Cockpit');

  log('INTERACTIONS — Mobile sm: viewport 375×812 (densité responsive)');
  await context.close();
  const mobileCtx = await browser.newContext({
    viewport: { width: 375, height: 812 },
    locale: 'fr-FR',
    deviceScaleFactor: 2,
  });
  const mobilePage = await mobileCtx.newPage();
  await mobilePage.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded' });
  await mobilePage.evaluate((t) => localStorage.setItem('promeos_token', t), loginResp.access_token);
  await mobilePage.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded' });
  await mobilePage.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  await mobilePage.waitForTimeout(1500);
  await mobilePage.screenshot({ path: join(OUT_DIR, '13-cockpit-mobile-375.png'), fullPage: false });
  log('  ✓ Cockpit mobile 375px capté');

  await browser.close();

  console.log(`\n=== Résultats ===`);
  console.log(`✓ ${results.ok.length} pages capturées`);
  if (results.fail.length) console.log(`✗ ${results.fail.length} pages KO :`, results.fail);
  console.log(`Dossier : ${OUT_DIR}\n`);
}

main().catch((err) => {
  console.error('[FATAL]', err);
  process.exit(1);
});
