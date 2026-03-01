/**
 * PROMEOS — Sprint Cockpit V2 — Pure-logic tests
 * Covers:
 *   - buildTodayActions   (dédup, tri sévérité, max 5)
 *   - buildExecutiveSummary (bullets décideur)
 *   - buildExecutiveKpis  (4 tuiles, statuts, format)
 *
 * All tests run in Vitest node environment (no DOM).
 */
import { describe, it, expect } from 'vitest';
import {
  buildTodayActions,
  buildExecutiveSummary,
  buildExecutiveKpis,
} from '../../models/dashboardEssentials';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeKpis(overrides = {}) {
  return {
    total: 10,
    conformes: 7,
    nonConformes: 2,
    aRisque: 1,
    risqueTotal: 15000,
    couvertureDonnees: 70,
    ...overrides,
  };
}

function _makeWatchlist() {
  return [
    { id: 'non_conformes', label: '2 sites non conformes', severity: 'critical', path: '/conformite', cta: 'Voir conformité' },
    { id: 'a_risque', label: '1 site à risque', severity: 'high', path: '/actions', cta: "Plan d'action" },
    { id: 'no_conso_data', label: 'Données manquantes', severity: 'warn', path: '/consommations/import', cta: 'Importer' },
  ];
}

function makeSites(n = 10) {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    nom: `Site ${i + 1}`,
    statut_conformite: i < 7 ? 'conforme' : i < 9 ? 'non_conforme' : 'a_risque',
    risque_eur: i < 7 ? 0 : (i + 1) * 1000,
    conso_kwh_an: i < 7 ? 100000 + i * 1000 : 0,
  }));
}

// ── buildTodayActions ─────────────────────────────────────────────────────────

describe('buildTodayActions', () => {
  it('returns empty array when watchlist and opportunities are empty', () => {
    const result = buildTodayActions(makeKpis(), [], []);
    expect(result).toHaveLength(0);
  });

  it('returns watchlist items sorted by severity', () => {
    const watchlist = [
      { id: 'low_item', label: 'Low priority', severity: 'medium', path: '/x', cta: 'X' },
      { id: 'critical_item', label: 'Critical', severity: 'critical', path: '/y', cta: 'Y' },
    ];
    const result = buildTodayActions(makeKpis(), watchlist, []);
    expect(result[0].id).toBe('critical_item');
    expect(result[1].id).toBe('low_item');
  });

  it('deduplicates items with the same id across watchlist and opportunities', () => {
    const watchlist = [{ id: 'shared_id', label: 'In watchlist', severity: 'warn', path: '/a', cta: 'A' }];
    const opportunities = [{ id: 'shared_id', label: 'Also in opps', path: '/b', cta: 'B' }];
    const result = buildTodayActions(makeKpis(), watchlist, opportunities);
    const matchingItems = result.filter(r => r.id === 'shared_id');
    expect(matchingItems).toHaveLength(1);
    // Watchlist item takes priority (processed first)
    expect(matchingItems[0].label).toBe('In watchlist');
  });

  it('caps result at 5 items maximum', () => {
    const watchlist = Array.from({ length: 8 }, (_, i) => ({
      id: `item_${i}`, label: `Item ${i}`, severity: 'warn', path: '/x', cta: 'X',
    }));
    const result = buildTodayActions(makeKpis(), watchlist, []);
    expect(result).toHaveLength(5);
  });

  it('appends opportunities as info-severity after watchlist items', () => {
    const watchlist = [{ id: 'wl_1', label: 'Watchlist', severity: 'high', path: '/a', cta: 'A' }];
    const opps = [{ id: 'opp_1', label: 'Opportunity', path: '/b', cta: 'B' }];
    const result = buildTodayActions(makeKpis(), watchlist, opps);
    const oppItem = result.find(r => r.id === 'opp_1');
    expect(oppItem).toBeDefined();
    expect(oppItem.severity).toBe('info');
    expect(oppItem.type).toBe('opportunity');
  });

  it('watchlist item type is "watchlist"', () => {
    const watchlist = [{ id: 'wl_1', label: 'Watchlist item', severity: 'critical', path: '/a', cta: 'A' }];
    const result = buildTodayActions(makeKpis(), watchlist, []);
    expect(result[0].type).toBe('watchlist');
  });
});

// ── buildExecutiveSummary ─────────────────────────────────────────────────────

