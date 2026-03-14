/**
 * Playwright Premium Pass — Board-ready validation
 * Parcours: Cockpit → Conformité → Anomalies → Achat → Actions → Détail action
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const DIR = 'playwright-screenshots/premium-pass';
mkdirSync(DIR, { recursive: true });

const BASE = 'http://localhost:5173';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Login
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], input[name="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"], input[name="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  async function shot(name, url, opts = {}) {
    if (url) await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
    if (opts.wait) await page.waitForTimeout(opts.wait);
    if (opts.click) {
      try { await page.click(opts.click, { timeout: 3000 }); await page.waitForTimeout(800); } catch {}
    }
    await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: opts.fullPage || false });
    console.log(`✓ ${name}`);
  }

  // 1. Cockpit — CTA "Créer une action", pas de jargon technique
  await shot('01-cockpit', '/cockpit');

  // 2. Conformité — CTA harmonisé
  await shot('02-conformite', '/conformite');

  // 3. Anomalies — CTA harmonisé
  await shot('03-anomalies', '/anomalies');

  // 4. Achat — CTA harmonisé
  await shot('04-achat', '/achat-energie');

  // 5. Actions — CTA + empty states + badges
  await shot('05-actions', '/actions');

  // 6. Détail action — badge palette
  await shot('06-action-detail', '/actions', {
    wait: 1000,
    click: 'tr[data-testid^="action-row-"]'
  });

  // 7. Bill Intel — badge colors -700
  await shot('07-bill-intel', '/bill-intel');

  // 8. Monitoring — CTA
  await shot('08-monitoring', '/monitoring');

  // 9. Notifications — microcopy
  await shot('09-notifications', '/notifications');

  await browser.close();
  console.log(`\n✅ Premium Pass screenshots saved to ${DIR}/`);
})();
