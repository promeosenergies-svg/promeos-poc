/**
 * PROMEOS — E2E Sprint S2 Conformité simplicité métier (2026-05-28).
 *
 * Couvre la checklist QA des items 8-11 :
 *   8.  /conformite normal = 3 tabs · expert = 4 tabs
 *   9.  /conformite?tab=execution (normal) → redirige /action-center-v4?domain=conformite
 *   10. NextBestAction crée/ouvre action idempotente · CLOSED non ressuscité
 *   11. Golden path : 0 console error · 0 network 4xx/5xx
 *
 * Sprint infra-stabilisation 2026-05-29 — login retiré : auth est posée
 * une fois pour toutes par `auth.setup.spec.js` (project `setup` dans
 * playwright.config.js). Élimine le flake rate-limit observé pré-merge.
 *
 * Pré-requis : backend :8001 + frontend :5173 démarrés + demo data seeded.
 */
import { test, expect } from '@playwright/test';

const TIMEOUT = 15_000;

/** Collecteur d'erreurs console + network 4xx/5xx (golden path). */
function attachHardeningProbes(page) {
  const consoleErrors = [];
  const networkErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(`${msg.text()} @ ${msg.location()?.url || '?'}`);
    }
  });
  page.on('response', (res) => {
    const status = res.status();
    if (status >= 400 && status < 600 && !res.url().includes('/favicon')) {
      networkErrors.push(`HTTP ${status} ${res.url()}`);
    }
  });
  return { consoleErrors, networkErrors };
}

test.describe('S2 — Conformité simplicité métier', () => {
  // Sprint infra-stabilisation 2026-05-29 — plus de beforeEach login :
  // chaque page hérite du storageState produit par auth.setup.spec.js.

  // ── Item 8 — Tabs dynamiques par persona ─────────────────────────

  test('Item 8a · mode normal /conformite : tab Plan d\'exécution ABSENT', async ({ page }) => {
    const probes = attachHardeningProbes(page);
    await page.goto('/conformite');
    // Au moins un tab cockpit doit être visible (la page a chargé).
    await expect(page.locator('text=Obligations').first()).toBeVisible({ timeout: TIMEOUT });
    // Doctrine S2 : « Plan d'exécution » est retiré du strip en mode normal.
    // L'apostrophe peut être Unicode (’) ou ASCII (') selon la source.
    const planTab = page.locator("nav button", { hasText: /Plan d[’']ex[ée]cution/ });
    await expect(planTab).toHaveCount(0);
    // Golden path : pas d'erreur console ni 4xx/5xx hors favicon.
    expect(probes.consoleErrors, `console errors: ${probes.consoleErrors.join(' · ')}`).toEqual([]);
    expect(probes.networkErrors, `network 4xx/5xx: ${probes.networkErrors.join(' · ')}`).toEqual([]);
  });

  test('Item 8b · mode expert /conformite : tab Plan d\'exécution PRESENT', async ({ page }) => {
    // Le toggle expert est porté par useExpertMode — on l'active via le
    // localStorage (clé documentée dans ExpertModeContext) avant de naviguer.
    await page.addInitScript(() => {
      try {
        // STORAGE_KEY = 'promeos_expert' (cf. ExpertModeContext.jsx).
        window.localStorage.setItem('promeos_expert', 'true');
      } catch (_) {}
    });
    await page.goto('/conformite');
    await expect(page.locator('text=Obligations').first()).toBeVisible({ timeout: TIMEOUT });
    const planTab = page.locator("nav button", { hasText: /Plan d[’']ex[ée]cution/ });
    await expect(planTab).toHaveCount(1);
  });

  // ── Item 9 — Redirect deep-link execution en mode normal ─────────

  test('Item 9 · /conformite?tab=execution en mode normal redirige /action-center-v4', async ({
    page,
  }) => {
    await page.goto('/conformite?tab=execution');
    // Le useEffect détecte tab non autorisée + isExpert=false → navigate.
    await page.waitForURL((url) => url.pathname === '/action-center-v4', { timeout: TIMEOUT });
    expect(new URL(page.url()).searchParams.get('domain')).toBe('conformite');
  });

  // ── Item 11 — Golden path /action-center-v4?domain=conformite ────

  test('Item 11 · /action-center-v4?domain=conformite : 0 console error, 0 4xx/5xx', async ({
    page,
  }) => {
    const probes = attachHardeningProbes(page);
    await page.goto('/action-center-v4?domain=conformite');
    // Wait page idle (1 réseau idle + 250 ms supplémentaires).
    await page.waitForLoadState('networkidle', { timeout: TIMEOUT });
    await page.waitForTimeout(250);
    expect(probes.consoleErrors, `console errors: ${probes.consoleErrors.join(' · ')}`).toEqual([]);
    expect(probes.networkErrors, `network 4xx/5xx: ${probes.networkErrors.join(' · ')}`).toEqual([]);
  });
});
