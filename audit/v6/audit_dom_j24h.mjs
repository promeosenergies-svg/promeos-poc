/**
 * Audit J+24h — DOM presence checker for / and /cockpit
 * Checks textual markers and DOM indicators from commit 1ecc04eb refonte.
 */
import pkg from '/opt/node22/lib/node_modules/playwright/index.js';
const { chromium } = pkg;
import { writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FE_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const BE_URL = process.env.PROMEOS_BACKEND_URL || 'http://localhost:8001';
const OUT_DIR = join(__dirname);

const results = {
  timestamp: new Date().toISOString(),
  fe_url: FE_URL,
  be_url: BE_URL,
  home: { markers: {}, dom: {}, console_errors: [], api_errors: [], screenshot: null },
  cockpit: { markers: {}, dom: {}, console_errors: [], api_errors: [], screenshot: null },
};

async function loginAndGetToken() {
  const r = await fetch(`${BE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
  });
  if (!r.ok) throw new Error(`Login failed: ${r.status} ${await r.text()}`);
  const data = await r.json();
  return data.access_token;
}

async function auditPage(page, url, config) {
  const consoleErrors = [];
  const apiErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('response', (resp) => {
    const status = resp.status();
    if (status >= 400 && resp.url().includes('/api/')) {
      apiErrors.push(`${status} ${resp.url()}`);
    }
  });

  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);

  const bodyText = await page.evaluate(() => document.body.innerText);

  // Text markers
  const markers = {};
  for (const [key, phrase] of Object.entries(config.textMarkers)) {
    markers[key] = bodyText.toLowerCase().includes(phrase.toLowerCase());
  }

  // DOM indicators
  const dom = {};
  for (const [key, selector] of Object.entries(config.domSelectors)) {
    const count = await page.locator(selector).count();
    dom[key] = { count, ok: count >= (config.domMinCounts[key] || 1) };
  }

  return { markers, dom, console_errors: consoleErrors, api_errors: apiErrors };
}

const HOME_CONFIG = {
  textMarkers: {
    'vos_actions_du_jour': 'vos actions du jour',
    'sol_propose': 'Sol propose',
    'a_traiter_aujourdhui': 'À traiter aujourd\'hui',
    'a_surveiller': 'À surveiller',
    'activite_7_jours': 'Activité 7 derniers jours',
    'heures_pleines_creuses': 'Heures pleines',
    'profil_horaire': 'Profil horaire',
    'acces_rapide_modules': 'Accès rapide',
  },
  domSelectors: {
    'recharts_area': '.recharts-area',
    'recharts_bar': '.recharts-bar',
    'recharts_reference_line': '.recharts-reference-line',
    'recharts_reference_area': '.recharts-reference-area',
    'recharts_reference_dot': '.recharts-reference-dot',
  },
  domMinCounts: {
    'recharts_area': 1,
    'recharts_bar': 1,
    'recharts_reference_line': 2,
    'recharts_reference_area': 3,
    'recharts_reference_dot': 1,
  },
};

const COCKPIT_CONFIG = {
  textMarkers: {
    'semaine_en_briefing': 'votre semaine en briefing',
    'briefing_exec': 'Briefing exécutif',
    'trajectoire_dt': 'Trajectoire Décret Tertiaire',
    'performance_sites': 'Performance',
    'vecteurs': 'Vecteur',
    'evenements_recents': 'Événements récents',
    'rapport_comex': 'Rapport COMEX',
    'co2_empreinte': 'tCO₂',
  },
  domSelectors: {
    'kpi_facture': 'text=Facture',
    'kpi_conformite': 'text=Conformité',
    'kpi_consommation': 'text=Consommation',
    'kpi_co2': 'text=CO₂',
  },
  domMinCounts: {
    'kpi_facture': 1,
    'kpi_conformite': 1,
    'kpi_consommation': 1,
    'kpi_co2': 1,
  },
};

(async () => {
  let token;
  try {
    token = await loginAndGetToken();
    console.log('✓ Auth OK — token obtained');
  } catch (e) {
    console.error('✗ Auth failed:', e.message);
    results.auth_error = e.message;
    writeFileSync(join(OUT_DIR, 'dom_audit_result.json'), JSON.stringify(results, null, 2));
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });

  // Inject token into localStorage via page
  const homePage = await context.newPage();
  await homePage.goto(`${FE_URL}`, { timeout: 15000 });
  await homePage.evaluate((t) => {
    localStorage.setItem('promeos_token', t);
    localStorage.setItem('token', t);
  }, token);

  // Audit /
  console.log('Auditing / (CommandCenter)...');
  try {
    await homePage.reload({ waitUntil: 'networkidle' });
    await homePage.waitForTimeout(3000);
    const homeResult = await auditPage(homePage, `${FE_URL}/`, HOME_CONFIG);
    Object.assign(results.home, homeResult);
    const screenshotPath = join(OUT_DIR, 'screenshot_home_1440.png');
    await homePage.screenshot({ path: screenshotPath, fullPage: true });
    results.home.screenshot = screenshotPath;
    console.log('  markers:', Object.entries(homeResult.markers).map(([k,v]) => `${v?'✅':'❌'} ${k}`).join(', '));
  } catch (e) {
    results.home.error = e.message;
    console.error('  ERROR on /:', e.message);
  }

  // Audit /cockpit
  console.log('Auditing /cockpit...');
  const cockpitPage = await context.newPage();
  try {
    await cockpitPage.goto(`${FE_URL}/cockpit`, { waitUntil: 'networkidle', timeout: 30000 });
    await cockpitPage.waitForTimeout(3000);
    const cockpitResult = await auditPage(cockpitPage, `${FE_URL}/cockpit`, COCKPIT_CONFIG);
    Object.assign(results.cockpit, cockpitResult);
    const screenshotPath = join(OUT_DIR, 'screenshot_cockpit_1440.png');
    await cockpitPage.screenshot({ path: screenshotPath, fullPage: true });
    results.cockpit.screenshot = screenshotPath;
    console.log('  markers:', Object.entries(cockpitResult.markers).map(([k,v]) => `${v?'✅':'❌'} ${k}`).join(', '));
  } catch (e) {
    results.cockpit.error = e.message;
    console.error('  ERROR on /cockpit:', e.message);
  }

  await browser.close();
  writeFileSync(join(OUT_DIR, 'dom_audit_result.json'), JSON.stringify(results, null, 2));
  console.log('✓ Results saved to', join(OUT_DIR, 'dom_audit_result.json'));
})();
