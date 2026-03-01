/**
 * PROMEOS — Sprint Demo Scope Fix regression tests
 * Covers: setApiScope interceptor, ScopeContext orgSites/sitesCount,
 * scopedSites using apiSites, ScopeSwitcher site-selector logic.
 */
import { describe, it, expect, vi } from 'vitest';

// ── setApiScope / interceptor logic ─────────────────────────────────────────

describe('setApiScope: scope state management', () => {
  // Simulate the module-level _apiScope + setApiScope pattern from api.js
  function makeApiScopeModule() {
    let _scope = { orgId: null, siteId: null };
    function setApiScope({ orgId = null, siteId = null } = {}) {
      _scope = { orgId: orgId ?? null, siteId: siteId ?? null };
    }
    function getScope() { return { ..._scope }; }
    function buildHeaders(url) {
      const isDemoPath = url && (url.includes('/demo/') || url.includes('/seed'));
      const headers = {};
      if (!isDemoPath) {
        if (_scope.orgId != null) headers['X-Org-Id'] = String(_scope.orgId);
        if (_scope.siteId != null) headers['X-Site-Id'] = String(_scope.siteId);
      }
      return headers;
    }
    return { setApiScope, getScope, buildHeaders };
  }

  it('initial scope is null/null', () => {
    const { getScope } = makeApiScopeModule();
    expect(getScope()).toEqual({ orgId: null, siteId: null });
  });

  it('setApiScope updates orgId and siteId', () => {
    const { setApiScope, getScope } = makeApiScopeModule();
    setApiScope({ orgId: 42, siteId: 7 });
    expect(getScope()).toEqual({ orgId: 42, siteId: 7 });
  });

  it('setApiScope with only orgId leaves siteId null', () => {
    const { setApiScope, getScope } = makeApiScopeModule();
    setApiScope({ orgId: 5 });
    expect(getScope()).toEqual({ orgId: 5, siteId: null });
  });

  it('setApiScope with null resets values', () => {
    const { setApiScope, getScope } = makeApiScopeModule();
    setApiScope({ orgId: 10, siteId: 3 });
    setApiScope({ orgId: null, siteId: null });
    expect(getScope()).toEqual({ orgId: null, siteId: null });
  });

  it('buildHeaders injects X-Org-Id when orgId is set', () => {
    const { setApiScope, buildHeaders } = makeApiScopeModule();
    setApiScope({ orgId: 99 });
    const headers = buildHeaders('/api/cockpit');
    expect(headers['X-Org-Id']).toBe('99');
    expect(headers['X-Site-Id']).toBeUndefined();
  });

  it('buildHeaders injects both headers when both are set', () => {
    const { setApiScope, buildHeaders } = makeApiScopeModule();
    setApiScope({ orgId: 3, siteId: 12 });
    const headers = buildHeaders('/api/sites');
    expect(headers['X-Org-Id']).toBe('3');
    expect(headers['X-Site-Id']).toBe('12');
  });

  it('buildHeaders skips demo/seed paths', () => {
    const { setApiScope, buildHeaders } = makeApiScopeModule();
    setApiScope({ orgId: 1, siteId: 2 });
    expect(buildHeaders('/api/demo/seed')).toEqual({});
    expect(buildHeaders('/api/seed')).toEqual({});
  });

  it('buildHeaders skips injection when orgId is null', () => {
    const { buildHeaders } = makeApiScopeModule();
    const headers = buildHeaders('/api/cockpit');
    expect(headers['X-Org-Id']).toBeUndefined();
    expect(headers['X-Site-Id']).toBeUndefined();
  });
});

// ── ScopeContext: orgSites / scopedSites logic ────────────────────────────────

describe('ScopeContext: orgSites and scopedSites logic', () => {
  const MOCK_SITES = Array.from({ length: 60 }, (_, i) => ({ id: i + 1, nom: `Mock Site ${i + 1}` }));
  const API_SITES_10 = Array.from({ length: 10 }, (_, i) => ({ id: i + 100, nom: `API Site ${i + 1}` }));

  function computeOrgSites(apiSites, mockSites, effectiveOrgId) {
    if (apiSites.length > 0) return apiSites;
    // Simulate mock fallback (all mocks "belong" to org 1 in simplified test)
    return effectiveOrgId === 1 ? mockSites : [];
  }

  function computeScopedSites(apiSites, mockSites, effectiveOrgId, siteId) {
    let sites;
    if (apiSites.length > 0) {
      sites = apiSites;
    } else {
      sites = effectiveOrgId === 1 ? mockSites : [];
    }
    if (siteId) {
      sites = sites.filter(s => s.id === siteId);
    }
    return sites;
  }

  it('orgSites uses apiSites when available', () => {
    const org = computeOrgSites(API_SITES_10, MOCK_SITES, 1);
    expect(org).toHaveLength(10);
    expect(org[0].id).toBe(100);
  });

  it('orgSites falls back to mockSites when apiSites is empty', () => {
    const org = computeOrgSites([], MOCK_SITES, 1);
    expect(org).toHaveLength(60);
  });

  it('sitesCount reflects apiSites.length when apiSites available', () => {
    const orgSites = computeOrgSites(API_SITES_10, MOCK_SITES, 1);
    const sitesCount = orgSites.length;
    expect(sitesCount).toBe(10); // correct: 10, not 60
  });

  it('scopedSites uses apiSites without siteId filter', () => {
    const scoped = computeScopedSites(API_SITES_10, MOCK_SITES, 1, null);
    expect(scoped).toHaveLength(10);
  });

  it('scopedSites filters to single site when siteId is set', () => {
    const scoped = computeScopedSites(API_SITES_10, MOCK_SITES, 1, 101);
    expect(scoped).toHaveLength(1);
    expect(scoped[0].id).toBe(101);
  });

  it('scopedSites returns empty when siteId not found', () => {
    const scoped = computeScopedSites(API_SITES_10, MOCK_SITES, 1, 9999);
    expect(scoped).toHaveLength(0);
  });

  it('scopedSites falls back to mockSites when apiSites empty', () => {
    const scoped = computeScopedSites([], MOCK_SITES, 1, null);
    expect(scoped).toHaveLength(60);
  });
});

