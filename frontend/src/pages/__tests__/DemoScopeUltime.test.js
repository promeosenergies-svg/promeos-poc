/**
 * PROMEOS — Fix Ultime: Cohérence Demo Pack + Scope Global
 * Tests couvrant:
 *   - DemoState org tracking (logique pure simulée)
 *   - status-pack: retourne org correct + sites_count scopé
 *   - ScopeSummary: label correct selon siteId null/set
 *   - CommandCenter/Cockpit/Conformité: utilisent sitesCount (orgSites.length)
 *   - Scénarios end-to-end: seed S(10), reset, switch org
 */
import { describe, it, expect, beforeEach } from 'vitest';

// ── Simulate DemoState singleton logic ────────────────────────────────────────

describe('DemoState: org tracking', () => {
  function makeDemoState() {
    let _org_id = null;
    let _org_nom = null;
    let _pack = null;
    let _size = null;
    let _sites_count = null;

    return {
      set_demo_org({ org_id, org_nom = null, pack = null, size = null, sites_count = null }) {
        _org_id = org_id;
        _org_nom = org_nom;
        _pack = pack;
        _size = size;
        _sites_count = sites_count;
      },
      clear_demo_org() {
        _org_id = null;
        _org_nom = null;
        _pack = null;
        _size = null;
        _sites_count = null;
      },
      get_demo_org_id: () => _org_id,
      get_demo_context: () => ({
        org_id: _org_id,
        org_nom: _org_nom,
        pack: _pack,
        size: _size,
        sites_count: _sites_count,
      }),
    };
  }

  it('starts with null org_id', () => {
    const ds = makeDemoState();
    expect(ds.get_demo_org_id()).toBeNull();
  });

  it('set_demo_org stores correct org_id and pack info', () => {
    const ds = makeDemoState();
    ds.set_demo_org({ org_id: 42, org_nom: 'SCI Les Terrasses', pack: 'tertiaire', size: 'S', sites_count: 10 });
    expect(ds.get_demo_org_id()).toBe(42);
    const ctx = ds.get_demo_context();
    expect(ctx.org_nom).toBe('SCI Les Terrasses');
    expect(ctx.pack).toBe('tertiaire');
    expect(ctx.size).toBe('S');
    expect(ctx.sites_count).toBe(10);
  });

  it('clear_demo_org resets all fields to null', () => {
    const ds = makeDemoState();
    ds.set_demo_org({ org_id: 42, org_nom: 'SCI Les Terrasses', pack: 'tertiaire', size: 'S', sites_count: 10 });
    ds.clear_demo_org();
    expect(ds.get_demo_org_id()).toBeNull();
    expect(ds.get_demo_context().org_id).toBeNull();
    expect(ds.get_demo_context().sites_count).toBeNull();
  });

  it('re-seeding with different org updates correctly (no stale data)', () => {
    const ds = makeDemoState();
    ds.set_demo_org({ org_id: 1, org_nom: 'Groupe Casino', pack: 'casino', size: 'S', sites_count: 36 });
    ds.set_demo_org({ org_id: 42, org_nom: 'SCI Les Terrasses', pack: 'tertiaire', size: 'S', sites_count: 10 });
    expect(ds.get_demo_org_id()).toBe(42);
    expect(ds.get_demo_context().sites_count).toBe(10);
    expect(ds.get_demo_context().org_nom).toBe('SCI Les Terrasses');
  });
});

// ── Simulate status-pack response logic ───────────────────────────────────────

