/**
 * PROMEOS — DashboardEssentials.test.js (Sprint WOW Phase 7.0 + Cockpit Sprint)
 * Pure-logic tests — no DOM, no React.
 */
import { describe, it, expect } from 'vitest';
import {
  buildWatchlist,
  checkConsistency,
  buildTopSites,
  buildOpportunities,
  buildBriefing,
} from '../../models/dashboardEssentials';
import { formatPercentFR } from '../../utils/format';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const makeKpis = (overrides = {}) => ({
  total: 5,
  conformes: 3,
  nonConformes: 0,
  aRisque: 0,
  risqueTotal: 0,
  couvertureDonnees: 80,
  ...overrides,
});

const makeSites = (n = 5, overrides = {}) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    nom: `Site ${i + 1}`,
    ville: 'Lyon',
    statut_conformite: 'conforme',
    conso_kwh_an: 10000 + i * 1000,
    risque_eur: 0,
    surface_m2: 500,
    ...overrides,
  }));

// ── describe: buildWatchlist ──────────────────────────────────────────────────

describe('buildWatchlist', () => {
  it('nonConformes=3 → item severity=critical, path=/conformite', () => {
    const kpis = makeKpis({ nonConformes: 3, total: 5 });
    const result = buildWatchlist(kpis, []);
    const item = result.find(i => i.id === 'non_conformes');
    expect(item).toBeDefined();
    expect(item.severity).toBe('critical');
    expect(item.path).toBe('/conformite');
  });

  it('sites without conso_kwh_an → item severity=warn, path=/consommations/import', () => {
    const kpis = makeKpis({ couvertureDonnees: 0, total: 5 });
    const sites = makeSites(5, { conso_kwh_an: 0 });
    const result = buildWatchlist(kpis, sites);
    const item = result.find(i => i.id === 'no_conso_data');
    expect(item).toBeDefined();
    expect(item.severity).toBe('warn');
    expect(item.path).toBe('/consommations/import');
  });

  it('all conformes + all have conso data → returns empty array', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 100 });
    const sites = makeSites(5);
    const result = buildWatchlist(kpis, sites);
    expect(result).toHaveLength(0);
  });

  it('6 conditions triggered → result is capped at 5 items', () => {
    // Force all 4 conditions + extra by having non-conformes, a_risque,
    // sites without data, and multiple kpis thresholds
    const kpis = makeKpis({
      nonConformes: 2,
      aRisque: 3,
      couvertureDonnees: 20,
      total: 10,
    });
    // Sites without data triggers condition #3 (overrides #4 since length > 0)
    const sites = makeSites(10, { conso_kwh_an: 0 });
    const result = buildWatchlist(kpis, sites);
    expect(result.length).toBeLessThanOrEqual(5);
  });
});

// ── describe: checkConsistency ────────────────────────────────────────────────

describe('checkConsistency', () => {
  it('conformeRate=100% + couvertureDonnees<30 + total>0 → !ok, issue code=all_conformes_low_data', () => {
    const kpis = makeKpis({ conformes: 5, total: 5, nonConformes: 0, couvertureDonnees: 10 });
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(false);
    expect(result.issues).toHaveLength(1);
    expect(result.issues[0].code).toBe('all_conformes_low_data');
  });

  it('couvertureDonnees=0 + total>0 → !ok, issue code=no_data_coverage', () => {
    const kpis = makeKpis({ couvertureDonnees: 0, total: 5 });
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(false);
    const issue = result.issues.find(i => i.code === 'no_data_coverage');
    expect(issue).toBeDefined();
  });

  it('healthy state (data + partial conformity) → ok=true, issues=[]', () => {
    const kpis = makeKpis({ conformes: 3, total: 5, couvertureDonnees: 80 });
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(true);
    expect(result.issues).toHaveLength(0);
  });
});

// ── describe: buildTopSites ───────────────────────────────────────────────────

