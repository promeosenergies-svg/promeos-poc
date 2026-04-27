/**
 * PROMEOS — Démo Marie DAF 90s scénarisée (Sprint 2 Vague C ét12f).
 *
 * Pitch deck slide 4 : « Marie ouvre Cockpit, repère un événement DT
 * critique, comprend l'origine en 1 clic, arbitre l'action ».
 *
 * Scénario 90s timeline :
 *   t=0     : login auto + landing /cockpit
 *   t=15s   : capture hero — narrative + KPIs + SolEventStream natif §10
 *   t=30s   : zoom screenshot SolEventCard (severity + mitigation 14px + footer)
 *   t=45s   : clic icône Info → popover methodology drill-down
 *   t=60s   : capture popover (CFO P0 #3 ét12e — provenance traçable)
 *   t=75s   : clic CTA "Ouvrir conformité"
 *   t=90s   : landing /conformite avec contexte préservé
 *
 * Sortie : tools/playwright/captures/demo-marie-90s/
 *   - 01-cockpit-hero.png (1920×1080)
 *   - 02-sol-event-card-zoom.png (clip 800×600)
 *   - 03-methodology-popover.png (clip 600×400)
 *   - 04-conformite-landing.png (1920×1080)
 *   - timeline.json (timestamps + durations)
 *
 * Prérequis :
 *   - Backend lancé (port 8001) : cd backend && python main.py
 *   - Frontend lancé (port 5173) : cd frontend && npm run dev
 *   - Seed démo helios actif (DEMO_MODE=true)
 *
 * Usage :
 *   node tools/playwright/demo-marie-90s.mjs
 *   node tools/playwright/demo-marie-90s.mjs --headed  # voir le navigateur
 *   node tools/playwright/demo-marie-90s.mjs --slow=300 # ralenti 300ms par action
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const BACKEND_URL = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const AUTH_EMAIL = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';

const OUT_DIR = resolve(process.cwd(), 'tools', 'playwright', 'captures', 'demo-marie-90s');

// CLI parsing minimal
const args = process.argv.slice(2);
const HEADED = args.includes('--headed');
const SLOW_MO = (() => {
  const arg = args.find((a) => a.startsWith('--slow='));
  return arg ? parseInt(arg.slice(7), 10) : 0;
})();

function log(step, msg) {
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`[${ts}] ${step.padEnd(8)} ${msg}`);
}

async function main() {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const timeline = { start: new Date().toISOString(), steps: [] };
  const tic = (name) => timeline.steps.push({ name, t: Date.now() });

  const browser = await chromium.launch({ headless: !HEADED, slowMo: SLOW_MO });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  // ── Auth (DEMO_MODE) ────────────────────────────────────────────
  log('AUTH', 'login + JWT');
  tic('auth_start');
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
  // Utilise le proxy Vite (/api → backend 8001) pour rester same-origin —
  // évite CORS quand le frontend tourne sur 5175 et le backend sur 8001.
  const loginResp = await page.evaluate(
    async ({ email, password }) => {
      const res = await fetch(`/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      return res.json();
    },
    { email: AUTH_EMAIL, password: AUTH_PASSWORD }
  );
  if (!loginResp.access_token) {
    console.error('[AUTH] FAILED:', loginResp.detail || 'Unknown');
    await browser.close();
    process.exit(1);
  }
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), loginResp.access_token);
  tic('auth_done');

  // ── t=0 → t=15s : Cockpit hero ──────────────────────────────────
  log('STEP-1', 'navigate /cockpit');
  await page.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
  // Attendre que le SolEventStream soit présent (signe que les events ont été poussés)
  await page
    .waitForSelector('[data-testid="sol-event-stream"], [data-testid^="sol-event-card-"]', {
      timeout: 8000,
    })
    .catch(() => log('STEP-1', '⚠ SolEventStream non visible, fallback week-cards probable'));
  await page.waitForTimeout(1500);
  tic('cockpit_loaded');

  log('CAP-1', '01-cockpit-hero.png (full page hero §5 + SolEventStream)');
  await page.screenshot({
    path: join(OUT_DIR, '01-cockpit-hero.png'),
    fullPage: false,
  });

  // ── t=30s : Zoom sur la première SolEventCard ───────────────────
  const firstCard = page.locator('[data-testid^="sol-event-card-"]').first();
  const cardVisible = await firstCard.isVisible().catch(() => false);
  if (cardVisible) {
    log('CAP-2', '02-sol-event-card-zoom.png (sévérité + mitigation 14px + footer source)');
    const box = await firstCard.boundingBox();
    if (box) {
      await page.screenshot({
        path: join(OUT_DIR, '02-sol-event-card-zoom.png'),
        clip: {
          x: Math.max(0, box.x - 10),
          y: Math.max(0, box.y - 10),
          width: Math.min(800, box.width + 20),
          height: Math.min(700, box.height + 20),
        },
      });
    }
    tic('event_card_zoom');

    // ── t=45s → t=60s : clic Info → popover methodology ───────────
    log('STEP-2', 'clic icône Info → popover methodology drill-down');
    const infoBtn = firstCard.locator('button[aria-label="Voir la méthodologie de calcul"]').first();
    if (await infoBtn.isVisible().catch(() => false)) {
      await infoBtn.click();
      await page.waitForTimeout(800);
      // Le popover apparaît sous la ligne source
      await page
        .waitForSelector('[role="region"][aria-label="Méthodologie de calcul"]', { timeout: 3000 })
        .catch(() => log('STEP-2', '⚠ Popover methodology non trouvé'));
      tic('methodology_popover_open');

      log('CAP-3', '03-methodology-popover.png (CFO P0 #3 ét12e — provenance)');
      // Capture étendue : card + popover juste en dessous
      const cardBox = await firstCard.boundingBox();
      if (cardBox) {
        await page.screenshot({
          path: join(OUT_DIR, '03-methodology-popover.png'),
          clip: {
            x: Math.max(0, cardBox.x - 10),
            y: Math.max(0, cardBox.y - 10),
            width: Math.min(800, cardBox.width + 20),
            height: Math.min(900, cardBox.height + 220), // +200 pour le popover
          },
        });
      }
    } else {
      log('STEP-2', '⚠ Bouton Info non trouvé (event sans methodology ?)');
    }

    // ── t=75s → t=90s : clic CTA "Ouvrir" → landing /conformite ───
    log('STEP-3', 'clic CTA action sur la card');
    // La card entière est cliquable (role="button"). Cliquer hors du bouton Info.
    const cardBoxAfter = await firstCard.boundingBox();
    if (cardBoxAfter) {
      // Cliquer sur le titre (haut de la card, loin du footer Info)
      await page.mouse.click(cardBoxAfter.x + cardBoxAfter.width / 2, cardBoxAfter.y + 50);
      await page.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2000);
      tic('cta_navigated');

      log('CAP-4', `04-${page.url().split('/').pop().split('?')[0]}-landing.png`);
      await page.screenshot({
        path: join(OUT_DIR, '04-conformite-landing.png'),
        fullPage: false,
      });
    }
  } else {
    log('CAP-2', '⚠ Aucune SolEventCard visible — démo dégrade en week-cards. Vérifier le seed.');
    await page.screenshot({
      path: join(OUT_DIR, '02-fallback-week-cards.png'),
      fullPage: false,
    });
  }

  tic('end');

  // ── Timeline JSON pour pitch deck ───────────────────────────────
  const t0 = timeline.steps[0].t;
  const enriched = timeline.steps.map((s) => ({
    ...s,
    elapsed_ms: s.t - t0,
    elapsed_sec: ((s.t - t0) / 1000).toFixed(1),
  }));
  writeFileSync(
    join(OUT_DIR, 'timeline.json'),
    JSON.stringify({ start: timeline.start, total_ms: Date.now() - t0, steps: enriched }, null, 2)
  );

  log('DONE', `Captures + timeline → ${OUT_DIR}`);
  console.log(`\nDurée totale : ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  console.log('Pitch deck slide 4 : utiliser 01-cockpit-hero.png + 03-methodology-popover.png\n');

  await browser.close();
}

main().catch((err) => {
  console.error('[FATAL]', err);
  process.exit(1);
});
