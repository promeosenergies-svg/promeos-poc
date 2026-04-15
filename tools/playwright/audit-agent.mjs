/**
 * PROMEOS — Agent Playwright d'audit front-end
 *
 * Usage:
 *   node audit-agent.mjs                    # Capture toutes les pages
 *   node audit-agent.mjs --pages cockpit,patrimoine  # Pages spécifiques
 *   node audit-agent.mjs --viewport 1440x900         # Viewport custom
 *   node audit-agent.mjs --out ./artifacts/audits/captures # Dossier de sortie custom
 *   node audit-agent.mjs --no-full-page               # Pas de fullPage (viewport only)
 *   node audit-agent.mjs --interactions               # Active les captures d'interactions
 *
 * Prérequis:
 *   npm i playwright
 *   npx playwright install chromium
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';

// ─── Config ────────────────────────────────────────────────────────
const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const BACKEND_URL  = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const AUTH_EMAIL    = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';
const DEFAULT_DIR   = resolve(process.cwd(), 'artifacts', 'audits', 'captures');

// ─── Toutes les pages auditables (route canonique, dédupl.) ────────
const ALL_PAGES = [
  // PILOTAGE
  { name: '01-cockpit',            path: '/cockpit',                section: 'pilotage' },
  { name: '02-actions',            path: '/actions',                section: 'pilotage' },
  { name: '03-notifications',      path: '/notifications',          section: 'pilotage' },

  // PATRIMOINE
  { name: '04-patrimoine',         path: '/patrimoine',             section: 'patrimoine' },
  { name: '05-conformite',         path: '/conformite',             section: 'patrimoine' },
  { name: '06-contrats',             path: '/contrats',             section: 'patrimoine' },
  { name: '06b-conformite-tertiaire', path: '/conformite/tertiaire', section: 'patrimoine' },

  // ÉNERGIE — Consommations
  { name: '07-consommations',      path: '/consommations',          section: 'energie' },
  { name: '08-explorer',           path: '/consommations/explorer', section: 'energie' },
  { name: '09-portfolio-conso',    path: '/consommations/portfolio',section: 'energie' },
  { name: '10-import-conso',       path: '/consommations/import',   section: 'energie' },
  { name: '11-diagnostic',         path: '/diagnostic-conso',       section: 'energie' },
  { name: '12-monitoring',         path: '/monitoring',             section: 'energie' },
  { name: '13-usages-horaires',    path: '/usages-horaires',        section: 'energie' },

  // ÉNERGIE — Facturation
  { name: '14-bill-intel',         path: '/bill-intel',             section: 'facturation' },
  { name: '15-billing-timeline',   path: '/billing',                section: 'facturation' },

  // ACHAT
  { name: '16-achat-energie',      path: '/achat-energie',          section: 'achat' },
  { name: '17-assistant-achat',    path: '/achat-assistant',        section: 'achat' },
  { name: '18-renouvellements',    path: '/renouvellements',        section: 'achat' },

  // ADMIN & SYSTÈME
  { name: '19-admin-users',        path: '/admin/users',            section: 'admin' },
  { name: '20-onboarding',         path: '/onboarding',             section: 'admin' },
  { name: '21-connectors',         path: '/connectors',             section: 'admin' },
  { name: '22-activation',         path: '/activation',             section: 'admin' },
  { name: '23-status',             path: '/status',                 section: 'admin' },

  // AUTRES
  { name: '24-kb',                 path: '/kb',                     section: 'autre' },
  { name: '25-segmentation',       path: '/segmentation',           section: 'autre' },
  { name: '26-command-center',     path: '/',                       section: 'autre' },
  { name: '27-energy-copilot',     path: '/energy-copilot',         section: 'autre' },
];

// ─── Interactions à tester (optionnel, --interactions) ─────────────
const INTERACTIONS = [
  {
    name: 'INT-01-cockpit-tooltip',
    path: '/cockpit',
    action: async (page) => {
      // Hover sur le premier KPI pour voir tooltip
      const kpi = page.locator('[data-testid="kpi-card"], .bg-white.rounded-xl').first();
      if (await kpi.isVisible()) await kpi.hover();
      await page.waitForTimeout(800);
    },
  },
  {
    name: 'INT-02-sidebar-expand',
    path: '/cockpit',
    action: async (page) => {
      // Cliquer sur une section sidebar pour la déplier
      const section = page.locator('text=PATRIMOINE').first();
      if (await section.isVisible()) await section.click();
      await page.waitForTimeout(500);
    },
  },
  {
    name: 'INT-03-explorer-filters',
    path: '/consommations/explorer',
    action: async (page) => {
      // Cliquer toggle Expert si visible
      const expertBtn = page.locator('button:has-text("Expert")').first();
      if (await expertBtn.isVisible()) await expertBtn.click();
      await page.waitForTimeout(1000);
    },
  },
  {
    name: 'INT-04-bill-intel-drawer',
    path: '/bill-intel',
    action: async (page) => {
      // Cliquer sur la première anomalie pour ouvrir le drawer
      const anomaly = page.locator('button:has-text("Comprendre"), button:has-text("Détail"), [data-testid="insight-row"]').first();
      if (await anomaly.isVisible()) {
        await anomaly.click();
        await page.waitForTimeout(1500);
      }
    },
  },
  {
    name: 'INT-05-patrimoine-site-detail',
    path: '/patrimoine',
    action: async (page) => {
      // Cliquer sur le premier site dans le tableau
      const row = page.locator('table tbody tr').first();
      if (await row.isVisible()) {
        await row.click();
        await page.waitForTimeout(1500);
      }
    },
  },
  {
    name: 'INT-06-conformite-tab',
    path: '/conformite',
    action: async (page) => {
      // Cliquer sur l'onglet "Plan d'actions"
      const tab = page.locator('button:has-text("Plan d"), a:has-text("Plan d")').first();
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(1000);
      }
    },
  },
  {
    name: 'INT-07-achat-simulation',
    path: '/achat-energie',
    action: async (page) => {
      // Cliquer "Comparer les scénarios"
      const btn = page.locator('button:has-text("Comparer")').first();
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(2000);
      }
    },
  },
  {
    name: 'INT-08-search-palette',
    path: '/cockpit',
    action: async (page) => {
      // Ouvrir la palette de recherche (Ctrl+K)
      await page.keyboard.press('Control+k');
      await page.waitForTimeout(1000);
    },
  },
];

// ─── CLI parsing ───────────────────────────────────────────────────
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    pages: null,       // null = all, or comma-separated names
    viewport: '1920x1080',
    outDir: DEFAULT_DIR,
    fullPage: true,
    interactions: false,
    sections: null,    // filter by section
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--pages':
        opts.pages = args[++i]?.split(',').map(s => s.trim());
        break;
      case '--viewport':
        opts.viewport = args[++i];
        break;
      case '--out':
        opts.outDir = resolve(args[++i]);
        break;
      case '--no-full-page':
        opts.fullPage = false;
        break;
      case '--interactions':
        opts.interactions = true;
        break;
      case '--sections':
        opts.sections = args[++i]?.split(',').map(s => s.trim());
        break;
      case '--help':
        console.log(`
PROMEOS Audit Agent — Playwright screenshot capture

Options:
  --pages cockpit,patrimoine   Capture only specific pages (by name keyword)
  --sections pilotage,energie  Capture only specific sections
  --viewport 1440x900          Custom viewport (default: 1920x1080)
  --out ./path                 Output directory (default: ./captures)
  --no-full-page               Capture viewport only, not full scroll
  --interactions               Also capture interaction screenshots
  --help                       Show this help
`);
        process.exit(0);
    }
  }
  return opts;
}

// ─── Main ──────────────────────────────────────────────────────────
(async () => {
  const opts = parseArgs();
  const [vw, vh] = opts.viewport.split('x').map(Number);

  // Create output directory with timestamp subfolder
  const timestamp = new Date().toISOString().slice(0, 16).replace(/[T:]/g, '-');
  const outDir = join(opts.outDir, timestamp);
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

  console.log(`\n=== PROMEOS Audit Agent ===`);
  console.log(`Output:   ${outDir}`);
  console.log(`Viewport: ${vw}x${vh}`);
  console.log(`FullPage: ${opts.fullPage}`);
  console.log('');

  // Filter pages
  let pages = ALL_PAGES;
  if (opts.pages) {
    pages = pages.filter(p =>
      opts.pages.some(kw => p.name.includes(kw) || p.path.includes(kw))
    );
  }
  if (opts.sections) {
    pages = pages.filter(p => opts.sections.includes(p.section));
  }

  console.log(`Pages to capture: ${pages.length}`);

  // Launch browser
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: vw, height: vh },
    locale: 'fr-FR',
  });
  const page = await context.newPage();

  // ─── Authentication ──────────────────────────────────────────
  console.log('\n[AUTH] Fetching JWT token...');
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded', timeout: 15000 });

  const loginResp = await page.evaluate(async ({ url, email, password }) => {
    const res = await fetch(`${url}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return res.json();
  }, { url: BACKEND_URL, email: AUTH_EMAIL, password: AUTH_PASSWORD });

  if (!loginResp.access_token) {
    console.error('[AUTH] FAILED:', loginResp.detail || 'Unknown error');
    await browser.close();
    process.exit(1);
  }

  await page.evaluate((token) => {
    localStorage.setItem('promeos_token', token);
  }, loginResp.access_token);

  // Navigate to cockpit to validate auth
  await page.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2000);

  const isAuth = page.url().includes('/cockpit');
  if (!isAuth) {
    console.error('[AUTH] Login failed — redirected to:', page.url());
    await browser.close();
    process.exit(1);
  }
  console.log(`[AUTH] OK — ${loginResp.user.email} (${loginResp.role})\n`);

  // ─── Capture pages ───────────────────────────────────────────
  const results = { ok: [], fail: [], notFound: [] };

  for (const { name, path, section } of pages) {
    try {
      process.stdout.write(`[${section.toUpperCase().padEnd(12)}] ${name}...`);
      await page.goto(FRONTEND_URL + path, { waitUntil: 'domcontentloaded', timeout: 12000 }).catch(() => {});

      // Wait for the app to finish loading data:
      // 1. Wait for any cascading API calls (auth/me → scope → page data) to settle
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
      // 2. Wait for skeleton/loading placeholders to disappear (animate-pulse divs)
      //    This handles cascading fetches that fire after networkidle settles prematurely
      await page.waitForFunction(() => {
        const skeletons = document.querySelectorAll('.animate-pulse');
        return skeletons.length === 0;
      }, { timeout: 8000 }).catch(() => {});
      // 3. Small buffer for final paint
      await page.waitForTimeout(500);

      // Detect 404 / "Page introuvable"
      const is404 = await page.locator('text=Page introuvable, text=introuvable').first().isVisible().catch(() => false);

      const filename = `${name}.png`;
      await page.screenshot({
        path: join(outDir, filename),
        fullPage: opts.fullPage,
      });

      if (is404) {
        console.log(` 404 (captured)`);
        results.notFound.push({ name, path });
      } else {
        console.log(` OK`);
        results.ok.push({ name, path });
      }
    } catch (err) {
      console.log(` FAIL: ${err.message.slice(0, 80)}`);
      results.fail.push({ name, path, error: err.message });
    }
  }

  // ─── Capture interactions (optional) ─────────────────────────
  if (opts.interactions) {
    console.log('\n--- Interactions ---\n');
    for (const { name, path, action } of INTERACTIONS) {
      try {
        process.stdout.write(`[INTERACTION] ${name}...`);
        await page.goto(FRONTEND_URL + path, { waitUntil: 'domcontentloaded', timeout: 12000 }).catch(() => {});
        await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
        await page.waitForFunction(() => {
          const skeletons = document.querySelectorAll('.animate-pulse');
          return skeletons.length === 0;
        }, { timeout: 8000 }).catch(() => {});
        await page.waitForTimeout(500);
        await action(page);
        await page.screenshot({
          path: join(outDir, `${name}.png`),
          fullPage: opts.fullPage,
        });
        console.log(` OK`);
      } catch (err) {
        console.log(` FAIL: ${err.message.slice(0, 80)}`);
      }
    }
  }

  // ─── Summary report ──────────────────────────────────────────
  await browser.close();

  console.log('\n=== RAPPORT ===');
  console.log(`Captures OK:     ${results.ok.length}`);
  console.log(`Pages 404:       ${results.notFound.length}`);
  if (results.notFound.length > 0) {
    results.notFound.forEach(p => console.log(`  - ${p.path} (${p.name})`));
  }
  console.log(`Échecs:          ${results.fail.length}`);
  if (results.fail.length > 0) {
    results.fail.forEach(p => console.log(`  - ${p.path}: ${p.error.slice(0, 60)}`));
  }
  console.log(`\nTotal:           ${pages.length} pages`);
  console.log(`Dossier:         ${outDir}`);
  console.log('Done.\n');
})();
