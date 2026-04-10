/**
 * PROMEOS — Route Matching Tests (matchRouteToModule)
 * Covers: exact match, dynamic patterns, best-match strategy,
 * prefix fallback, querystring/hash ignore, edge cases.
 */
import { describe, it, expect } from 'vitest';
import { matchRouteToModule, resolveModule, ROUTE_MODULE_MAP, NAV_MODULES } from '../NavRegistry';

/* ── Exact matches ── */
describe('matchRouteToModule — exact matches', () => {
  it('/ → cockpit', () => {
    const r = matchRouteToModule('/');
    expect(r.moduleId).toBe('cockpit');
    expect(r.moduleLabel).toBe('Accueil');
    expect(r.pattern).toBe('/');
  });

  it('/conformite → conformite (module autonome V7)', () => {
    expect(matchRouteToModule('/conformite').moduleId).toBe('conformite');
  });

  it('/consommations → energie', () => {
    expect(matchRouteToModule('/consommations').moduleId).toBe('energie');
  });

  it('/bill-intel → patrimoine (migré V7)', () => {
    expect(matchRouteToModule('/bill-intel').moduleId).toBe('patrimoine');
  });

  it('/patrimoine → patrimoine', () => {
    expect(matchRouteToModule('/patrimoine').moduleId).toBe('patrimoine');
  });
});

/* ── Dynamic route patterns ── */
describe('matchRouteToModule — dynamic patterns (10 cases)', () => {
  it('/sites/42 → patrimoine (pattern /sites/:id)', () => {
    const r = matchRouteToModule('/sites/42');
    expect(r.moduleId).toBe('patrimoine');
    expect(r.pattern).toBe('/sites/:id');
  });

  it('/sites/1 → patrimoine', () => {
    expect(matchRouteToModule('/sites/1').moduleId).toBe('patrimoine');
  });

  it('/sites/999 → patrimoine', () => {
    expect(matchRouteToModule('/sites/999').moduleId).toBe('patrimoine');
  });

  it('/actions/123 → cockpit (pattern /actions/:actionId)', () => {
    const r = matchRouteToModule('/actions/123');
    expect(r.moduleId).toBe('cockpit');
    expect(r.pattern).toBe('/actions/:actionId');
  });

  it('/actions/7 → cockpit', () => {
    expect(matchRouteToModule('/actions/7').moduleId).toBe('cockpit');
  });

  it('/conformite/tertiaire/efa/5 → conformite (pattern /conformite/tertiaire/efa/:id)', () => {
    const r = matchRouteToModule('/conformite/tertiaire/efa/5');
    expect(r.moduleId).toBe('conformite');
    expect(r.pattern).toBe('/conformite/tertiaire/efa/:id');
  });

  it('/conformite/tertiaire/efa/99 → conformite', () => {
    expect(matchRouteToModule('/conformite/tertiaire/efa/99').moduleId).toBe('conformite');
  });

  it('/compliance/sites/42 → conformite (pattern /compliance/sites/:siteId)', () => {
    const r = matchRouteToModule('/compliance/sites/42');
    expect(r.moduleId).toBe('conformite');
    expect(r.pattern).toBe('/compliance/sites/:siteId');
  });

  it('/actions/new → cockpit (exact match wins over dynamic)', () => {
    const r = matchRouteToModule('/actions/new');
    expect(r.moduleId).toBe('cockpit');
    expect(r.pattern).toBe('/actions/new');
  });

  it('/admin/users → admin (multi-segment exact)', () => {
    expect(matchRouteToModule('/admin/users').moduleId).toBe('admin');
  });
});

/* ── Best match strategy ── */
describe('matchRouteToModule — best match wins', () => {
  it('/conformite/tertiaire/efa/:id is more specific than /conformite', () => {
    const r = matchRouteToModule('/conformite/tertiaire/efa/5');
    expect(r.pattern).toBe('/conformite/tertiaire/efa/:id');
    expect(r.pattern).not.toBe('/conformite');
  });

  it('exact match takes priority over pattern', () => {
    const r = matchRouteToModule('/actions/new');
    expect(r.pattern).toBe('/actions/new');
  });

  it('more static segments score higher than dynamic ones', () => {
    const r = matchRouteToModule('/conformite/tertiaire/efa/5');
    expect(r.moduleId).toBe('conformite');
  });
});

