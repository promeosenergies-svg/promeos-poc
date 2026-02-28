/**
 * PROMEOS — Sprint V17 tests
 * Site selection coherence fixes:
 *  - normalizeId utility (in helpers.js)
 *  - Org-change siteIds validation (ConsumptionExplorerPage org-aware reset effect)
 *  - Auto-select logic (N ≤ 5 → all; N > 5 → first)
 *  - URL site_ids parsing (number coercion)
 *  - ScopeContext filter with String() coerce
 */
import { describe, it, expect } from 'vitest';
import { normalizeId } from '../consumption/helpers';

// ── normalizeId (from helpers.js) ─────────────────────────────────────────────

describe('normalizeId (helpers.js) — V17-B', () => {
  it('converts number to string', () => {
    expect(normalizeId(5)).toBe('5');
  });

  it('converts string to string (identity)', () => {
    expect(normalizeId('5')).toBe('5');
  });

  it('returns null for null', () => {
    expect(normalizeId(null)).toBe(null);
  });

  it('returns null for undefined', () => {
    expect(normalizeId(undefined)).toBe(null);
  });

  it('number 5 and string "5" are equal after normalization', () => {
    expect(normalizeId(5)).toBe(normalizeId('5'));
  });
});

// ── Org-change siteIds validation logic ───────────────────────────────────────

describe('Org-change siteIds validation — V17-A', () => {
  /**
   * Simulates the setSiteIds(prev => ...) updater logic from the org-change effect.
   * N_AUTO = 5 (select all if orgSites.length ≤ 5)
   */
  const N_AUTO = 5;

  function resolveNewSiteIds(prevSiteIds, orgSites, selectedSiteId = null) {
    if (!orgSites.length) return prevSiteIds; // Still loading — no-op
    const orgSiteIdsSet = new Set(orgSites.map(s => s.id));
    const valid = prevSiteIds.filter(id => orgSiteIdsSet.has(Number(id)));
    if (valid.length > 0) {
      return valid.length === prevSiteIds.length ? prevSiteIds : valid;
    }
    // No valid IDs → auto-select
    if (selectedSiteId && orgSiteIdsSet.has(Number(selectedSiteId))) {
      return [Number(selectedSiteId)];
    }
    return orgSites.length <= N_AUTO ? orgSites.map(s => s.id) : [orgSites[0].id];
  }

  it('stale siteId reset to first Tertiaire site when N > 5', () => {
    const staleSites = [1, 2, 3]; // IDs from previous org
    const tertiaireSites = Array.from({ length: 10 }, (_, i) => ({ id: 10 + i }));
    const result = resolveNewSiteIds(staleSites, tertiaireSites, null);
    expect(result).toEqual([tertiaireSites[0].id]);
  });

  it('stale siteId reset to ALL Tertiaire sites when N ≤ 5', () => {
    const staleSites = [99];
    const smallOrg = [{ id: 1 }, { id: 2 }, { id: 3 }]; // N=3 ≤ 5
    const result = resolveNewSiteIds(staleSites, smallOrg, null);
    expect(result).toEqual([1, 2, 3]);
  });

  it('valid siteId in new org → unchanged (stable reference)', () => {
    const prev = [5, 7];
    const orgSites = [{ id: 5 }, { id: 7 }, { id: 9 }];
    const result = resolveNewSiteIds(prev, orgSites, null);
    expect(result).toBe(prev); // Same reference → no re-render
  });

  it('partially valid → only valid IDs kept', () => {
    const prev = [5, 99]; // 99 is stale
    const orgSites = [{ id: 5 }, { id: 7 }];
    const result = resolveNewSiteIds(prev, orgSites, null);
    expect(result).toEqual([5]);
  });

  it('selectedSiteId wins over auto-select when in new org', () => {
    const prev = [99]; // stale
    const orgSites = Array.from({ length: 10 }, (_, i) => ({ id: 10 + i }));
    const result = resolveNewSiteIds(prev, orgSites, 15); // selectedSiteId=15 is in org
    expect(result).toEqual([15]);
  });

  it('selectedSiteId NOT in new org → falls back to auto-select', () => {
    const prev = [99]; // stale
    const orgSites = [{ id: 1 }, { id: 2 }]; // N=2 ≤ 5 → select all
    const result = resolveNewSiteIds(prev, orgSites, 999); // 999 not in org
    expect(result).toEqual([1, 2]); // all because N ≤ 5
  });

  it('empty orgSites (still loading) → returns prevSiteIds unchanged', () => {
    const prev = [5];
    const result = resolveNewSiteIds(prev, [], null);
    expect(result).toBe(prev);
  });
});

