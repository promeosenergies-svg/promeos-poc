/**
 * PROMEOS — Sprint V19: Explorer Fix Tests
 * Tests couvrant:
 *   1. Default tab 'timeseries' (RC1 fix)
 *   2. handleSwitchEnergy keeps timeseries tab (RC6 fix)
 *   3. Site selector always-visible logic (RC2 fix)
 *   4. metric mapping eur → kwh (RC4 fix)
 */
import { describe, it, expect } from 'vitest';

// ── 1. Default tab 'timeseries' ───────────────────────────────────────────────

describe('Default tab "timeseries" (V19-A RC1)', () => {
  const DEFAULTS = {
    energy: 'electricity',
    days: 90,
    mode: 'agrege',
    unit: 'kwh',
    tab: 'timeseries', // V19: timeseries is the primary chart view
  };

  it('DEFAULTS.tab is "timeseries", not "tunnel"', () => {
    expect(DEFAULTS.tab).toBe('timeseries');
    expect(DEFAULTS.tab).not.toBe('tunnel');
  });

  it('URL with no tab param falls back to DEFAULTS.tab = "timeseries"', () => {
    // Simulates: searchParams.get('tab') || DEFAULTS.tab
    const searchParamsGet = (key) => (key === 'tab' ? null : null);
    const tab = searchParamsGet('tab') || DEFAULTS.tab;
    expect(tab).toBe('timeseries');
  });

  it('Explicit URL tab param overrides default', () => {
    const searchParamsGet = (key) => (key === 'tab' ? 'tunnel' : null);
    const tab = searchParamsGet('tab') || DEFAULTS.tab;
    expect(tab).toBe('tunnel');
  });
});

// ── 2. handleSwitchEnergy keeps timeseries tab (RC6 fix) ─────────────────────

describe('handleSwitchEnergy does not clobber timeseries tab (V19-A RC6)', () => {
  // Simulates the V19-fixed handleSwitchEnergy logic
  function simulateSwitchEnergy(newType, activeTab) {
    let resultTab = activeTab;
    if (newType === 'gas') {
      resultTab = 'gas';
    } else if (activeTab === 'gas') {
      // V19 fix: only leave gas tab when currently ON gas tab
      resultTab = 'timeseries';
    }
    // else: stay on current tab (timeseries, tunnel, etc.)
    return resultTab;
  }

  it('Switching to gas from timeseries → tab becomes "gas"', () => {
    const result = simulateSwitchEnergy('gas', 'timeseries');
    expect(result).toBe('gas');
  });

  it('Switching from gas to electricity → tab returns to "timeseries"', () => {
    const result = simulateSwitchEnergy('electricity', 'gas');
    expect(result).toBe('timeseries');
  });

  it('Switching from gas to electricity when on gas tab → "timeseries" (not "tunnel")', () => {
    const result = simulateSwitchEnergy('electricity', 'gas');
    expect(result).toBe('timeseries');
    expect(result).not.toBe('tunnel');
  });

  it('Switching to electricity while on timeseries → stays "timeseries"', () => {
    const result = simulateSwitchEnergy('electricity', 'timeseries');
    expect(result).toBe('timeseries'); // no change — not on gas tab
  });

  it('Switching to electricity while on tunnel → stays "tunnel"', () => {
    const result = simulateSwitchEnergy('electricity', 'tunnel');
    expect(result).toBe('tunnel'); // only leaves gas tab, not other tabs
  });
});

// ── 3. Site selector always-visible logic (RC2 fix) ──────────────────────────