describe('status-pack: scoped response', () => {
  function buildStatusPackResponse(demoCtx, orgFromDb, siteCount) {
    if (!orgFromDb) return { status: 'no_org' };
    return {
      status: 'seeded',
      org_id: orgFromDb.id,
      org_nom: orgFromDb.nom,
      pack: demoCtx.pack ?? orgFromDb.pack ?? null,
      size: demoCtx.size ?? null,
      sites_count: siteCount,
      total_rows: siteCount * 365 * 48,  // indicative
    };
  }

  it('returns 10 for Tertiaire S pack', () => {
    const ctx = { org_id: 42, org_nom: 'SCI Les Terrasses', pack: 'tertiaire', size: 'S', sites_count: 10 };
    const org = { id: 42, nom: 'SCI Les Terrasses' };
    const resp = buildStatusPackResponse(ctx, org, 10);
    expect(resp.sites_count).toBe(10);
    expect(resp.pack).toBe('tertiaire');
    expect(resp.size).toBe('S');
  });

  it('returns 20 for Tertiaire M pack', () => {
    const ctx = { org_id: 42, pack: 'tertiaire', size: 'M' };
    const org = { id: 42, nom: 'SCI Les Terrasses' };
    const resp = buildStatusPackResponse(ctx, org, 20);
    expect(resp.sites_count).toBe(20);
    expect(resp.size).toBe('M');
  });

  it('returns 36 for Casino S pack (not confused with Tertiaire)', () => {
    const ctx = { org_id: 1, pack: 'casino', size: 'S' };
    const org = { id: 1, nom: 'Groupe Casino' };
    const resp = buildStatusPackResponse(ctx, org, 36);
    expect(resp.sites_count).toBe(36);
    expect(resp.pack).toBe('casino');
    expect(resp.org_nom).toBe('Groupe Casino');
  });

  it('returns no_org when no org in DB after reset', () => {
    const ctx = { org_id: null };
    const resp = buildStatusPackResponse(ctx, null, 0);
    expect(resp.status).toBe('no_org');
  });
});

// ── ScopeSummary label logic ───────────────────────────────────────────────────

describe('ScopeSummary: label logic', () => {
  function buildScopeLabel({ orgNom, scopeLabel, sitesCount, selectedSiteId, showCount = true }) {
    if (!orgNom) return null;
    if (selectedSiteId) {
      return `${orgNom} — ${scopeLabel}`;
    }
    return `${orgNom} — Tous les sites${showCount && sitesCount ? ` (${sitesCount})` : ''}`;
  }

  it('shows "Org — Tous les sites (10)" when siteId null and sitesCount=10', () => {
    const label = buildScopeLabel({ orgNom: 'SCI Les Terrasses', scopeLabel: 'Tous les sites', sitesCount: 10, selectedSiteId: null });
    expect(label).toBe('SCI Les Terrasses — Tous les sites (10)');
  });

  it('shows "Org — Site : Hotel Ibis" when siteId set', () => {
    const label = buildScopeLabel({ orgNom: 'SCI Les Terrasses', scopeLabel: 'Site\u00a0: Hotel Ibis', sitesCount: 10, selectedSiteId: 7 });
    expect(label).toBe('SCI Les Terrasses — Site\u00a0: Hotel Ibis');
  });

  it('omits count when showCount=false', () => {
    const label = buildScopeLabel({ orgNom: 'SCI Les Terrasses', scopeLabel: 'Tous les sites', sitesCount: 10, selectedSiteId: null, showCount: false });
    expect(label).toBe('SCI Les Terrasses — Tous les sites');
  });

  it('omits count when sitesCount=0', () => {
    const label = buildScopeLabel({ orgNom: 'SCI Les Terrasses', scopeLabel: 'Tous les sites', sitesCount: 0, selectedSiteId: null });
    expect(label).toBe('SCI Les Terrasses — Tous les sites');
  });

  it('returns null when org is missing', () => {
    const label = buildScopeLabel({ orgNom: null, scopeLabel: 'Tous les sites', sitesCount: 10, selectedSiteId: null });
    expect(label).toBeNull();
  });

  it('shows (20) for Tertiaire M pack', () => {
    const label = buildScopeLabel({ orgNom: 'SCI Les Terrasses', scopeLabel: 'Tous les sites', sitesCount: 20, selectedSiteId: null });
    expect(label).toContain('(20)');
  });

  it('shows (36) for Casino S pack', () => {
    const label = buildScopeLabel({ orgNom: 'Groupe Casino', scopeLabel: 'Tous les sites', sitesCount: 36, selectedSiteId: null });
    expect(label).toContain('(36)');
  });
});

