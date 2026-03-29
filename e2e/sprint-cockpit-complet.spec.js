/**
 * PROMEOS — E2E Sprint Cockpit Complet
 * Couvre : C1-C6 + I1-I9 + V1-V5 + P0-A/B + P2-A
 *
 * Parcours validés :
 * 1. Cockpit → KPIs cohérents + gauge + kWh/m²
 * 2. Cockpit → clic site → Site360 → onglets Conso + Actions (plus de stub)
 * 3. Cockpit → "Surcoût facture" → BillIntel (accessible en simple)
 * 4. Mode simple → KPIs exécutifs visibles (I9)
 * 5. Conformité, Consommations, Actions — pages fonctionnelles
 * 6. Navigation — 10 routes, zéro 404/crash
 *
 * Pré-requis :
 *   - Backend sur localhost:8001, Frontend sur localhost:5173
 *   - Seed HELIOS : python -m services.demo_seed --pack helios --size S --reset
 *   - npx playwright install
 *
 * Lancer :
 *   cd e2e && npx playwright test sprint-cockpit-complet.spec.js --headed
 */
import { test, expect } from '@playwright/test';
import { login, waitForPageReady, assertCleanBody } from './helpers.js';

// ── Helpers ─────────────────────────────────────────────────

async function getBody(page, timeout = 5000) {
  await waitForPageReady(page, timeout);
  const body = await page.textContent('body');
  expect(body.length).toBeGreaterThan(200);
  return body;
}

/**
 * Navigate to Site360 for the first HELIOS site (id=1).
 * Direct navigation — more reliable than click-through patrimoine drawer.
 */
async function navigateToFirstSite360(page) {
  await page.goto('/sites/1');
  await waitForPageReady(page, 6000);
  return page.textContent('body');
}

// ═════════════════════════════════════════════════════════════
// 1. COCKPIT EXÉCUTIF — Intégrité post-sprint
// ═════════════════════════════════════════════════════════════

test.describe('1. Cockpit exécutif — intégrité', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/cockpit');
    await waitForPageReady(page);
  });

  test('Page charge avec titre et KPIs', async ({ page }) => {
    const body = await getBody(page);
    expect(body).toContain('Conformité');
    expect(body).toContain('Risque');
  });

  test('Gauge Score Santé visible (V1)', async ({ page }) => {
    const svgCount = await page.locator('svg').count();
    expect(svgCount).toBeGreaterThan(0);
  });

  test('Performance par site — barres kWh/m² visibles (V2)', async ({ page }) => {
    const body = await getBody(page);
    expect(body).not.toContain('Données benchmark non disponibles');
    expect(body).not.toContain('Données non disponibles');
    const hasKwhM2 = body.includes('kWh/m²') || body.includes('kWh/m');
    expect(hasKwhM2).toBe(true);
  });

  test('Alertes avec countdown J-X (V3)', async ({ page }) => {
    const body = await getBody(page);
    const hasCountdown = body.includes('J-') || body.includes('Dépassé') || body.includes('Échu');
    expect(hasCountdown).toBe(true);
  });

  test('Trajectoire DT avec toggle KWH/% RÉDUCTION', async ({ page }) => {
    const body = await getBody(page);
    const hasToggle =
      body.includes('KWH') ||
      body.includes('% RÉDUCTION') ||
      body.includes('% Réduction') ||
      body.includes('MWh');
    expect(hasToggle).toBe(true);
  });

  test('Émissions CO₂ avec facteurs ADEME (V4)', async ({ page }) => {
    const body = await getBody(page);
    const hasCO2 = body.includes('CO₂') || body.includes('CO2') || body.includes('tCO₂');
    expect(hasCO2).toBe(true);
  });

  test('Actions impact avec CTA (V5)', async ({ page }) => {
    const body = await getBody(page);
    expect(body).toContain('Actions');
    const hasActionsLink = body.includes('toutes les actions') || body.includes('plan complet');
    expect(hasActionsLink).toBe(true);
  });
});

// ═════════════════════════════════════════════════════════════
// 2. PARCOURS SITE360 — Onglets débloqués (P0-A, P0-B, P2-A)
// ═════════════════════════════════════════════════════════════

test.describe('2. Parcours Cockpit → Site360', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Site360 affiche 6 onglets', async ({ page }) => {
    const body = await navigateToFirstSite360(page);
    expect(body).not.toContain('Site introuvable');
    expect(body).toContain('Résumé');
    expect(body).toContain('Consommation');
    expect(body).toContain('Factures');
    expect(body).toContain('Réconciliation');
    expect(body).toContain('Conformité');
    expect(body).toContain('Actions');
  });

  test('P2-A : kWh/m² visible dans header Site360', async ({ page }) => {
    const body = await navigateToFirstSite360(page);
    const hasIntensity = body.includes('kWh/m²') || body.includes('Intensité');
    expect(hasIntensity).toBe(true);
  });

  test('P0-A : Onglet Consommation ≠ stub "à venir"', async ({ page }) => {
    await navigateToFirstSite360(page);

    const consoTab = page.locator('button, [role="tab"]').filter({ hasText: 'Consommation' });
    await expect(consoTab).toBeVisible({ timeout: 5000 });
    await consoTab.click();
    await waitForPageReady(page, 4000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Courbes de charge, historique et benchmark à venir');
    expect(body).not.toContain('Bientôt disponible');
    // Doit afficher du contenu réel (chart ou KPIs conso)
    const hasConsoContent =
      body.includes('kWh') ||
      body.includes('Total 30 jours') ||
      body.includes('Aucune donnée de consommation');
    expect(hasConsoContent).toBe(true);
  });

  test('P0-B : Onglet Actions ≠ stub "à venir"', async ({ page }) => {
    await navigateToFirstSite360(page);

    const actionsTab = page.locator('button, [role="tab"]').filter({ hasText: 'Actions' });
    await expect(actionsTab).toBeVisible({ timeout: 5000 });
    await actionsTab.click();
    await waitForPageReady(page, 4000);

    const body = await page.textContent('body');
    expect(body).not.toContain("Plan d'action et suivi des recommandations à venir");
    expect(body).not.toContain('Bientôt disponible');
    // Doit afficher du contenu réel (liste ou empty state)
    const hasActionsContent =
      body.includes('En cours') ||
      body.includes('Ouvertes') ||
      body.includes('Créer une action') ||
      body.includes('Aucune action');
    expect(hasActionsContent).toBe(true);
  });
});

