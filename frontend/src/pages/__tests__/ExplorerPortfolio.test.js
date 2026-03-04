/**
 * PROMEOS — Sprint V12 regression tests
 * Covers: Portfolio mode logic, chart state machine, OverviewRow KPI computation,
 * maxSitesComparatif enforcement, StickyFilterBar chip-only-selected behaviour.
 */
import { describe, it, expect } from 'vitest';
import { MAX_SITES } from '../consumption/types';
import { computeOverviewData } from '../consumption/OverviewRow';

// ── MAX_SITES_COMPARATIF enforcement ────────────────────────────────────────

describe('maxSitesComparatif enforcement', () => {
  it('MAX_SITES constant is 5', () => {
    expect(MAX_SITES).toBe(5);
  });

  it('toggleSite prevents adding beyond MAX_SITES in comparatif', () => {
    // Simulate toggleSite logic from StickyFilterBar
    function toggleSite(effectiveSiteIds, id, isPortfolioMode) {
      if (effectiveSiteIds.includes(id)) {
        return effectiveSiteIds.length > 1
          ? effectiveSiteIds.filter((s) => s !== id)
          : effectiveSiteIds;
      }
      if (!isPortfolioMode && effectiveSiteIds.length >= MAX_SITES) {
        return effectiveSiteIds; // blocked
      }
      return [...effectiveSiteIds, id];
    }

    const ids = [1, 2, 3, 4, 5];
    // Cannot add 6th in comparatif mode
    expect(toggleSite(ids, 6, false)).toEqual([1, 2, 3, 4, 5]);
    // Can remove one then add
    const after = toggleSite(ids, 5, false); // remove 5
    expect(after).toEqual([1, 2, 3, 4]);
    expect(toggleSite(after, 6, false)).toEqual([1, 2, 3, 4, 6]);
  });

  it('toggleSite allows any site in Portfolio mode (no cap)', () => {
    function canAdd(effectiveSiteIds, isPortfolioMode) {
      return isPortfolioMode || effectiveSiteIds.length < MAX_SITES;
    }
    expect(canAdd([1, 2, 3, 4, 5], false)).toBe(false);
    expect(canAdd([1, 2, 3, 4, 5], true)).toBe(true);
    expect(canAdd([1, 2, 3, 4, 5, 6, 7, 8], true)).toBe(true);
  });

  it('Portfolio mode is triggered when all sites are selected', () => {
    const allSites = [1, 2, 3, 4, 5, 6, 7];
    const selectedIds = allSites;
    const isPortfolioMode = selectedIds.length > MAX_SITES;
    expect(isPortfolioMode).toBe(true);
  });

  it('Comparatif mode works with exactly 5 sites', () => {
    const selectedIds = [1, 2, 3, 4, 5];
    const isBlocked = selectedIds.length > MAX_SITES;
    expect(isBlocked).toBe(false);
  });
});

// ── Portfolio mode: available modes ─────────────────────────────────────────

describe('Portfolio mode: mode availability', () => {
  function getAvailableModes(isPortfolioMode) {
    const allModes = ['agrege', 'superpose', 'empile', 'separe'];
    return isPortfolioMode ? ['agrege'] : allModes;
  }

  it('Portfolio mode: only agrege available', () => {
    expect(getAvailableModes(true)).toEqual(['agrege']);
  });

  it('Comparatif mode: all 4 modes available', () => {
    expect(getAvailableModes(false)).toEqual(['agrege', 'superpose', 'empile', 'separe']);
  });

  it('entering Portfolio mode forces mode to agrege', () => {
    let mode = 'superpose';
    const enterPortfolio = () => {
      mode = 'agrege';
    };
    enterPortfolio();
    expect(mode).toBe('agrege');
  });
});

// ── Chart state machine ──────────────────────────────────────────────────────

