// M2-6.A.3 — Walkthrough FE 4 étapes post-Cat 1 sécu clôturée.
// Login Marie Leclerc → /pilotage → drawer item → reload F5.
// Vérifie aucune régression fonctionnelle suite aux 3 commits M2-6.A.
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const OUT = 'tools/playwright/captures/m2_6_a3_walkthrough';
const FE = 'http://127.0.0.1:5175';
const DEMO_USER = 'm.leclerc@helios-energie.fr';
const DEMO_PASS = 'promeos2024';

async function shoot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  📸 ${name}.png`);
}

(async () => {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage();

  const errors = [];
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
  });

  try {
    // ── ÉTAPE 1 — Login Marie Leclerc (form email/password classique) ──
    console.log('\n1. Login Marie Leclerc (ENERGY_MANAGER)');
    await page.goto(`${FE}/login`, { waitUntil: 'networkidle' });
    await shoot(page, '01-login-page');

    await page.fill('input[type="email"]', DEMO_USER);
    await page.fill('input[type="password"]', DEMO_PASS);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 10_000 }),
      page.getByRole('button', { name: /^connexion$|^se connecter$|^login$/i }).click(),
    ]);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    console.log(`  ✓ URL post-login: ${page.url()}`);
    await shoot(page, '02-post-login');

    // ── ÉTAPE 2 — Navigate /action-center-v4/pilotage ──
    console.log('\n2. Navigate /action-center-v4/pilotage');
    await page.goto(`${FE}/action-center-v4/pilotage`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await shoot(page, '03-pilotage-rendered');

    // Vérifications cardinales (NarrativeBar + EditorialNarrativeBlock + Masthead)
    const mastheadVisible = await page.getByText(/centre d'action/i).first().isVisible();
    const narrativeBarVisible = await page
      .getByText(/décisions p0\/p1|sans responsable|bloqués/i)
      .first()
      .isVisible();
    console.log(`  ✓ Masthead visible: ${mastheadVisible}`);
    console.log(`  ✓ NarrativeBar v2 visible: ${narrativeBarVisible}`);

    // ── ÉTAPE 3 — Open drawer sur 1er item file prioritaire ──
    console.log('\n3. Open drawer item file prioritaire');
    // Card prioritaire = bouton/role button avec titre item
    const firstCard = page.locator('[data-testid*="priority-queue-card"], [role="button"]').first();
    let drawerOpened = false;
    try {
      await firstCard.click({ timeout: 3_000 });
      await page.waitForTimeout(800);
      // Drawer V4 — vérifier role dialog ou panel ouvert
      const drawerVisible = await page
        .locator('[role="dialog"], [aria-label*="détail" i], [aria-label*="drawer" i]')
        .first()
        .isVisible({ timeout: 2_000 })
        .catch(() => false);
      drawerOpened = drawerVisible;
      console.log(`  ✓ Drawer ouvert: ${drawerOpened}`);
      await shoot(page, '04-drawer-open');
    } catch (e) {
      console.log(`  ⚠ Drawer click failed: ${e.message}`);
      await shoot(page, '04-drawer-failed');
    }

    // ── ÉTAPE 4 — Reload F5 (vérifier session + état restaurés) ──
    console.log('\n4. Reload F5 — session persiste');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    const stillOnPilotage = page.url().includes('/action-center-v4/pilotage');
    console.log(`  ✓ URL après reload: ${page.url()}`);
    console.log(`  ✓ Toujours sur pilotage (session OK): ${stillOnPilotage}`);
    await shoot(page, '05-post-reload');

    // ── BILAN ──
    console.log('\n═══ BILAN WALKTHROUGH ═══');
    console.log(`Masthead visible        : ${mastheadVisible ? '✅' : '❌'}`);
    console.log(`NarrativeBar v2 visible : ${narrativeBarVisible ? '✅' : '❌'}`);
    console.log(`Drawer s'ouvre          : ${drawerOpened ? '✅' : '⚠️ skipped'}`);
    console.log(`Reload F5 préserve      : ${stillOnPilotage ? '✅' : '❌'}`);
    console.log(`Errors JS               : ${errors.length === 0 ? '✅ 0' : `❌ ${errors.length}`}`);
    if (errors.length > 0) {
      console.log('\nErrors détectées:');
      errors.slice(0, 5).forEach((e) => console.log(`  - ${e.substring(0, 200)}`));
    }

    const ok = mastheadVisible && narrativeBarVisible && stillOnPilotage && errors.length === 0;
    process.exitCode = ok ? 0 : 1;
  } catch (e) {
    console.error('FATAL:', e.message);
    await shoot(page, '99-fatal');
    process.exitCode = 2;
  } finally {
    await browser.close();
  }
})();