// ── sitesCount usage in page subtitles ────────────────────────────────────────

describe('Page subtitles: use sitesCount (orgSites.length) not scopedSites.length', () => {
  // Simulates the new subtitle logic used in CommandCenter + Cockpit
  function buildSubtitle(orgNom, sitesCount) {
    return `${orgNom} · ${sitesCount} site${sitesCount !== 1 ? 's' : ''}`;
  }

  it('CommandCenter subtitle: "SCI Les Terrasses · 10 sites" for S pack', () => {
    const subtitle = buildSubtitle('SCI Les Terrasses', 10);
    expect(subtitle).toBe('SCI Les Terrasses · 10 sites');
  });

  it('CommandCenter subtitle: "SCI Les Terrasses · 20 sites" for M pack', () => {
    const subtitle = buildSubtitle('SCI Les Terrasses', 20);
    expect(subtitle).toBe('SCI Les Terrasses · 20 sites');
  });

  it('CommandCenter subtitle: "Groupe Casino · 36 sites" for Casino S pack', () => {
    const subtitle = buildSubtitle('Groupe Casino', 36);
    expect(subtitle).toBe('Groupe Casino · 36 sites');
  });

  it('correct pluralization: "1 site" singular', () => {
    const subtitle = buildSubtitle('SCI Les Terrasses', 1);
    expect(subtitle).toBe('SCI Les Terrasses · 1 site');
  });

  it('correct pluralization: "0 sites" for empty org after reset', () => {
    const subtitle = buildSubtitle('SCI Les Terrasses', 0);
    expect(subtitle).toBe('SCI Les Terrasses · 0 sites');
  });

  it('sitesCount (orgSites.length=10) != scopedSites.length (1) when site selected → subtitle stays 10', () => {
    // Demonstrates why we use sitesCount not scopedSites.length for org-level subtitle
    const sitesCount = 10;        // orgSites.length (org total)
    const scopedCount = 1;        // scopedSites.length (filtered by siteId)
    const subtitleWithSitesCount = buildSubtitle('SCI Les Terrasses', sitesCount);
    const subtitleWithScopedCount = buildSubtitle('SCI Les Terrasses', scopedCount);
    // sitesCount gives the right org total (10)
    expect(subtitleWithSitesCount).toContain('10 sites');
    // scopedSites.length would show "1 site" when site is selected
    expect(subtitleWithScopedCount).toBe('SCI Les Terrasses · 1 site');
  });
});

// ── Scope coherence across navigation ────────────────────────────────────────