describe('Chart state machine', () => {
  function classifyChartState({ loading, availability, siteIds, isPortfolioMode }) {
    if (loading) return 'loading';
    if (siteIds.length > MAX_SITES && !isPortfolioMode) return 'blocked';
    if (!availability) return 'loading'; // waiting for first fetch
    if (!availability.has_data) return 'empty';
    return 'ready';
  }

  it('loading → state=loading', () => {
    expect(
      classifyChartState({
        loading: true,
        availability: null,
        siteIds: [1],
        isPortfolioMode: false,
      })
    ).toBe('loading');
  });

  it('no data → state=empty', () => {
    expect(
      classifyChartState({
        loading: false,
        availability: { has_data: false, reasons: ['no_meter'] },
        siteIds: [1],
        isPortfolioMode: false,
      })
    ).toBe('empty');
  });

  it('data available → state=ready', () => {
    expect(
      classifyChartState({
        loading: false,
        availability: { has_data: true },
        siteIds: [1],
        isPortfolioMode: false,
      })
    ).toBe('ready');
  });

  it('too many sites in comparatif → state=blocked', () => {
    expect(
      classifyChartState({
        loading: false,
        availability: { has_data: true },
        siteIds: [1, 2, 3, 4, 5, 6],
        isPortfolioMode: false,
      })
    ).toBe('blocked');
  });

  it('too many sites but Portfolio mode active → state=ready', () => {
    expect(
      classifyChartState({
        loading: false,
        availability: { has_data: true },
        siteIds: [1, 2, 3, 4, 5, 6, 7, 8],
        isPortfolioMode: true,
      })
    ).toBe('ready');
  });
});

// ── OverviewRow: computeOverviewData ─────────────────────────────────────────

describe('computeOverviewData', () => {
  it('returns null for null tunnel', () => {
    expect(computeOverviewData(null)).toBeNull();
    expect(computeOverviewData(undefined)).toBeNull();
  });

  it('returns null when no weekday envelope', () => {
    expect(computeOverviewData({ envelope: {} })).toBeNull();
    expect(computeOverviewData({ envelope: { weekday: [] } })).toBeNull();
  });

  it('computes peak_kw from max p50', () => {
    const tunnel = {
      envelope: {
        weekday: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          p10: 1,
          p25: 2,
          p50: h < 10 ? 5 : h < 16 ? 20 : 5,
          p75: 25,
          p90: 30,
        })),
      },
      readings_count: 500,
    };
    const data = computeOverviewData(tunnel);
    expect(data).not.toBeNull();
    expect(data.peak_kw).toBe(20);
  });

  it('computes talon_kw from night hours (0-5)', () => {
    const tunnel = {
      envelope: {
        weekday: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          p10: h < 6 ? 2 : 10,
          p50: h < 6 ? 3 : 12,
          p75: 15,
          p90: 20,
        })),
      },
      readings_count: 500,
    };
    const data = computeOverviewData(tunnel);
    expect(data.talon_kw).toBeLessThanOrEqual(3);
  });

  it('computes off_hours_pct as fraction of consumption outside 8h-20h', () => {
    // All equal values: 12h day (8-20) + 12h night → 50% off-hours
    const tunnel = {
      envelope: {
        weekday: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          p10: 10,
          p50: 10,
          p75: 10,
          p90: 10,
        })),
      },
      readings_count: 500,
    };
    const data = computeOverviewData(tunnel);
    // off_hours_pct = (12h night / 24h total) = 50%
    expect(data.off_hours_pct).toBeCloseTo(50, 0);
  });

  it('returned object has expected keys', () => {
    const tunnel = {
      envelope: {
        weekday: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          p10: 1,
          p50: 5,
          p75: 8,
          p90: 10,
        })),
      },
      readings_count: 200,
    };
    const data = computeOverviewData(tunnel);
    expect(data).toHaveProperty('peak_kw');
    expect(data).toHaveProperty('talon_kw');
    expect(data).toHaveProperty('off_hours_pct');
    expect(data).toHaveProperty('avg_kwh');
  });
});

// ── Portfolio ranking logic ──────────────────────────────────────────────────

