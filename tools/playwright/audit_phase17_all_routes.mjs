/**
 * Phase 17 — Audit complet : capture toutes les routes principales user-facing.
 *
 * 16 routes principales sidebar Sol (les pages réellement visibles par les
 * personas Marc/Marie/Jean-Marc/Sophie/Antoine).
 *
 * Output : tools/playwright/captures/phase17_all_routes/<route_slug>.png
 *          + tools/playwright/captures/phase17_all_routes/audit_manifest.json
 *          (chaque route → URL + status code + screenshot path + texts visibles)
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const FRONT = 'http://localhost:5175';
const OUT = 'tools/playwright/captures/phase17_all_routes';
mkdirSync(OUT, { recursive: true });

const ROUTES = [
  { path: '/cockpit/strategique', label: 'Vue exécutive (Décision CFO 3min)' },
  { path: '/cockpit/jour', label: 'Tableau de bord (Pilotage EM 30s)' },
  { path: '/conformite', label: 'Conformité' },
  { path: '/conformite/tertiaire', label: 'Décret Tertiaire' },
  { path: '/conformite/aper', label: 'Solarisation APER' },
  { path: '/consommations', label: 'Consommations' },
  { path: '/monitoring', label: 'Performance énergétique' },
  { path: '/usages', label: 'Usages énergétiques' },
  { path: '/diagnostic-conso', label: 'Diagnostic conso' },
  { path: '/patrimoine', label: 'Sites & bâtiments' },
  { path: '/contrats', label: 'Contrats' },
  { path: '/achat-energie', label: 'Achat énergie' },
  { path: '/anomalies', label: 'Centre d\'actions' },
  { path: '/flex', label: 'Flex Intelligence' },
  { path: '/bill-intel', label: 'Bill intel' },
  { path: '/billing', label: 'Facturation' },
];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

// Login démo
// Phase 20.bis.A : `networkidle` ne se résout jamais en dev Vite (HMR)
// → timeout 30s. Désormais `domcontentloaded` + petit délai post-mount.
await page.goto(`${FRONT}/login`, { waitUntil: 'domcontentloaded', timeout: 8000 });
await page.waitForTimeout(800);
const emailField = await page.$('input[type=email]');
if (emailField) {
  await page.fill('input[type=email]', 'promeos@promeos.io');
  await page.fill('input[type=password]', 'promeos2024');
  await page.press('input[type=password]', 'Enter');
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 8000 }).catch(() => {});
}

const manifest = [];

for (const r of ROUTES) {
  const slug = r.path.replace(/\//g, '_').replace(/^_/, '') || 'root';
  console.log(`→ ${r.path}`);
  const t0 = Date.now();
  try {
    // Phase 19.C (audit P17 P1) : `networkidle` était incompatible avec
    // backend lent (14/16 timeouts 15s).
    // Phase 20.bis.A (audit triple pre-Phase 21) : `domcontentloaded` seul
    // capturait avant hydratation React → 13/16 PNG identiques (page login)
    // + manifests vides. Désormais : domcontentloaded rapide + waitForFunction
    // qui attend que `<main>` ait du contenu réel (>200 chars) ou un timeout
    // 8s. Capture authentique de la page hydratée.
    const resp = await page.goto(`${FRONT}${r.path}`, {
      waitUntil: 'domcontentloaded',
      timeout: 12000,
    });
    // Attente hydratation React : main rempli OU timeout.
    await page
      .waitForFunction(
        () => {
          const main = document.querySelector('main');
          if (!main) return false;
          const text = main.innerText || '';
          return text.length > 200;
        },
        { timeout: 8000 },
      )
      .catch(() => {
        /* timeout silencieux : capture quand même l'état dégradé */
      });
    await page.waitForTimeout(800);
    const tElapsed = Date.now() - t0;

    // Capture above-the-fold + texts visibles
    const shotPath = `${OUT}/${slug}.png`;
    await page.screenshot({ path: shotPath, fullPage: false });

    // Capture des textes : labels mono uppercase + KPI values + titres
    const extracted = await page.evaluate(() => {
      const titles = Array.from(document.querySelectorAll('h1, h2, h3'))
        .map((h) => h.innerText?.trim())
        .filter(Boolean)
        .slice(0, 20);
      // Repérer les acronymes potentiels (mots ALL CAPS de 2-6 chars)
      const bodyText = document.body.innerText || '';
      const acronymCandidates = [
        ...new Set(bodyText.match(/\b[A-Z]{2,6}(?:\s?\d+)?\b/g) || []),
      ].slice(0, 50);
      // Repérer les valeurs €/MWh
      const moneyValues = [...new Set(bodyText.match(/[\d,.]+\s?(?:k€|M€|€)\b/g) || [])].slice(0, 30);
      const energyValues = [...new Set(bodyText.match(/[\d,.]+\s?(?:MWh|kWh|GWh|kW|MW)\b/g) || [])].slice(0, 30);
      const co2Values = [...new Set(bodyText.match(/[\d,.]+\s?t(?:CO2|CO₂)?\/an\b/gi) || [])].slice(0, 10);
      // Sources / sources mentionnées
      const sourceMentions = [...new Set(bodyText.match(/(?:Source|Décret|CRE|ADEME|Enedis|GRDF|TURPE|REGOPS|EMS)[^.\n]{0,80}/gi) || [])].slice(0, 20);
      return {
        titles,
        acronymCandidates,
        moneyValues,
        energyValues,
        co2Values,
        sourceMentions,
      };
    });

    manifest.push({
      path: r.path,
      label: r.label,
      slug,
      status: resp?.status() || null,
      latency_ms: tElapsed,
      url_final: page.url(),
      screenshot: shotPath,
      ...extracted,
    });
    console.log(`  ✓ status=${resp?.status()} ${tElapsed}ms titles=${extracted.titles.length} acronymes=${extracted.acronymCandidates.length}`);
  } catch (e) {
    console.log(`  ✗ ${e.message}`);
    manifest.push({ path: r.path, label: r.label, slug, error: e.message });
  }
}

writeFileSync(`${OUT}/audit_manifest.json`, JSON.stringify(manifest, null, 2));
console.log(`\n✓ Manifest sauvegardé : ${OUT}/audit_manifest.json (${manifest.length} routes)`);
await browser.close();
