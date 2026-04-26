/**
 * Test doctrinal T7 — Transformation acronymes §10
 *
 * Doctrine §3 P10 : « transformer la complexité en simplicité »
 * Doctrine §6.3 anti-pattern : « acronymes bruts dans les titres ».
 *
 * Mécanique :
 * 1. Pour chaque page Sol rendue, scanner h1/h2/title/kicker
 * 2. Détecter acronymes nus de la liste interdite (DT/BACS/APER/...)
 * 3. Whitelist : "ACRONYM — narrative", "ACRONYM (Forme longue)"
 *
 * Liste interdite alignée avec test_doctrine_sol_source_guards.py
 * (cohérence backend/frontend tests).
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const FE = process.env.FE_URL || 'http://localhost:5175';
const VIEWPORT = { width: 1440, height: 900 };
const OUT_DIR = path.join(
  '/Users/amine/projects/promeos-poc/tools/playwright/doctrine/results',
  new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19),
);

const PAGES = [
  { route: '/cockpit', name: 'cockpit' },
  { route: '/', name: 'tableau_de_bord' },
];

const RAW_ACRONYMS = [
  'DT',
  'BACS',
  'APER',
  'OPERAT',
  'TURPE 7',
  'TURPE7',
  'CTA',
  'NEBCO',
  'ARENH',
  'VNU',
  'EUI',
  'DJU',
  'CUSUM',
  'TICGN',
  'aFRR',
  'AOFD',
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
  }, tok);
}

function isWhitelisted(text, acronym) {
  // Whitelist : "ACRONYM — narrative" ou "ACRONYM - narrative" ou "ACRONYM (Forme longue)"
  const escaped = acronym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const wl = [
    new RegExp(`\\b${escaped}\\s*[—–-]\\s*\\w`, 'i'),
    new RegExp(`\\b${escaped}\\s*\\(`, 'i'),
  ];
  return wl.some((re) => re.test(text));
}

function findRawAcronymsIn(text) {
  if (!text) return [];
  const found = [];
  for (const acr of RAW_ACRONYMS) {
    const escaped = acr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`\\b${escaped}\\b`);
    if (re.test(text) && !isWhitelisted(text, acr)) {
      found.push(acr);
    }
  }
  return found;
}

async function scanPage(page) {
  return page.evaluate(() => {
    const titleSelectors = [
      'h1',
      'h2',
      '[data-testid*="title"]',
      '[class*="kicker"]',
      '[class*="page-title"]',
    ];
    const out = [];
    titleSelectors.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => {
        const text = (el.textContent || '').trim();
        if (text) {
          out.push({ selector: sel, tag: el.tagName.toLowerCase(), text: text.slice(0, 200) });
        }
      });
    });
    return out;
  });
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
    await page.waitForTimeout(1500);

    const titles = await scanPage(page);
    const violations = [];
    for (const t of titles) {
      const found = findRawAcronymsIn(t.text);
      if (found.length > 0) {
        violations.push({ ...t, acronyms: found });
      }
    }
    results.push({ page: p.name, route: p.route, titlesScanned: titles.length, violations });
  }
  await browser.close();

  const totalViolations = results.reduce((s, r) => s + r.violations.length, 0);
  const verdict = totalViolations === 0 ? 'PASS' : 'FAIL';

  fs.writeFileSync(path.join(OUT_DIR, 't7_acronyms.json'), JSON.stringify(results, null, 2));

  let md = `# Test doctrinal T7 — Transformation acronymes §10\n\n`;
  md += `**Verdict** : ${verdict} (${totalViolations} violations sur ${PAGES.length} pages)\n`;
  md += `**Acronymes interdits nus** : ${RAW_ACRONYMS.join(', ')}\n`;
  md += `**Whitelist** : "DT — trajectoire 2030", "DT (Décret Tertiaire)"\n\n`;
  for (const r of results) {
    md += `## ${r.page} (${r.route})\n`;
    md += `Titres scannés : ${r.titlesScanned}\n\n`;
    if (r.violations.length === 0) {
      md += `✅ Aucun acronyme brut détecté\n\n`;
    } else {
      md += `❌ ${r.violations.length} violation(s) :\n\n`;
      for (const v of r.violations) {
        md += `- \`${v.tag}\` (${v.selector}) acronymes [${v.acronyms.join(', ')}] dans : "${v.text}"\n`;
      }
      md += '\n';
    }
  }
  fs.writeFileSync(path.join(OUT_DIR, 't7_acronyms.md'), md);

  console.log(`T7 ${verdict} — ${totalViolations} violations · output : ${OUT_DIR}`);
  process.exit(verdict === 'PASS' ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