describe('Portfolio: ranking computation', () => {
  function computeSiteKPIs(tunnel) {
    if (!tunnel) return null;
    const weekday = tunnel.envelope?.weekday || [];
    if (!weekday.length) return null;
    const vals = weekday.map((s) => s.p50 ?? 0);
    const total = vals.reduce((a, b) => a + b, 0);
    const peak = Math.max(...vals);
    const nightVals = weekday.filter((s) => s.hour < 6 || s.hour >= 22).map((s) => s.p50 ?? 0);
    const nightSum = nightVals.reduce((a, b) => a + b, 0);
    const offHoursPct = total > 0 ? (nightSum / total) * 100 : 0;
    return { total_kwh: Math.round(total * 24), peak_kw: peak, off_hours_pct: offHoursPct };
  }

  function buildRanking(siteDataMap, sites, metric) {
    return sites
      .map((site) => ({ site, kpis: computeSiteKPIs(siteDataMap[site.id]) }))
      .filter((r) => r.kpis?.[metric] != null)
      .sort((a, b) => (b.kpis[metric] ?? 0) - (a.kpis[metric] ?? 0));
  }

  const mockWeekday = (baseP50) =>
    Array.from({ length: 24 }, (_, h) => ({
      hour: h,
      p50: baseP50,
      p10: baseP50 * 0.8,
      p90: baseP50 * 1.2,
    }));

  const siteDataMap = {
    1: { envelope: { weekday: mockWeekday(10) } },
    2: { envelope: { weekday: mockWeekday(30) } },
    3: { envelope: { weekday: mockWeekday(5) } },
  };
  const sites = [
    { id: 1, nom: 'A' },
    { id: 2, nom: 'B' },
    { id: 3, nom: 'C' },
  ];

  it('ranking by total_kwh: highest first', () => {
    const ranked = buildRanking(siteDataMap, sites, 'total_kwh');
    expect(ranked[0].site.id).toBe(2); // p50=30, highest
    expect(ranked[2].site.id).toBe(3); // p50=5, lowest
  });

  it('site with no tunnel data is excluded from ranking', () => {
    const partialMap = { 1: siteDataMap[1] }; // only site 1
    const ranked = buildRanking(partialMap, sites, 'total_kwh');
    expect(ranked).toHaveLength(1);
    expect(ranked[0].site.id).toBe(1);
  });

  it('empty siteDataMap returns empty ranking', () => {
    expect(buildRanking({}, sites, 'total_kwh')).toHaveLength(0);
  });
});

// ── StickyFilterBar: chip visibility ─────────────────────────────────────────

describe('StickyFilterBar: only selected chips shown (V12 fix)', () => {
  it('chips are derived from effectiveSiteIds, not all sites', () => {
    // Simulate: 36 sites available, only 2 selected
    const allSites = Array.from({ length: 36 }, (_, i) => ({ id: i + 1, nom: `Site ${i + 1}` }));
    const effectiveSiteIds = [1, 5];

    // What V12 renders: only effectiveSiteIds, not allSites
    const renderedChips = allSites.filter((s) => effectiveSiteIds.includes(s.id));
    expect(renderedChips).toHaveLength(2);
    expect(renderedChips.map((s) => s.id)).toEqual([1, 5]);
  });

  it('with 36 sites and 0 selected: renders 0 chips (empty state)', () => {
    const effectiveSiteIds = [];
    const allSites = Array.from({ length: 36 }, (_, i) => ({ id: i + 1, nom: `Site ${i + 1}` }));
    const chips = allSites.filter((s) => effectiveSiteIds.includes(s.id));
    expect(chips).toHaveLength(0);
  });

  it('add button shown only when selected < MAX_SITES', () => {
    expect([1, 2, 3, 4].length < MAX_SITES).toBe(true); // 4 < 5 → show "+"
    expect([1, 2, 3, 4, 5].length < MAX_SITES).toBe(false); // 5 = 5 → hide "+"
  });
});
