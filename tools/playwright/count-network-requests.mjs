/**
 * Phase Sprint Retro — comptage requêtes réseau au mount d'une route.
 *
 * Compte total + APIs + endpoints uniques. Login démo automatique.
 * Output : JSON {summary, requests} + log console.
 *
 * Usage :
 *   node tools/playwright/count-network-requests.mjs \
 *     --url=http://localhost:5175/cockpit/strategique \
 *     --output=outputs/network_count_strategique.json
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => a.replace(/^--/, '').split('=')),
);

const PAGE_URL = args.url;
const OUTPUT = args.output;
if (!PAGE_URL || !OUTPUT) {
  console.error('Usage: --url=<url> --output=<path>');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

// Login démo (cohérent avec audit_phase17_all_routes.mjs)
const baseUrl = new URL(PAGE_URL).origin;
await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 8000 });
await page.waitForSelector('input[type=email]', { timeout: 8000 });
await page.fill('input[type=email]', 'promeos@promeos.io');
await page.fill('input[type=password]', 'promeos2024');
await page.click('button[type="submit"]');
await page
  .waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 12000 })
  .catch(() => null);
await page.waitForTimeout(1500);

// Reset compteur — on ne mesure que le mount de la route cible
const requests = [];
page.on('request', (req) => requests.push({ url: req.url(), method: req.method() }));

await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: 25000 }).catch(() => null);
await page
  .waitForFunction(
    () => {
      const main = document.querySelector('main');
      if (!main) return false;
      return (main.innerText || '').length > 120;
    },
    { timeout: 12000 },
  )
  .catch(() => null);
await page.waitForTimeout(2000);

const apiRequests = requests.filter((r) => r.url.includes('/api/'));
const apiEndpoints = [
  ...new Set(apiRequests.map((r) => r.url.replace(/^.*\/api/, '/api').split('?')[0])),
];
const summary = {
  url: PAGE_URL,
  total: requests.length,
  api: apiRequests.length,
  api_endpoints: apiEndpoints,
  api_endpoints_count: apiEndpoints.length,
};

console.log(JSON.stringify(summary, null, 2));
writeFileSync(OUTPUT, JSON.stringify({ summary, requests: apiRequests }, null, 2));
await browser.close();