describe('buildExecutiveSummary', () => {
  it('returns max 3 bullets', () => {
    const result = buildExecutiveSummary(makeKpis(), {});
    expect(result.length).toBeLessThanOrEqual(3);
  });

  it('returns warn bullet for total=0 (no sites)', () => {
    const kpis = makeKpis({ total: 0, conformes: 0, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 0 });
    const result = buildExecutiveSummary(kpis, {});
    expect(result[0].type).toBe('warn');
    expect(result[0].id).toBe('no_sites');
  });

  it('returns positive bullet when 100% conforme and coverage >= 80%', () => {
    const kpis = makeKpis({ total: 5, conformes: 5, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 90 });
    const result = buildExecutiveSummary(kpis, {});
    const positive = result.find(b => b.type === 'positive' && b.id === 'conforme_ok');
    expect(positive).toBeDefined();
  });

  it('returns negative bullet for nonConformes > 0', () => {
    const result = buildExecutiveSummary(makeKpis({ nonConformes: 3 }), {});
    const neg = result.find(b => b.id === 'non_conformes_exec');
    expect(neg).toBeDefined();
    expect(neg.type).toBe('negative');
    expect(neg.label).toContain('3 sites');
  });

  it('returns opportunity bullet when coverage < 80%', () => {
    const kpis = makeKpis({ couvertureDonnees: 50, nonConformes: 0, aRisque: 0 });
    const result = buildExecutiveSummary(kpis, {});
    const opp = result.find(b => b.id === 'coverage_exec');
    expect(opp).toBeDefined();
    expect(opp.type).toBe('opportunity');
  });

  it('returns "all_ok_exec" bullet when fully conforme with good coverage', () => {
    const kpis = makeKpis({ total: 5, conformes: 5, nonConformes: 0, aRisque: 0, couvertureDonnees: 100, risqueTotal: 0 });
    const result = buildExecutiveSummary(kpis, { worst: [], best: [] });
    const allOk = result.find(b => b.id === 'all_ok_exec');
    expect(allOk).toBeDefined();
    expect(allOk.type).toBe('positive');
  });
});

// ── buildExecutiveKpis ────────────────────────────────────────────────────────

describe('buildExecutiveKpis', () => {
  it('returns exactly 4 KPI tiles', () => {
    const result = buildExecutiveKpis(makeKpis(), makeSites());
    expect(result).toHaveLength(4);
  });

  it('first tile is conformite with pctConf value', () => {
    const kpis = makeKpis({ total: 10, conformes: 7 }); // 70%
    const result = buildExecutiveKpis(kpis, makeSites());
    expect(result[0].id).toBe('conformite');
    expect(result[0].value).toContain('70');
  });

  it('second tile is risque with correct k€ format', () => {
    const kpis = makeKpis({ risqueTotal: 25000 });
    const result = buildExecutiveKpis(kpis, makeSites());
    expect(result[1].id).toBe('risque');
    expect(result[1].value).toBe('25 k€');
  });

  it('conformite tile status is "crit" when nonConformes > 0', () => {
    const kpis = makeKpis({ nonConformes: 2 });
    const result = buildExecutiveKpis(kpis, makeSites());
    expect(result[0].status).toBe('crit');
  });

  it('conformite tile status is "ok" when all conformes', () => {
    const kpis = makeKpis({ total: 5, conformes: 5, nonConformes: 0, aRisque: 0, risqueTotal: 0 });
    const result = buildExecutiveKpis(kpis, makeSites(5));
    expect(result[0].status).toBe('ok');
  });

  it('returns "—" values for total=0 (empty portfolio)', () => {
    const kpis = makeKpis({ total: 0, conformes: 0, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 0 });
    const result = buildExecutiveKpis(kpis, []);
    expect(result[0].value).toBe('—');
    expect(result[2].value).toBe('—'); // maturite
    expect(result[3].value).toBe('—'); // couverture
  });

  it('risque tile shows 0€ when no risk', () => {
    const kpis = makeKpis({ risqueTotal: 0, nonConformes: 0, aRisque: 0 });
    const result = buildExecutiveKpis(kpis, makeSites());
    expect(result[1].value).toBe('0 €');
  });

  it('fourth tile is couverture with correct sites count', () => {
    const sites = makeSites(10); // 7 have conso_kwh_an > 0
    const result = buildExecutiveKpis(makeKpis(), sites);
    expect(result[3].id).toBe('couverture');
    expect(result[3].sub).toContain('7 sites');
  });
});
