/**
 * ROUTE_MODULE_MAP ↔ App.jsx invariant — Sprint 1 Vague A phase A6
 *
 * Anti-drift : toute entrée de ROUTE_MODULE_MAP doit avoir une Route
 * React correspondante dans App.jsx (soit réelle, soit redirect via
 * <Navigate>). Évite la récidive de l'incident A5 (mapping vers rail
 * + promesse cassée en NotFound) et de l'oubli A6 (aper-legacy mappé
 * nulle part malgré la route React).
 *
 * Pattern matching : segments `:id` considérés comme wildcards (la
 * résolution frontend fait pattern-score matching). Entrées avec
 * query param (`?tab=`) extraites en base path.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { ROUTE_MODULE_MAP } from '../NavRegistry';

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_SRC = readFileSync(join(__dirname, '..', '..', 'App.jsx'), 'utf-8');

const ALL_DECLARED_PATHS = Array.from(APP_SRC.matchAll(/path="([^"]+)"/g), (m) => m[1]).filter(
  (p) => p !== '*'
);

// Routes absolues (commencent par `/`).
const ABS_ROUTES = ALL_DECLARED_PATHS.filter((p) => p.startsWith('/'));

// Routes nested (path relatif sans `/` initial) — le parent est la route
// absolue précédente dans App.jsx. Ici on code en dur la connaissance
// des parents connus : `/consommations` contient les 4 tabs en nested.
// Quand une nouvelle nested route parent apparaît, ajouter ici.
const NESTED_PARENTS = { '/consommations': ['explorer', 'portfolio', 'import', 'kb'] };

const NESTED_COMPOSED = Object.entries(NESTED_PARENTS).flatMap(([parent, children]) =>
  children.map((c) => `${parent}/${c}`)
);

// Pool complète : absolus + nested composés.
const DECLARED_ROUTE_PATHS = [...ABS_ROUTES, ...NESTED_COMPOSED];

function normalize(path) {
  return path.replace(/:[a-zA-Z_]+/g, ':id');
}

function hasRouteMatch(mapEntry) {
  const norm = normalize(mapEntry);
  return DECLARED_ROUTE_PATHS.some((r) => normalize(r) === norm);
}

describe('ROUTE_MODULE_MAP ↔ App.jsx invariant (A6)', () => {
  it('every ROUTE_MODULE_MAP entry has a corresponding Route in App.jsx', () => {
    const orphans = Object.keys(ROUTE_MODULE_MAP).filter((entry) => !hasRouteMatch(entry));
    expect(
      orphans,
      `ROUTE_MODULE_MAP entries without matching Route in App.jsx: ${orphans.join(', ')}`
    ).toEqual([]);
  });

  it('every legacy A/B route has a ROUTE_MODULE_MAP entry', () => {
    const LEGACY_ROUTES = [
      '/home-legacy',
      '/cockpit-legacy',
      '/conformite-legacy',
      '/conformite/aper-legacy',
      '/monitoring-legacy',
      '/patrimoine-legacy',
      '/sites-legacy/:id',
      '/bill-intel-legacy',
      '/achat-energie-legacy',
    ];
    const unmapped = LEGACY_ROUTES.filter((r) => !ROUTE_MODULE_MAP[r]);
    expect(unmapped, `Legacy routes missing from ROUTE_MODULE_MAP: ${unmapped.join(', ')}`).toEqual(
      []
    );
  });

  it('A5 retired routes remain absent', () => {
    expect(ROUTE_MODULE_MAP['/conformite/dt']).toBeUndefined();
    expect(ROUTE_MODULE_MAP['/conformite/bacs']).toBeUndefined();
    expect(ROUTE_MODULE_MAP['/conformite/audit-sme']).toBeUndefined();
  });

  it('A6 /conformite/aper-legacy now has entry', () => {
    expect(ROUTE_MODULE_MAP['/conformite/aper-legacy']).toBe('conformite');
  });
});