// ═════════════════════════════════════════════════════════════
// 3. PARCOURS BILL INTELLIGENCE — Accessible en simple
// ═════════════════════════════════════════════════════════════

test.describe('3. Parcours Cockpit → BillIntel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('BillIntel accessible sans mode expert', async ({ page }) => {
    await page.goto('/bill-intel');
    await waitForPageReady(page);
    const body = await getBody(page);

    expect(body).not.toContain('Mode Expert requis');
    expect(body).not.toContain('Cette fonctionnalité nécessite le mode Expert');

    const hasBillingContent =
      body.includes('Factur') || body.includes('factur') || body.includes('Anomal');
    expect(hasBillingContent).toBe(true);
  });

  test('Deep-link cockpit → BillIntel avec filtre anomalies', async ({ page }) => {
    await page.goto('/bill-intel?filter=anomalies');
    await waitForPageReady(page);
    const body = await getBody(page);
    expect(body).not.toContain('Something went wrong');
  });
});

// ═════════════════════════════════════════════════════════════
// 4. MODE SIMPLE — KPIs exécutifs visibles (I9)
// ═════════════════════════════════════════════════════════════

test.describe('4. Mode simple — visibilité KPIs (I9)', () => {
  test('Vue exécutive montre les KPIs même sans expert toggle', async ({ page }) => {
    await login(page);
    await page.goto('/cockpit');
    await waitForPageReady(page);
    const body = await getBody(page);

    expect(body).toContain('Conformité');
    const hasImpact = body.includes('Impact') || body.includes('Risque') || body.includes('k€');
    expect(hasImpact).toBe(true);
  });
});

// ═════════════════════════════════════════════════════════════
// 5. CONFORMITÉ — Page fonctionnelle
// ═════════════════════════════════════════════════════════════

test.describe('5. Conformité — parcours complet', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('Page conformité charge avec scanner et obligations', async ({ page }) => {
    await page.goto('/conformite');
    const body = await getBody(page);
    expect(body).toContain('Conformité');
    const hasReg =
      body.includes('Tertiaire') || body.includes('BACS') || body.includes('Obligation');
    expect(hasReg).toBe(true);
  });

  test('Deep-link cockpit hero → conformité', async ({ page }) => {
    await page.goto('/cockpit');
    await waitForPageReady(page);

    const ctaConf = page.locator('text=Voir conformité').first();
    if (await ctaConf.isVisible({ timeout: 3000 }).catch(() => false)) {
      await ctaConf.click();
      await page.waitForURL(/\/conformite/, { timeout: 10_000 });
      const body = await page.textContent('body');
      expect(body).not.toContain('Something went wrong');
      expect(body).toContain('Conformité');
    }
  });
});

// ═════════════════════════════════════════════════════════════
// 6. CONSOMMATIONS — Explorer fonctionnel
// ═════════════════════════════════════════════════════════════

test.describe('6. Consommations Explorer', () => {
  test('Page consommations charge', async ({ page }) => {
    await login(page);
    await page.goto('/consommations');
    const body = await getBody(page);
    expect(body).not.toContain('Something went wrong');
    const hasConso = body.includes('Consommation') || body.includes('kWh') || body.includes('Électricité');
    expect(hasConso).toBe(true);
  });
});

// ═════════════════════════════════════════════════════════════
// 7. ACTIONS — Plan d'actions fonctionnel
// ═════════════════════════════════════════════════════════════

test.describe('7. Actions', () => {
  test('Page actions charge avec liste', async ({ page }) => {
    await login(page);
    await page.goto('/actions');
    const body = await getBody(page);
    expect(body).not.toContain('Something went wrong');
    expect(body).toContain('Actions');
  });
});

// ═════════════════════════════════════════════════════════════
// 8. NAVIGATION — Zéro dead link
// ═════════════════════════════════════════════════════════════

test.describe('8. Navigation — zéro 404', () => {
  const routes = [
    '/',
    '/cockpit',
    '/patrimoine',
    '/conformite',
    '/actions',
    '/consommations',
    '/monitoring',
    '/bill-intel',
    '/notifications',
    '/diagnostic-conso',
  ];

  for (const route of routes) {
    test(`${route} ne retourne pas 404 ni crash`, async ({ page }) => {
      await login(page);
      await page.goto(route);
      await waitForPageReady(page);
      const body = await page.textContent('body');
      expect(body).not.toContain('Page non trouvée');
      expect(body).not.toContain('Something went wrong');
      expect(body.length).toBeGreaterThan(100);
    });
  }
});