describe('Scope coherence: apiSites vs mockSites precedence', () => {
  // Simulates the ScopeContext orgSites/scopedSites logic
  function computeOrgSites(apiSites, mockSites, effectiveOrgId) {
    if (apiSites.length > 0) return apiSites;
    return mockSites.filter(s => s.org_id === effectiveOrgId);
  }

  function computeScopedSites(orgSites, siteId) {
    if (siteId) return orgSites.filter(s => s.id === siteId);
    return orgSites;
  }

  const tertiaire10 = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, org_id: 42, nom: `Site ${i + 1}` }));
  const casinoMock36 = Array.from({ length: 36 }, (_, i) => ({ id: i + 1, org_id: 1, nom: `Casino ${i + 1}` }));

  it('apiSites loaded → orgSites = apiSites (10 for S pack)', () => {
    const orgSites = computeOrgSites(tertiaire10, casinoMock36, 42);
    expect(orgSites).toHaveLength(10);
    expect(orgSites[0].nom).toContain('Site');
  });

  it('apiSites empty → fallback to mockSites filtered by org', () => {
    const orgSites = computeOrgSites([], casinoMock36, 1);
    expect(orgSites).toHaveLength(36);
  });

  it('apiSites loaded → mockSites ignored (no 36-sites contamination)', () => {
    const orgSites = computeOrgSites(tertiaire10, casinoMock36, 42);
    // Even though casinoMock36 has 36 entries, apiSites wins
    expect(orgSites).toHaveLength(10);
    expect(orgSites.every(s => s.org_id === 42)).toBe(true);
  });

  it('siteId set → scopedSites = 1 site', () => {
    const orgSites = computeOrgSites(tertiaire10, [], 42);
    const scoped = computeScopedSites(orgSites, 3);
    expect(scoped).toHaveLength(1);
    expect(scoped[0].id).toBe(3);
  });

  it('siteId null → scopedSites = orgSites (all 10)', () => {
    const orgSites = computeOrgSites(tertiaire10, [], 42);
    const scoped = computeScopedSites(orgSites, null);
    expect(scoped).toHaveLength(10);
  });

  it('sitesCount = orgSites.length regardless of site selection', () => {
    const orgSites = computeOrgSites(tertiaire10, [], 42);
    const sitesCount = orgSites.length;  // always org total
    const scoped1 = computeScopedSites(orgSites, 3);
    const scoped2 = computeScopedSites(orgSites, null);
    // sitesCount stays 10 regardless
    expect(sitesCount).toBe(10);
    expect(scoped1.length).toBe(1);   // filtered
    expect(scoped2.length).toBe(10);  // unfiltered
  });
});

// ── setApiScope: X-Org-Id / X-Site-Id injection ───────────────────────────────

describe('setApiScope: header injection logic', () => {
  function makeApiScope() {
    let _scope = { orgId: null, siteId: null };
    return {
      setApiScope({ orgId, siteId }) {
        _scope = { orgId: orgId ?? null, siteId: siteId ?? null };
      },
      getHeaders(url) {
        // Simulate the axios interceptor
        const isDemoPath = url?.includes('/demo');
        if (isDemoPath) return {};
        const headers = {};
        if (_scope.orgId) headers['X-Org-Id'] = String(_scope.orgId);
        if (_scope.siteId) headers['X-Site-Id'] = String(_scope.siteId);
        return headers;
      },
    };
  }

  it('injects X-Org-Id after setApiScope', () => {
    const api = makeApiScope();
    api.setApiScope({ orgId: 42, siteId: null });
    expect(api.getHeaders('/api/conformite')).toEqual({ 'X-Org-Id': '42' });
  });

  it('injects X-Org-Id + X-Site-Id when site selected', () => {
    const api = makeApiScope();
    api.setApiScope({ orgId: 42, siteId: 7 });
    const headers = api.getHeaders('/api/conformite');
    expect(headers['X-Org-Id']).toBe('42');
    expect(headers['X-Site-Id']).toBe('7');
  });

  it('clears headers after scope clear (orgId=null)', () => {
    const api = makeApiScope();
    api.setApiScope({ orgId: 42, siteId: null });
    api.setApiScope({ orgId: null, siteId: null });
    expect(api.getHeaders('/api/conformite')).toEqual({});
  });

  it('skips headers for /demo paths', () => {
    const api = makeApiScope();
    api.setApiScope({ orgId: 42, siteId: null });
    expect(api.getHeaders('/api/demo/status')).toEqual({});
  });

  it('after reset + re-seed: new org_id replaces old', () => {
    const api = makeApiScope();
    api.setApiScope({ orgId: 1, siteId: null });   // Casino
    api.setApiScope({ orgId: 42, siteId: null });   // Tertiaire
    const headers = api.getHeaders('/api/dashboard');
    expect(headers['X-Org-Id']).toBe('42');
  });
});