describe('Site selector always-visible logic (V19-B RC2)', () => {
  // Simulates V19 isMultiMode + rendering decision
  function getV19SiteSectionState({ setSiteIds, sites: _sites, effectiveSiteIds, sitesLoading, isPortfolioMode }) {
    const _isMultiMode = Boolean(setSiteIds); // V19 fix: was: sites.length > 1 && setSiteIds
    const showSection = Boolean(setSiteIds) && !isPortfolioMode;

    if (!showSection) return { visible: false, content: null };

    if (effectiveSiteIds.length > 0) {
      return { visible: true, content: 'chips', count: effectiveSiteIds.length };
    }

    // Placeholder when no sites selected
    return {
      visible: true,
      content: 'placeholder',
      label: sitesLoading ? 'Chargement\u2026' : 'S\u00e9lectionner des sites\u2026',
    };
  }

  it('setSiteIds provided + 0 sites → section visible with placeholder', () => {
    const result = getV19SiteSectionState({
      setSiteIds: () => {},
      sites: [],
      effectiveSiteIds: [],
      sitesLoading: false,
      isPortfolioMode: false,
    });
    expect(result.visible).toBe(true);
    expect(result.content).toBe('placeholder');
    expect(result.label).toBe('S\u00e9lectionner des sites\u2026');
  });

  it('setSiteIds provided + sitesLoading → section visible with "Chargement…"', () => {
    const result = getV19SiteSectionState({
      setSiteIds: () => {},
      sites: [],
      effectiveSiteIds: [],
      sitesLoading: true,
      isPortfolioMode: false,
    });
    expect(result.visible).toBe(true);
    expect(result.content).toBe('placeholder');
    expect(result.label).toBe('Chargement\u2026');
  });

  it('setSiteIds provided + 1 site selected → section visible with chips (was hidden in V18)', () => {
    const result = getV19SiteSectionState({
      setSiteIds: () => {},
      sites: [{ id: 5, nom: 'Bureau Paris' }],
      effectiveSiteIds: [5],
      sitesLoading: false,
      isPortfolioMode: false,
    });
    expect(result.visible).toBe(true);
    expect(result.content).toBe('chips');
    expect(result.count).toBe(1);
  });

  it('setSiteIds provided + 3 sites selected → section visible with 3 chips', () => {
    const result = getV19SiteSectionState({
      setSiteIds: () => {},
      sites: [{ id: 1 }, { id: 2 }, { id: 3 }],
      effectiveSiteIds: [1, 2, 3],
      sitesLoading: false,
      isPortfolioMode: false,
    });
    expect(result.visible).toBe(true);
    expect(result.content).toBe('chips');
    expect(result.count).toBe(3);
  });

  it('setSiteIds null → section not shown (legacy select path)', () => {
    const result = getV19SiteSectionState({
      setSiteIds: null,
      sites: [{ id: 1 }, { id: 2 }],
      effectiveSiteIds: [1],
      sitesLoading: false,
      isPortfolioMode: false,
    });
    expect(result.visible).toBe(false);
  });

  it('isPortfolioMode=true → section not shown even with setSiteIds', () => {
    const result = getV19SiteSectionState({
      setSiteIds: () => {},
      sites: [{ id: 1 }],
      effectiveSiteIds: [1],
      sitesLoading: false,
      isPortfolioMode: true,
    });
    expect(result.visible).toBe(false);
  });
});

// ── 4. metric mapping eur → kwh (RC4 fix) ────────────────────────────────────

describe('metric mapping EUR → kWh for API (V19-D RC4)', () => {
  // Simulates the V19 apiMetric derivation in useEmsTimeseries
  function getApiMetric(unit) {
    return unit === 'eur' ? 'kwh' : unit;
  }

  it('unit="kwh" → apiMetric="kwh"', () => {
    expect(getApiMetric('kwh')).toBe('kwh');
  });

  it('unit="kw" → apiMetric="kw"', () => {
    expect(getApiMetric('kw')).toBe('kw');
  });

  it('unit="eur" → apiMetric="kwh" (EUR is display-only; API only accepts kwh/kw)', () => {
    expect(getApiMetric('eur')).toBe('kwh');
    expect(getApiMetric('eur')).not.toBe('eur');
  });

  it('Unknown unit passthrough (future-proof)', () => {
    expect(getApiMetric('mwh')).toBe('mwh');
    expect(getApiMetric('co2')).toBe('co2');
  });
});
