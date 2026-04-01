/**
 * Audit Site360 — Screenshots conformité maquette
 * Mode lecture seule : aucune modification de production
 */
import { test } from '@playwright/test';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIR = path.join(__dirname, '..', 'screenshots', 'audit-site360');
const SITE_URL = '/sites/1';
const BACKEND = 'http://127.0.0.1:8001';

async function login(page) {
  const res = await page.request.post(`${BACKEND}/api/auth/login`, {
    data: { email: 'promeos@promeos.io', password: 'promeos2024' },
  });
  if (res.ok()) {
    const data = await res.json();
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((token) => {
      localStorage.setItem('promeos_token', token);
    }, data.access_token);
  }
}

test.describe('Audit Site360 — Screenshots conformité', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('01 — Resume haut', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(4000);
    await page.screenshot({ path: path.join(DIR, '01-resume-haut.png'), fullPage: false });
  });

  test('02 — Resume scroll bas', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(4000);
    await page.evaluate(() => window.scrollTo(0, 800));
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(DIR, '02-resume-bas.png'), fullPage: false });
  });

  test('03 — Resume fullpage', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(4000);
    await page.screenshot({ path: path.join(DIR, '03-resume-fullpage.png'), fullPage: true });
  });

  test('04 — Onglet Consommation', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(3000);
    await page.locator('text=Consommation').first().click().catch(() => {});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(DIR, '04-conso.png'), fullPage: true });
  });

  test('05 — Onglet Actions', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(3000);
    await page.locator('text=Actions').last().click().catch(() => {});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(DIR, '05-actions.png'), fullPage: true });
  });

  test('06 — Onglet Factures', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(3000);
    await page.locator('text=Factures').first().click().catch(() => {});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(DIR, '06-factures.png'), fullPage: true });
  });

  test('07 — Onglet Conformité', async ({ page }) => {
    await page.goto(SITE_URL);
    await page.waitForTimeout(3000);
    await page.locator('text=Conformit').first().click().catch(() => {});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(DIR, '07-conformite.png'), fullPage: true });
  });

  test('08 — Redirect /sites', async ({ page }) => {
    await page.goto('/sites');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(DIR, '08-redirect-sites.png'), fullPage: false });
  });
});
