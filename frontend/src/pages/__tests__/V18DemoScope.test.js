/**
 * PROMEOS — Sprint V18: Demo Scope Coherence
 * Tests couvrant:
 *   - sitesLoading state transitions (RC1 fix)
 *   - requestId stale-response guard (RC3 fix)
 *   - getEffectiveSiteIds helper with loading guard
 *   - ScopeSummary loading label logic (V18-C)
 */
import { describe, it, expect } from 'vitest';

// ── 1. sitesLoading state transitions ─────────────────────────────────────────

describe('sitesLoading state transitions (V18-A RC1)', () => {
  // Simulates the V18 useEffect logic in ScopeContext
  function simulateSitesEffect(effectiveOrgId, apiResponse) {
    const states = [];
    states.push({ sitesLoading: false, apiSites: [] }); // initial

    if (!effectiveOrgId) {
      states.push({ sitesLoading: false, apiSites: [] }); // early return
      return states;
    }

    states.push({ sitesLoading: true, apiSites: [] }); // loading started

    if (apiResponse instanceof Error) {
      states.push({ sitesLoading: false, apiSites: [] }); // error → loading=false
    } else {
      const list = Array.isArray(apiResponse)
        ? apiResponse
        : apiResponse.sites || apiResponse.items || [];
      states.push({ sitesLoading: false, apiSites: list }); // success
    }

    return states;
  }

  it('sitesLoading starts false at initialization', () => {
    const states = simulateSitesEffect(null, null);
    expect(states[0].sitesLoading).toBe(false);
  });

  it('sitesLoading becomes true when effectiveOrgId is set, then false on success', () => {
    const sites = [{ id: 1 }, { id: 2 }, { id: 3 }];
    const states = simulateSitesEffect(42, sites);
    expect(states[1].sitesLoading).toBe(true);   // started
    expect(states[2].sitesLoading).toBe(false);  // done
    expect(states[2].apiSites).toHaveLength(3);
  });

  it('sitesLoading returns false on API failure, apiSites stays []', () => {
    const states = simulateSitesEffect(42, new Error('Network error'));
    expect(states[1].sitesLoading).toBe(true);   // started
    expect(states[2].sitesLoading).toBe(false);  // done (error path)
    expect(states[2].apiSites).toHaveLength(0);
  });

  it('null effectiveOrgId → sitesLoading stays false, no loading spinner', () => {
    const states = simulateSitesEffect(null, []);
    expect(states.every(s => s.sitesLoading === false)).toBe(true);
  });
});

// ── 2. requestId stale-response guard (RC3) ────────────────────────────────────

describe('requestId stale-response guard (V18-A RC3)', () => {
  // Simulates the _fetchId.current counter pattern
  function makeRequestGuard() {
    let currentId = 0;
    return {
      newRequest() { return ++currentId; },
      isFresh(myId) { return myId === currentId; },
      currentId: () => currentId,
    };
  }

  it('stale response (old requestId) is ignored', () => {
    const guard = makeRequestGuard();
    const req1 = guard.newRequest(); // org switch 1 → id=1
    const req2 = guard.newRequest(); // org switch 2 → id=2

    // req1 resolves last (stale)
    expect(guard.isFresh(req1)).toBe(false); // id=1 !== currentId=2 → ignore
  });

  it('fresh response (latest requestId) is accepted', () => {
    const guard = makeRequestGuard();
    const req1 = guard.newRequest();
    const req2 = guard.newRequest();

    // req2 resolves (fresh)
    expect(guard.isFresh(req2)).toBe(true); // id=2 === currentId=2 → accept
  });

  it('only one request outstanding: stale org response cannot overwrite fresh', () => {
    const guard = makeRequestGuard();
    let apiSites = [];

    const heliosReqId = guard.newRequest();   // org=Helios, id=1
    const tertiReqId  = guard.newRequest();   // org=Tertiaire, id=2

    // Helios API responds (stale)
    const heliosSites = Array.from({ length: 5 }, (_, i) => ({ id: i + 1 }));
    if (guard.isFresh(heliosReqId)) {
      apiSites = heliosSites; // should NOT execute
    }

    // Tertiaire API responds (fresh)
    const tertiSites = Array.from({ length: 10 }, (_, i) => ({ id: i + 101 }));
    if (guard.isFresh(tertiReqId)) {
      apiSites = tertiSites; // should execute
    }

    expect(apiSites).toHaveLength(10);  // Tertiaire wins, no stale-Helios contamination
    expect(apiSites).toBe(tertiSites);
  });

  it('rapid org switches: only the last request wins', () => {
    const guard = makeRequestGuard();
    let accepted = [];

    // 5 rapid org switches
    const ids = Array.from({ length: 5 }, () => guard.newRequest());

    // All responses arrive in reverse order
    [...ids].reverse().forEach((id, i) => {
      if (guard.isFresh(id)) {
        accepted.push(id);
      }
    });

    expect(accepted).toHaveLength(1);          // only one accepted
    expect(accepted[0]).toBe(ids[ids.length - 1]); // the last one
  });
});