describe('buildTopSites', () => {
  it('worst 5: non-conformes sorted by risque_eur DESC', () => {
    const sites = [
      { id: 1, nom: 'A', ville: 'Paris', statut_conformite: 'non_conforme', risque_eur: 5000, conso_kwh_an: 0 },
      { id: 2, nom: 'B', ville: 'Lyon', statut_conformite: 'non_conforme', risque_eur: 20000, conso_kwh_an: 0 },
      { id: 3, nom: 'C', ville: 'Lille', statut_conformite: 'non_conforme', risque_eur: 12000, conso_kwh_an: 0 },
    ];
    const { worst } = buildTopSites(sites);
    expect(worst[0].risque_eur).toBe(20000);
    expect(worst[1].risque_eur).toBe(12000);
    expect(worst[2].risque_eur).toBe(5000);
  });

  it('best 5: conformes only', () => {
    const sites = [
      { id: 1, nom: 'A', statut_conformite: 'conforme', conso_kwh_an: 1000, risque_eur: 0, ville: 'Paris' },
      { id: 2, nom: 'B', statut_conformite: 'non_conforme', conso_kwh_an: 2000, risque_eur: 500, ville: 'Lyon' },
      { id: 3, nom: 'C', statut_conformite: 'conforme', conso_kwh_an: 500, risque_eur: 0, ville: 'Lille' },
    ];
    const { best } = buildTopSites(sites);
    expect(best.every(s => s.statut_conformite === 'conforme')).toBe(true);
    expect(best).toHaveLength(2);
  });

  it('empty sites → both arrays empty', () => {
    const { worst, best } = buildTopSites([]);
    expect(worst).toHaveLength(0);
    expect(best).toHaveLength(0);
  });

  it('only 2 non-conformes → worst has length 2 (not padded to 5)', () => {
    const sites = [
      { id: 1, nom: 'A', statut_conformite: 'non_conforme', risque_eur: 1000, conso_kwh_an: 0, ville: 'Lyon' },
      { id: 2, nom: 'B', statut_conformite: 'non_conforme', risque_eur: 2000, conso_kwh_an: 0, ville: 'Lyon' },
    ];
    const { worst } = buildTopSites(sites);
    expect(worst).toHaveLength(2);
  });
});

// ── describe: buildOpportunities ──────────────────────────────────────────────

describe('buildOpportunities', () => {
  it('isExpert=false → returns []', () => {
    const kpis = makeKpis({ couvertureDonnees: 30, nonConformes: 5, risqueTotal: 50000 });
    const result = buildOpportunities(kpis, makeSites(5), { isExpert: false });
    expect(result).toHaveLength(0);
  });

  it('isExpert=true + couvertureDonnees<80 → at least 1 opportunity (complete_data)', () => {
    const kpis = makeKpis({ couvertureDonnees: 40, total: 5, nonConformes: 0, risqueTotal: 0 });
    const result = buildOpportunities(kpis, makeSites(5), { isExpert: true });
    const opp = result.find(o => o.id === 'complete_data');
    expect(opp).toBeDefined();
    expect(opp.path).toBe('/consommations/explorer');
  });

  it('result is capped at 3 items even when all 3 conditions trigger', () => {
    const kpis = makeKpis({
      couvertureDonnees: 20,
      nonConformes: 5,
      risqueTotal: 50000,
      total: 10,
    });
    const result = buildOpportunities(kpis, makeSites(10), { isExpert: true });
    expect(result.length).toBeLessThanOrEqual(3);
  });
});

// ── describe: buildBriefing ───────────────────────────────────────────────────