/* ── Querystring & hash ignored ── */
describe('matchRouteToModule — ignores querystring and hash', () => {
  it('/bill-intel?site_id=1&month=2024-01 → patrimoine (migré V7)', () => {
    expect(matchRouteToModule('/bill-intel?site_id=1&month=2024-01').moduleId).toBe('patrimoine');
  });

  it('/actions/123?tab=detail → cockpit', () => {
    expect(matchRouteToModule('/actions/123?tab=detail').moduleId).toBe('cockpit');
  });

  it('/patrimoine#filters → patrimoine', () => {
    expect(matchRouteToModule('/patrimoine#filters').moduleId).toBe('patrimoine');
  });

  it('/sites/42?from=dashboard#top → patrimoine', () => {
    expect(matchRouteToModule('/sites/42?from=dashboard#top').moduleId).toBe('patrimoine');
  });
});

/* ── Prefix fallback ── */
describe('matchRouteToModule — prefix fallback', () => {
  it('/consommations/explorer → energie', () => {
    expect(matchRouteToModule('/consommations/explorer').moduleId).toBe('energie');
  });

  it('/admin/roles → admin', () => {
    expect(matchRouteToModule('/admin/roles').moduleId).toBe('admin');
  });

  it('/unknown/deep/path → cockpit (default fallback)', () => {
    const r = matchRouteToModule('/unknown/deep/path');
    expect(r.moduleId).toBe('cockpit');
    expect(r.pattern).toBeNull();
  });
});

/* ── resolveModule delegates correctly ── */
describe('resolveModule (uses matchRouteToModule)', () => {
  it('static routes resolve correctly', () => {
    expect(resolveModule('/')).toBe('cockpit');
    expect(resolveModule('/conformite')).toBe('conformite');
    expect(resolveModule('/bill-intel')).toBe('patrimoine');
  });

  it('dynamic routes resolve correctly', () => {
    expect(resolveModule('/sites/42')).toBe('patrimoine');
    expect(resolveModule('/actions/123')).toBe('cockpit');
    expect(resolveModule('/conformite/tertiaire/efa/5')).toBe('conformite');
  });

  it('unknown routes default to cockpit', () => {
    expect(resolveModule('/nope')).toBe('cockpit');
  });
});

/* ── moduleLabel correctness ── */
describe('matchRouteToModule — moduleLabel is always FR', () => {
  it('all moduleLabels are valid module labels', () => {
    const validLabels = NAV_MODULES.map((m) => m.label);
    const testPaths = [
      '/',
      '/conformite',
      '/consommations',
      '/bill-intel',
      '/patrimoine',
      '/sites/1',
      '/actions/99',
    ];
    for (const p of testPaths) {
      const { moduleLabel } = matchRouteToModule(p);
      expect(validLabels).toContain(moduleLabel);
    }
  });
});

/* ── ROUTE_MODULE_MAP integrity with dynamic patterns ── */
describe('ROUTE_MODULE_MAP — dynamic patterns present', () => {
  it('contains /sites/:id', () => {
    expect(ROUTE_MODULE_MAP['/sites/:id']).toBe('patrimoine');
  });

  it('contains /actions/:actionId', () => {
    expect(ROUTE_MODULE_MAP['/actions/:actionId']).toBe('cockpit');
  });

  it('contains /conformite/tertiaire/efa/:id', () => {
    expect(ROUTE_MODULE_MAP['/conformite/tertiaire/efa/:id']).toBe('conformite');
  });

  it('contains /compliance/sites/:siteId', () => {
    expect(ROUTE_MODULE_MAP['/compliance/sites/:siteId']).toBe('conformite');
  });

  it('all ROUTE_MODULE_MAP values are valid module keys', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const [, mod] of Object.entries(ROUTE_MODULE_MAP)) {
      expect(moduleKeys).toContain(mod);
    }
  });
});