// ── Auto-select threshold logic ────────────────────────────────────────────────

describe('Auto-select threshold (N ≤ 5) — V17-A', () => {
  const N_AUTO = 5;

  function autoSelect(orgSites) {
    return orgSites.length <= N_AUTO
      ? orgSites.map(s => s.id)
      : [orgSites[0].id];
  }

  it('N=3 → all 3 sites selected', () => {
    const sites = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(autoSelect(sites)).toEqual([1, 2, 3]);
  });

  it('N=5 → all 5 sites selected (boundary)', () => {
    const sites = Array.from({ length: 5 }, (_, i) => ({ id: i + 1 }));
    expect(autoSelect(sites)).toEqual([1, 2, 3, 4, 5]);
  });

  it('N=6 → only first site selected (above threshold)', () => {
    const sites = Array.from({ length: 6 }, (_, i) => ({ id: i + 1 }));
    expect(autoSelect(sites)).toEqual([1]);
  });

  it('N=10 (Tertiaire) → only first site', () => {
    const sites = Array.from({ length: 10 }, (_, i) => ({ id: i + 1 }));
    expect(autoSelect(sites)).toEqual([1]);
  });
});

// ── URL site_ids parsing ───────────────────────────────────────────────────────

describe('URL site_ids parsing — V17-A', () => {
  /**
   * Simulates useExplorerURL.js line 36:
   * searchParams.get('sites').split(',').map(Number).filter(Boolean)
   */
  function parseUrlSites(param) {
    if (!param) return [];
    return param.split(',').map(Number).filter(Boolean);
  }

  it('sites=1,2 → [1, 2] (numbers)', () => {
    expect(parseUrlSites('1,2')).toEqual([1, 2]);
  });

  it('sites=42 → [42]', () => {
    expect(parseUrlSites('42')).toEqual([42]);
  });

  it('null param → []', () => {
    expect(parseUrlSites(null)).toEqual([]);
  });

  it('empty string → []', () => {
    expect(parseUrlSites('')).toEqual([]);
  });
});

// ── ScopeContext siteId filter with String() coerce ────────────────────────────

describe('ScopeContext siteId filter — V17-B', () => {
  /**
   * Simulates ScopeContext.jsx line 195 after fix:
   * sites.filter((s) => String(s.id) === String(scope.siteId))
   */
  function filterSitesByScopeId(sites, scopeSiteId) {
    if (!scopeSiteId) return sites;
    return sites.filter(s => String(s.id) === String(scopeSiteId));
  }

  it('number s.id=5 matches number scope.siteId=5', () => {
    const sites = [{ id: 5, nom: 'A' }, { id: 7, nom: 'B' }];
    expect(filterSitesByScopeId(sites, 5)).toHaveLength(1);
    expect(filterSitesByScopeId(sites, 5)[0].nom).toBe('A');
  });

  it('number s.id=5 matches string scope.siteId="5" (localStorage case)', () => {
    const sites = [{ id: 5, nom: 'A' }, { id: 7, nom: 'B' }];
    expect(filterSitesByScopeId(sites, '5')).toHaveLength(1);
  });

  it('null scope.siteId → all sites returned', () => {
    const sites = [{ id: 5 }, { id: 7 }];
    expect(filterSitesByScopeId(sites, null)).toHaveLength(2);
  });

  it('non-existent siteId → empty array', () => {
    const sites = [{ id: 5 }, { id: 7 }];
    expect(filterSitesByScopeId(sites, 99)).toHaveLength(0);
  });
});