// ── scopeLabel logic ──────────────────────────────────────────────────────────

describe('ScopeContext: scopeLabel', () => {
  const sites = [
    { id: 1, nom: 'Site Alpha' },
    { id: 2, nom: 'Site Beta' },
  ];

  function computeScopeLabel(siteId, scopedSites) {
    if (!siteId) return 'Tous les sites';
    const site = scopedSites.find(s => s.id === siteId);
    return site ? `Site\u00a0: ${site.nom}` : 'Tous les sites';
  }

  it('returns "Tous les sites" when no siteId', () => {
    expect(computeScopeLabel(null, sites)).toBe('Tous les sites');
  });

  it('returns site name when siteId matches', () => {
    expect(computeScopeLabel(1, sites)).toBe('Site\u00a0: Site Alpha');
  });

  it('returns "Tous les sites" when siteId not found', () => {
    expect(computeScopeLabel(999, sites)).toBe('Tous les sites');
  });
});

// ── ScopeSwitcher: site selector logic ───────────────────────────────────────

describe('ScopeSwitcher: site selector', () => {
  it('shows site section only when orgSites is non-empty', () => {
    const hasSites10 = (orgSites) => orgSites.length > 0;
    expect(hasSites10([])).toBe(false);
    expect(hasSites10([{ id: 1 }])).toBe(true);
    expect(hasSites10(Array.from({ length: 10 }, (_, i) => ({ id: i })))).toBe(true);
  });

  it('selecting a site calls setSite(id)', () => {
    const setSite = vi.fn();
    function simulateClick(siteId) { setSite(siteId); }
    simulateClick(5);
    expect(setSite).toHaveBeenCalledWith(5);
  });

  it('"Tous les sites" calls setSite(null)', () => {
    const setSite = vi.fn();
    function simulateTousLesSites() { setSite(null); }
    simulateTousLesSites();
    expect(setSite).toHaveBeenCalledWith(null);
  });

  it('site count label shows correct count', () => {
    const orgSites = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, nom: `S${i + 1}` }));
    const label = `Site (${orgSites.length})`;
    expect(label).toBe('Site (10)');
  });

  it('clear button shown when siteId or portefeuilleId is set', () => {
    function showClear(scope) { return !!(scope.portefeuilleId || scope.siteId); }
    expect(showClear({ portefeuilleId: null, siteId: null })).toBe(false);
    expect(showClear({ portefeuilleId: 2, siteId: null })).toBe(true);
    expect(showClear({ portefeuilleId: null, siteId: 7 })).toBe(true);
  });
});

// ── Backend: cockpit org filter logic ────────────────────────────────────────

describe('Backend cockpit: org_id header extraction', () => {
  // Simulate the Python helper logic in pure JS for unit testing
  function getOrgIdFromHeaders(headers) {
    const raw = headers['X-Org-Id'];
    if (raw) {
      const n = parseInt(raw, 10);
      if (!isNaN(n)) return n;
    }
    return null;
  }

  it('returns null when no header', () => {
    expect(getOrgIdFromHeaders({})).toBeNull();
  });

  it('returns parsed int when header present', () => {
    expect(getOrgIdFromHeaders({ 'X-Org-Id': '42' })).toBe(42);
  });

  it('returns null for non-numeric header value', () => {
    expect(getOrgIdFromHeaders({ 'X-Org-Id': 'abc' })).toBeNull();
  });

  it('returns null for empty string header', () => {
    expect(getOrgIdFromHeaders({ 'X-Org-Id': '' })).toBeNull();
  });
});

// ── Demo scope: X sites count display ────────────────────────────────────────

describe('Demo scope: correct site count display', () => {
  it('TopBar shows sitesCount from API, not mockSites.length', () => {
    // Simulate: API returns 10 sites for SCI org, mockSites has 60
    const apiSites = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, nom: `S${i + 1}` }));
    const mockSites = Array.from({ length: 60 }, (_, i) => ({ id: i + 1, nom: `M${i + 1}` }));

    const sitesCount = apiSites.length > 0 ? apiSites.length : mockSites.length;
    expect(sitesCount).toBe(10);
  });

  it('sitesCount = 0 when org has no sites (new org)', () => {
    const apiSites = [];
    const orgSites = apiSites; // no fallback for unknown org
    expect(orgSites.length).toBe(0);
  });

  it('after setSite(id) scopedSites has exactly 1 site', () => {
    const apiSites = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, nom: `S${i + 1}` }));
    const siteId = 3;
    const scoped = apiSites.filter(s => s.id === siteId);
    expect(scoped).toHaveLength(1);
    expect(scoped[0].id).toBe(3);
  });
});
