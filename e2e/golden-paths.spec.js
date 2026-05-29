/**
 * PROMEOS — Golden paths stables (Sprint infra-stabilisation 2026-05-29).
 *
 * 4 routes cardinales doivent toujours rendre sans console error et sans
 * network 5xx pour qu'un démo / une vue client soit présentable :
 *   - /conformite
 *   - /usages?tab=pilotage
 *   - /action-center-v4
 *   - /bill-intel
 *
 * Critères d'acceptation :
 *   - 0 console error (hors whitelist)
 *   - 0 network 5xx (les 4xx attendus sont tolérés : ex /api/auth/me 401
 *     n'est jamais émis ici car storageState valide)
 *   - aucun blocage / 404 / écran d'erreur visible
 *
 * Pré-requis : auth.setup.spec.js a tourné en amont (project `setup`).
 */
import { test, expect } from '@playwright/test';

const TIMEOUT = 15_000;

const GOLDEN_PATHS = [
  { name: '/conformite', path: '/conformite' },
  { name: '/usages?tab=pilotage', path: '/usages?tab=pilotage' },
  { name: '/action-center-v4', path: '/action-center-v4' },
  { name: '/bill-intel', path: '/bill-intel' },
];

// Whitelist console : warnings React + vendor noise non liés au produit.
const CONSOLE_WHITELIST = [
  /favicon/i,
  /\[vite\]/,
  /DevTools/,
  /Autofill/,
  /third-party cookie/i,
  /Download the React DevTools/,
  /React does not recognize/,
  /Warning: Each child/i,
  /Warning: Encountered two children with the same key/i,
  /validateDOMNesting/,
  /ResizeObserver loop/,
  /Blocked aria-hidden/,
  /Failed to load resource.*404/,
  /Failed to load resource.*favicon/,
  /net::ERR_/,
  /Warning:/, // React warnings (non-criticals demo)
];

function isConsoleErrorWhitelisted(text) {
  return CONSOLE_WHITELIST.some((rx) => rx.test(text));
}

function attachProbes(page) {
  const consoleErrors = [];
  const network5xx = [];
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (isConsoleErrorWhitelisted(text)) return;
    consoleErrors.push(`${text} @ ${msg.location()?.url || '?'}`);
  });
  page.on('pageerror', (err) => {
    consoleErrors.push(`[pageerror] ${err.message}`);
  });
  page.on('response', (res) => {
    const status = res.status();
    // 5xx uniquement : on tolère les 4xx (validation, 404 sur ressources
    // optionnelles, etc.). Les 4xx critiques apparaissent comme console
    // errors si le FE les rend visibles, ce qui est déjà tracké ci-dessus.
    if (status >= 500 && status < 600) {
      network5xx.push(`HTTP ${status} ${res.url()}`);
    }
  });
  return { consoleErrors, network5xx };
}

test.describe('Golden paths — 0 console error · 0 network 5xx', () => {
  for (const { name, path } of GOLDEN_PATHS) {
    test(`route ${name} rend sans erreur`, async ({ page }) => {
      const probes = attachProbes(page);

      // 1. Navigation + DOM ready (volontairement PAS networkidle :
      // 4 routes × networkidle saturent le BE pendant la suite et
      // produisent des faux timeouts sur les login retry de runs
      // ultérieurs). On capture les erreurs sur le rendu initial
      // + un settle léger (500 ms) pour laisser les fetch primaires
      // se résoudre.
      await page.goto(path, { waitUntil: 'domcontentloaded', timeout: TIMEOUT });
      await page.waitForTimeout(500);

      // 2. Pas de page 404 / écran erreur générique.
      const body = await page.textContent('body');
      expect(
        body,
        `Route ${name} affiche une page 404 / écran erreur fallback`
      ).not.toMatch(/Page introuvable|Erreur serveur|Internal Server Error|Cannot read properties/i);

      // 3. Pas de console error.
      expect(
        probes.consoleErrors,
        `Route ${name} : ${probes.consoleErrors.length} console error(s) hors whitelist :\n  - ${probes.consoleErrors.join('\n  - ')}`
      ).toEqual([]);

      // 4. Pas de 5xx réseau.
      expect(
        probes.network5xx,
        `Route ${name} : ${probes.network5xx.length} réponse(s) 5xx :\n  - ${probes.network5xx.join('\n  - ')}`
      ).toEqual([]);
    });
  }
});
