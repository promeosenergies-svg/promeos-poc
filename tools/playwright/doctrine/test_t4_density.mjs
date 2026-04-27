/**
 * Test doctrinal T4 — Densité éditoriale §4
 *
 * Doctrine §3 P4 : « pas plus de 200px de hauteur sans information utile ».
 * Doctrine §6.1 anti-pattern : « card "Aucune action" pleine largeur 600px ».
 *
 * Mécanique :
 * 1. Pour chaque page Sol (refonte sol2 port 5175), parcourir le DOM
 * 2. Mesurer les zones contiguës sans contenu utile (vide visuel,
 *    skeleton, "loading...", empty state non-densifié)
 * 3. Émettre violation si zone >200px
 *
 * Heuristique densité utile : un élément contient du contenu utile s'il a
 * du texte non-trivial (>20 caractères significatifs), un graphique, un
 * input actionnable, ou une icône+label clair.
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const FE = process.env.FE_URL || 'http://localhost:5175';
const VIEWPORT = { width: 1440, height: 900 };
const DENSITY_THRESHOLD_PX = 200;
const OUT_DIR = path.join(
  '/Users/amine/projects/promeos-poc/tools/playwright/doctrine/results',
  new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19),
);

const PAGES = [
  { route: '/', name: 'tableau_de_bord' },
  { route: '/cockpit?angle=comex', name: 'cockpit_comex' },
  { route: '/patrimoine', name: 'patrimoine' },
  { route: '/conformite', name: 'conformite' },
  { route: '/bill-intel', name: 'bill_intel' },
  // Sprint 1.6+ : ajouter Achat/Monitoring/Diagnostic/Anomalies/Flex
];

async function login(page) {
  await page.goto(FE + '/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
  const tok = await page.evaluate(async () => {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
    });
    return (await r.json()).access_token;
  });
  await page.evaluate((t) => {
    localStorage.setItem('promeos_token', t);
    localStorage.setItem('promeos_onboarding_done', 'true');
    localStorage.setItem('promeos_spotlight_seen', '1');
  }, tok);
}

async function measureEmptyZones(page) {
  // Heuristique : pour chaque section/div haute, vérifier la densité informationnelle
  return page.evaluate((threshold) => {
    const violations = [];
    // Sélectionne les containers visuels significatifs
    const containers = document.querySelectorAll('main section, main > div, main article, [data-testid]');
    containers.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.height < threshold) return; // OK, pas une zone à risque
      // Mesure de densité : ratio texte/hauteur + présence chart/input/icon utile
      const textLen = (el.textContent || '').replace(/\s+/g, ' ').trim().length;
      const hasChart = el.querySelector('svg, canvas, [class*="recharts"]') !== null;
      const hasInteractive = el.querySelector('button, a, input, select') !== null;
      const looksEmpty =
        /aucun|aucune|empty|n\/a|chargement|loading\.\.\./i.test(el.textContent || '') &&
        textLen < 80;
      // Densité utile = texte >= hauteur/4 OU chart OU interactive non-empty
      const isEmpty = looksEmpty || (textLen < rect.height / 4 && !hasChart && !hasInteractive);
      if (isEmpty) {
        violations.push({
          tag: el.tagName.toLowerCase(),
          testid: el.getAttribute('data-testid') || null,
          height: Math.round(rect.height),
          textLen,
          hasChart,
          hasInteractive,
          excerpt: (el.textContent || '').slice(0, 100).replace(/\s+/g, ' ').trim(),
        });
      }
    });
    return violations;
  }, DENSITY_THRESHOLD_PX);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: VIEWPORT, locale: 'fr-FR' });
  const page = await ctx.newPage();

  await login(page);

  const results = [];
  for (const p of PAGES) {
    await page.goto(FE + p.route, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
    await page.waitForTimeout(2000); // stagger reveal complet

    const violations = await measureEmptyZones(page);
    results.push({ page: p.name, route: p.route, violations });

    // Screenshot pour audit visuel
    await page.screenshot({
      path: path.join(OUT_DIR, `${p.name}.png`),
      fullPage: true,
    });
  }

  await browser.close();

  // Output JSON + markdown
  const totalViolations = results.reduce((s, r) => s + r.violations.length, 0);
  const verdict = totalViolations === 0 ? 'PASS' : 'FAIL';

  fs.writeFileSync(path.join(OUT_DIR, 't4_density.json'), JSON.stringify(results, null, 2));

  let md = `# Test doctrinal T4 — Densité §4\n\n`;
  md += `**Verdict** : ${verdict} (${totalViolations} violations sur ${PAGES.length} pages)\n`;
  md += `**Seuil** : ${DENSITY_THRESHOLD_PX}px de hauteur sans info utile = violation\n`;
  md += `**Viewport** : ${VIEWPORT.width}×${VIEWPORT.height}\n\n`;
  for (const r of results) {
    md += `## ${r.page} (${r.route})\n`;
    if (r.violations.length === 0) {
      md += `✅ Aucune zone vide >${DENSITY_THRESHOLD_PX}px\n\n`;
    } else {
      md += `❌ ${r.violations.length} zone(s) vide(s) :\n\n`;
      for (const v of r.violations) {
        md += `- \`${v.tag}\`${v.testid ? `[data-testid="${v.testid}"]` : ''} — ${v.height}px, texte ${v.textLen}c · "${v.excerpt}"\n`;
      }
      md += '\n';
    }
  }
  fs.writeFileSync(path.join(OUT_DIR, 't4_density.md'), md);

  console.log(`T4 ${verdict} — ${totalViolations} violations · output : ${OUT_DIR}`);
  process.exit(verdict === 'PASS' ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
