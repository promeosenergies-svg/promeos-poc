const { chromium } = require('playwright');
const path = require('path');
const { mkdirSync } = require('fs');

const BASE = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5173';
const DIR = path.resolve(process.cwd(), 'artifacts', 'audits', 'manual-pages');
mkdirSync(DIR, { recursive: true });

const PAGES = [
  { name: '01-cockpit', path: '/cockpit' },
  { name: '02-patrimoine', path: '/patrimoine' },
  { name: '03-conformite', path: '/conformite' },
  { name: '04-consommations', path: '/consommations' },
  { name: '05-explorer', path: '/consommations/explorer' },
  { name: '06-diagnostic', path: '/diagnostic-conso' },
  { name: '07-monitoring', path: '/monitoring' },
  { name: '08-portfolio-conso', path: '/consommations/portfolio' },
  { name: '09-bill-intel', path: '/bill-intel' },
  { name: '10-billing-timeline', path: '/billing' },
  { name: '11-achat-energie', path: '/achat-energie' },
  { name: '12-assistant-achat', path: '/assistant-achat' },
  { name: '13-renouvellements', path: '/renouvellements' },
  { name: '14-actions', path: '/actions' },
  { name: '15-notifications', path: '/notifications' },
  { name: '16-admin-users', path: '/admin/users' },
  { name: '17-onboarding', path: '/onboarding' },
  { name: '18-marche', path: '/marche' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
  });
  const page = await ctx.newPage();

  // Navigate first to set localStorage
  await page.goto(BASE + '/cockpit', { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {});
  await page.evaluate(() => {
    localStorage.setItem('promeos_demo_mode', 'true');
    localStorage.setItem('promeos_auth', JSON.stringify({
      token: 'demo',
      user: { id: 1, email: 'promeos@promeos.io', role: 'dg_owner', prenom: 'Demo', nom: 'Admin' }
    }));
  });
  await page.reload({ waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2000);

  for (const { name, path } of PAGES) {
    try {
      process.stdout.write(`${name}...`);
      await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 12000 }).catch(() => {});
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: true });
      console.log(' OK');
    } catch (err) {
      console.log(` FAIL: ${err.message.slice(0, 80)}`);
    }
  }

  await browser.close();
  console.log('Done.');
})();
