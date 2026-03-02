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
    expect(r.moduleLabel).toBe('Cockpit');
    expect(r.pattern).toBe('/');
  });

  it('/conformite → operations', () => {
    expect(matchRouteToModule('/conformite').moduleId).toBe('operations');
  });

  it('/consommations → analyse', () => {
    expect(matchRouteToModule('/consommations').moduleId).toBe('analyse');
  });

  it('/bill-intel → marche', () => {
    expect(matchRouteToModule('/bill-intel').moduleId).toBe('marche');
  });

  it('/patrimoine → admin', () => {
    expect(matchRouteToModule('/patrimoine').moduleId).toBe('admin');
  });
});

/* ── Dynamic route patterns ── */
describe('matchRouteToModule — dynamic patterns (10 cases)', () => {
  it('/sites/42 → admin (pattern /sites/:id)', () => {
    const r = matchRouteToModule('/sites/42');
    expect(r.moduleId).toBe('admin');
    expect(r.pattern).toBe('/sites/:id');
  });

  it('/sites/1 → admin', () => {
    expect(matchRouteToModule('/sites/1').moduleId).toBe('admin');
  });

  it('/sites/999 → admin', () => {
    expect(matchRouteToModule('/sites/999').moduleId).toBe('admin');
  });

  it('/actions/123 → operations (pattern /actions/:actionId)', () => {
    const r = matchRouteToModule('/actions/123');
    expect(r.moduleId).toBe('operations');
    expect(r.pattern).toBe('/actions/:actionId');
  });

  it('/actions/7 → operations', () => {
    expect(matchRouteToModule('/actions/7').moduleId).toBe('operations');
  });

  it('/conformite/tertiaire/efa/5 → operations (pattern /conformite/tertiaire/efa/:id)', () => {
    const r = matchRouteToModule('/conformite/tertiaire/efa/5');
    expect(r.moduleId).toBe('operations');
    expect(r.pattern).toBe('/conformite/tertiaire/efa/:id');
  });

  it('/conformite/tertiaire/efa/99 → operations', () => {
    expect(matchRouteToModule('/conformite/tertiaire/efa/99').moduleId).toBe('operations');
  });

  it('/compliance/sites/42 → operations (pattern /compliance/sites/:siteId)', () => {
    const r = matchRouteToModule('/compliance/sites/42');
    expect(r.moduleId).toBe('operations');
    expect(r.pattern).toBe('/compliance/sites/:siteId');
  });

  it('/actions/new → operations (exact match wins over dynamic)', () => {
    const r = matchRouteToModule('/actions/new');
    expect(r.moduleId).toBe('operations');
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
    // Should NOT match /conformite by prefix
    expect(r.pattern).not.toBe('/conformite');
  });

  it('exact match takes priority over pattern', () => {
    const r = matchRouteToModule('/actions/new');
    // /actions/new is an exact match, should not match /actions/:actionId
    expect(r.pattern).toBe('/actions/new');
  });

  it('more static segments score higher than dynamic ones', () => {
    // /conformite/tertiaire/efa/:id has 3 static + 1 dynamic = score 7
    // This should beat a hypothetical /conformite/tertiaire/:x/:y = 2 static + 2 dynamic = score 6
    const r = matchRouteToModule('/conformite/tertiaire/efa/5');
    expect(r.moduleId).toBe('operations');
  });
});

/* ── Querystring & hash ignored ── */
describe('matchRouteToModule — ignores querystring and hash', () => {
  it('/bill-intel?site_id=1&month=2024-01 → marche', () => {
    expect(matchRouteToModule('/bill-intel?site_id=1&month=2024-01').moduleId).toBe('marche');
  });

  it('/actions/123?tab=detail → operations', () => {
    expect(matchRouteToModule('/actions/123?tab=detail').moduleId).toBe('operations');
  });

  it('/patrimoine#filters → admin', () => {
    expect(matchRouteToModule('/patrimoine#filters').moduleId).toBe('admin');
  });

  it('/sites/42?from=dashboard#top → admin', () => {
    expect(matchRouteToModule('/sites/42?from=dashboard#top').moduleId).toBe('admin');
  });
});

/* ── Prefix fallback ── */
describe('matchRouteToModule — prefix fallback', () => {
  it('/consommations/explorer → analyse', () => {
    expect(matchRouteToModule('/consommations/explorer').moduleId).toBe('analyse');
  });

  it('/admin/roles → admin', () => {
    expect(matchRouteToModule('/admin/roles').moduleId).toBe('admin');
  });

  it('/unknown/deep/path → cockpit (default)', () => {
    const r = matchRouteToModule('/unknown/deep/path');
    expect(r.moduleId).toBe('cockpit');
    expect(r.pattern).toBeNull();
  });
});

/* ── resolveModule delegates correctly ── */
describe('resolveModule (uses matchRouteToModule)', () => {
  it('static routes resolve correctly', () => {
    expect(resolveModule('/')).toBe('cockpit');
    expect(resolveModule('/conformite')).toBe('operations');
    expect(resolveModule('/bill-intel')).toBe('marche');
  });

  it('dynamic routes resolve correctly', () => {
    expect(resolveModule('/sites/42')).toBe('admin');
    expect(resolveModule('/actions/123')).toBe('operations');
    expect(resolveModule('/conformite/tertiaire/efa/5')).toBe('operations');
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
      '/', '/conformite', '/consommations', '/bill-intel',
      '/patrimoine', '/sites/1', '/actions/99',
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
    expect(ROUTE_MODULE_MAP['/sites/:id']).toBe('admin');
  });

  it('contains /actions/:actionId', () => {
    expect(ROUTE_MODULE_MAP['/actions/:actionId']).toBe('operations');
  });

  it('contains /conformite/tertiaire/efa/:id', () => {
    expect(ROUTE_MODULE_MAP['/conformite/tertiaire/efa/:id']).toBe('operations');
  });

  it('contains /compliance/sites/:siteId', () => {
    expect(ROUTE_MODULE_MAP['/compliance/sites/:siteId']).toBe('operations');
  });

  it('all ROUTE_MODULE_MAP values are valid module keys', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const [, mod] of Object.entries(ROUTE_MODULE_MAP)) {
      expect(moduleKeys).toContain(mod);
    }
  });
});