describe('buildBriefing', () => {
  it('all-green state (no issues) → returns empty array', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 100 });
    const result = buildBriefing(kpis, []);
    expect(result).toHaveLength(0);
  });

  it('nonConformes > 0 → first item id=non_conformes, severity=critical', () => {
    const kpis = makeKpis({ nonConformes: 2, aRisque: 0, couvertureDonnees: 100 });
    const result = buildBriefing(kpis, []);
    const item = result.find(i => i.id === 'non_conformes');
    expect(item).toBeDefined();
    expect(item.severity).toBe('critical');
    expect(item.path).toBe('/conformite');
  });

  it('aRisque > 0 → item id=a_risque, severity=high', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 3, couvertureDonnees: 100 });
    const result = buildBriefing(kpis, []);
    const item = result.find(i => i.id === 'a_risque');
    expect(item).toBeDefined();
    expect(item.severity).toBe('high');
    expect(item.path).toBe('/actions');
  });

  it('couvertureDonnees < 80 and total > 0 → item id=coverage, severity=warn', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 50, total: 4 });
    const result = buildBriefing(kpis, []);
    const item = result.find(i => i.id === 'coverage');
    expect(item).toBeDefined();
    expect(item.severity).toBe('warn');
    expect(item.path).toBe('/consommations/import');
  });

  it('all 3 conditions trigger → capped at 3 items', () => {
    const kpis = makeKpis({ nonConformes: 2, aRisque: 1, couvertureDonnees: 40, total: 5 });
    const result = buildBriefing(kpis, []);
    expect(result.length).toBeLessThanOrEqual(3);
  });

  it('couvertureDonnees >= 80 → no coverage item', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 80, total: 5 });
    const result = buildBriefing(kpis, []);
    expect(result.find(i => i.id === 'coverage')).toBeUndefined();
  });
});

// ── describe: formatPercentFR ─────────────────────────────────────────────────

describe('formatPercentFR', () => {
  it('80 → "80 %" (with FR locale spacing)', () => {
    const result = formatPercentFR(80);
    // Intl.NumberFormat inserts a narrow no-break space in some environments
    expect(result).toMatch(/80\s?%/);
  });

  it('0 → "0 %"', () => {
    const result = formatPercentFR(0);
    expect(result).toMatch(/0\s?%/);
  });

  it('100 → "100 %"', () => {
    const result = formatPercentFR(100);
    expect(result).toMatch(/100\s?%/);
  });

  it('null → "—"', () => {
    expect(formatPercentFR(null)).toBe('—');
  });

  it('NaN → "—"', () => {
    expect(formatPercentFR(NaN)).toBe('—');
  });
});

// ── describe: copy hygiene ────────────────────────────────────────────────────

describe('copy hygiene — no raw \\u00a0 escape sequences in model strings', () => {
  const NBSP_ESCAPE = '\u00a0'; // actual non-breaking space — check strings don't use raw esc

  it('buildWatchlist labels contain no raw \\u00a0 literal escape (6-char sequence)', () => {
    const kpis = makeKpis({ nonConformes: 2, aRisque: 1, couvertureDonnees: 30, total: 5 });
    const sites = makeSites(5, { conso_kwh_an: 0 });
    const watchlist = buildWatchlist(kpis, sites);
    for (const item of watchlist) {
      // Check the label doesn't contain the 6-char literal escape sequence
      // (which would appear as text in output if not processed)
      expect(item.label).not.toContain('\\u00a0');
    }
  });

  it('buildBriefing labels contain no raw \\u00a0 literal escape', () => {
    const kpis = makeKpis({ nonConformes: 2, aRisque: 1, couvertureDonnees: 40, total: 5 });
    const result = buildBriefing(kpis, []);
    for (const item of result) {
      expect(item.label).not.toContain('\\u00a0');
    }
  });

  it('buildOpportunities subs use formatPercentFR (contain "%" not raw escape)', () => {
    const kpis = makeKpis({ couvertureDonnees: 40, total: 5, nonConformes: 0, risqueTotal: 0 });
    const result = buildOpportunities(kpis, makeSites(5), { isExpert: true });
    const opp = result.find(o => o.id === 'complete_data');
    expect(opp?.sub).toContain('%');
    expect(opp?.sub).not.toContain('\\u00a0');
  });
});