// ── 3. getEffectiveSiteIds helper ─────────────────────────────────────────────

describe('getEffectiveSiteIds helper (V18-B guard)', () => {
  // Simulates the "what sites should I use?" logic in consumer pages
  function getEffectiveSiteIds({ sitesLoading, orgSites, selectedSiteId }) {
    if (sitesLoading) return null; // signal: "wait, don't render"
    if (selectedSiteId) {
      const found = orgSites.find(s => s.id === selectedSiteId);
      return found ? [selectedSiteId] : null;
    }
    if (orgSites.length === 0) return []; // genuinely empty org
    return orgSites.map(s => s.id);
  }

  const tertiaire10 = Array.from({ length: 10 }, (_, i) => ({ id: i + 1 }));

  it('returns null when sitesLoading=true (guard prevents rendering)', () => {
    const ids = getEffectiveSiteIds({ sitesLoading: true, orgSites: tertiaire10, selectedSiteId: null });
    expect(ids).toBeNull();
  });

  it('returns [siteId] when site selected and found in orgSites', () => {
    const ids = getEffectiveSiteIds({ sitesLoading: false, orgSites: tertiaire10, selectedSiteId: 5 });
    expect(ids).toEqual([5]);
  });

  it('returns all 10 IDs when siteId=null and 10 sites loaded', () => {
    const ids = getEffectiveSiteIds({ sitesLoading: false, orgSites: tertiaire10, selectedSiteId: null });
    expect(ids).toHaveLength(10);
    expect(ids).toContain(1);
    expect(ids).toContain(10);
  });

  it('returns [] (genuinely empty) when loaded but org has no sites', () => {
    const ids = getEffectiveSiteIds({ sitesLoading: false, orgSites: [], selectedSiteId: null });
    expect(ids).toEqual([]);
    expect(ids).not.toBeNull(); // distinct from loading state
  });
});

// ── 4. ScopeSummary loading label logic (V18-C) ────────────────────────────────

describe('ScopeSummary loading label (V18-C)', () => {
  // Simulates the V18 ScopeSummary rendering logic
  function buildScopeSummaryLabel({ orgNom, sitesLoading, selectedSiteId, scopeLabel, sitesCount, showCount = true }) {
    if (!orgNom) return null;
    if (sitesLoading) {
      return `${orgNom} — Chargement\u2026`; // loading state
    }
    if (selectedSiteId) {
      return `${orgNom} — ${scopeLabel}`;
    }
    return `${orgNom} — Tous les sites${showCount && sitesCount ? ` (${sitesCount})` : ''}`;
  }

  it('shows "Org — Chargement…" while sitesLoading=true', () => {
    const label = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses',
      sitesLoading: true,
      selectedSiteId: null,
      scopeLabel: 'Tous les sites',
      sitesCount: 0,
    });
    expect(label).toBe('SCI Les Terrasses — Chargement\u2026');
  });

  it('shows "Org — Site : Name" when loaded and site selected', () => {
    const label = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses',
      sitesLoading: false,
      selectedSiteId: 3,
      scopeLabel: 'Site\u00a0: Hotel Ibis',
      sitesCount: 10,
    });
    expect(label).toBe('SCI Les Terrasses — Site\u00a0: Hotel Ibis');
  });

  it('shows "Org — Tous les sites (10)" when loaded, no site selected', () => {
    const label = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses',
      sitesLoading: false,
      selectedSiteId: null,
      scopeLabel: 'Tous les sites',
      sitesCount: 10,
    });
    expect(label).toBe('SCI Les Terrasses — Tous les sites (10)');
  });

  it('loading state hides count (does not flash "0 sites" or "(0)")', () => {
    const label = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses',
      sitesLoading: true,
      selectedSiteId: null,
      scopeLabel: 'Tous les sites',
      sitesCount: 0,
    });
    expect(label).not.toContain('(0)');
    expect(label).not.toContain('0 site');
    expect(label).toContain('Chargement');
  });

  it('loading label is stable even when sitesCount becomes available later', () => {
    // During loading, sitesCount might be 0 (still fetching) — label must say "Chargement"
    const labelWhileLoading = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses', sitesLoading: true, selectedSiteId: null,
      scopeLabel: 'Tous les sites', sitesCount: 0,
    });
    const labelAfterLoad = buildScopeSummaryLabel({
      orgNom: 'SCI Les Terrasses', sitesLoading: false, selectedSiteId: null,
      scopeLabel: 'Tous les sites', sitesCount: 10,
    });
    expect(labelWhileLoading).toContain('Chargement');
    expect(labelAfterLoad).toContain('(10)');
    expect(labelWhileLoading).not.toBe(labelAfterLoad); // labels differ correctly
  });
});
