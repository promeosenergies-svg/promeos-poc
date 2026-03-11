import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const DIR = 'c:/Users/amine/promeos-poc/promeos-poc/audit-screenshots';

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
  { name: '19-usages-horaires', path: '/usages-horaires' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
  });

  const page = await context.newPage();

  // Get real JWT token via API, then inject into localStorage
  console.log('Fetching auth token from API...');
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
  const loginResp = await page.evaluate(async () => {
    const res = await fetch('http://localhost:8001/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'promeos@promeos.io', password: 'promeos2024' }),
    });
    return res.json();
  });
  console.log('Got token for:', loginResp.user?.email);
  await page.evaluate((token) => {
    localStorage.setItem('promeos_token', token);
  }, loginResp.access_token);
  // Reload to trigger AuthContext to pick up the token
  await page.goto(BASE + '/cockpit', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);
  console.log('Authenticated, current URL:', page.url());

  for (const { name, path } of PAGES) {
    try {
      console.log(`Capturing ${name} → ${path}`);
      await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 12000 }).catch(() => {});
      await page.waitForTimeout(1500);
      await page.screenshot({
        path: `${DIR}/${name}.png`,
        fullPage: true,
      });
      console.log(`  ✓ ${name}.png`);
    } catch (err) {
      console.error(`  ✗ ${name}: ${err.message}`);
    }
  }

  await browser.close();
  console.log('\nDone. Screenshots saved to:', DIR);
})();
