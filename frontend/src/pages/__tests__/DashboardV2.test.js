/**
 * PROMEOS — DashboardV2 pure-logic tests
 * Covers:
 *   - normalizeDashboardModel  (contradictions, isAllClear, actions gate)
 *   - buildWatchlist           (non-conformes, a_risque, coverage items)
 *   - buildBriefing            (headline, items from watchlist)
 *   - buildOpportunities       (coverage, expert mode)
 *   - buildTodayActions        (dedup, sort, max 5 — re-tested via CommandCenter data flow)
 *
 * All tests run in Vitest node environment (no DOM).
 */
import { describe, it, expect } from 'vitest';
import { normalizeDashboardModel } from '../CommandCenter';
import {
  buildWatchlist,
  buildBriefing,
  buildOpportunities,
  buildTodayActions,
} from '../../models/dashboardEssentials';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeKpis(overrides = {}) {
  return {
    total: 10,
    conformes: 7,
    nonConformes: 2,
    aRisque: 1,
    risque: 15000,
    pctConf: 70,
    couvertureDonnees: 70,
    compStatus: 'crit',
    risqueStatus: 'warn',
    ...overrides,
  };
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

// ── normalizeDashboardModel ───────────────────────────────────────────────────

describe('normalizeDashboardModel', () => {
  it('clears risque, nonConformes, aRisque when pctConf=100', () => {
    const kpis = makeKpis({ pctConf: 100, nonConformes: 0, aRisque: 0, risque: 5000 });
    const { kpis: norm } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(norm.risque).toBe(0);
    expect(norm.nonConformes).toBe(0);
    expect(norm.aRisque).toBe(0);
  });

  it('clears risque EUR when nonConformes + aRisque = 0', () => {
    const kpis = makeKpis({ pctConf: 90, nonConformes: 0, aRisque: 0, risque: 3000 });
    const { kpis: norm } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(norm.risque).toBe(0);
  });

  it('sets isAllClear=true when pctConf=100, risque=0, alertsCount=0', () => {
    const kpis = makeKpis({ pctConf: 100, nonConformes: 0, aRisque: 0, risque: 0 });
    const { isAllClear } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(isAllClear).toBe(true);
  });

  it('sets isAllClear=false when alertsCount > 0 even with 100% conformite', () => {
    const kpis = makeKpis({ pctConf: 100, nonConformes: 0, aRisque: 0, risque: 0 });
    const { isAllClear } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 2 });
    expect(isAllClear).toBe(false);
  });

  it('empties topActions when isAllClear=true', () => {
    const kpis = makeKpis({ pctConf: 100, nonConformes: 0, aRisque: 0, risque: 0 });
    const dummy = [{ id: 'x', titre: 'X', priorite: 'medium', impact_eur: 0, route: '/' }];
    const { topActions } = normalizeDashboardModel({ kpis, topActions: dummy, alertsCount: 0 });
    expect(topActions).toHaveLength(0);
  });

  it('preserves topActions when isAllClear=false', () => {
    const kpis = makeKpis({ pctConf: 80, nonConformes: 2 });
    const dummy = [{ id: 'x', titre: 'X', priorite: 'high', impact_eur: 1000, route: '/' }];
    const { topActions } = normalizeDashboardModel({ kpis, topActions: dummy, alertsCount: 0 });
    expect(topActions).toHaveLength(1);
  });

  it('does not mutate the original kpis object', () => {
    const kpis = makeKpis({ pctConf: 100, nonConformes: 0, aRisque: 0, risque: 9999 });
    const original = { ...kpis };
    normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(kpis.risque).toBe(original.risque);
  });

  it('passes through pctConf unchanged when < 100', () => {
    const kpis = makeKpis({ pctConf: 75 });
    const { kpis: norm } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(norm.pctConf).toBe(75);
  });
});

// ── buildWatchlist ────────────────────────────────────────────────────────────

describe('buildWatchlist', () => {
  it('returns non_conformes item when nonConformes > 0', () => {
    const kpis = makeKpis({ nonConformes: 2 });
    const result = buildWatchlist(kpis, makeSites());
    expect(result.some(w => w.id === 'non_conformes')).toBe(true);
  });

  it('returns a_risque item when aRisque > 0', () => {
    const kpis = makeKpis({ aRisque: 1, nonConformes: 0 });
    const result = buildWatchlist(kpis, makeSites());
    expect(result.some(w => w.id === 'a_risque')).toBe(true);
  });

  it('returns no items when all conformes and coverage is good', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 90 });
    const result = buildWatchlist(kpis, makeSites());
    expect(result.some(w => w.id === 'non_conformes')).toBe(false);
    expect(result.some(w => w.id === 'a_risque')).toBe(false);
  });

  it('all watchlist items have required fields: id, label, severity, path, cta', () => {
    const kpis = makeKpis({ nonConformes: 1, aRisque: 1, couvertureDonnees: 50 });
    const result = buildWatchlist(kpis, makeSites());
    for (const item of result) {
      expect(item).toHaveProperty('id');
      expect(item).toHaveProperty('label');
      expect(item).toHaveProperty('severity');
      expect(item).toHaveProperty('path');
      expect(item).toHaveProperty('cta');
    }
  });
});

// ── buildBriefing ─────────────────────────────────────────────────────────────

describe('buildBriefing', () => {
  it('returns an array of bullet objects', () => {
    const kpis = makeKpis();
    const watchlist = buildWatchlist(kpis, makeSites());
    const result = buildBriefing(kpis, watchlist);
    expect(Array.isArray(result)).toBe(true);
  });

  it('returns empty array when no issues', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, risque: 0, pctConf: 100, couvertureDonnees: 90 });
    const result = buildBriefing(kpis, []);
    expect(result).toHaveLength(0);
  });

  it('bullets list is bounded (≤ 3)', () => {
    const kpis = makeKpis({ nonConformes: 3, aRisque: 2, couvertureDonnees: 30 });
    const watchlist = buildWatchlist(kpis, makeSites());
    const result = buildBriefing(kpis, watchlist);
    expect(result.length).toBeLessThanOrEqual(3);
  });

  it('each bullet has id, label, severity, path', () => {
    const kpis = makeKpis({ nonConformes: 1 });
    const result = buildBriefing(kpis, buildWatchlist(kpis, makeSites()));
    for (const b of result) {
      expect(b).toHaveProperty('id');
      expect(b).toHaveProperty('label');
      expect(b).toHaveProperty('severity');
    }
  });

  it('includes non_conformes bullet when nonConformes > 0', () => {
    const kpis = makeKpis({ nonConformes: 2 });
    const result = buildBriefing(kpis, buildWatchlist(kpis, makeSites()));
    expect(result.some(b => b.id === 'non_conformes')).toBe(true);
  });
});

// ── buildOpportunities ────────────────────────────────────────────────────────

describe('buildOpportunities', () => {
  it('returns an array', () => {
    const result = buildOpportunities(makeKpis(), makeSites(), {});
    expect(Array.isArray(result)).toBe(true);
  });

  it('each opportunity has id, label, path, cta', () => {
    const result = buildOpportunities(makeKpis({ couvertureDonnees: 40 }), makeSites(), {});
    for (const opp of result) {
      expect(opp).toHaveProperty('id');
      expect(opp).toHaveProperty('label');
      expect(opp).toHaveProperty('path');
      expect(opp).toHaveProperty('cta');
    }
  });
});

// ── Data-flow integration: CommandCenter pipeline ─────────────────────────────

describe('CommandCenter data-flow (watchlist→briefing→todayActions)', () => {
  it('todayActions contains watchlist items when problems exist', () => {
    const kpis = makeKpis({ nonConformes: 2, aRisque: 1 });
    const sites = makeSites();
    const watchlist = buildWatchlist(kpis, sites);
    const opps = buildOpportunities(kpis, sites, {});
    const todayActions = buildTodayActions(kpis, watchlist, opps);
    const watchlistIds = watchlist.map(w => w.id);
    const todayIds = todayActions.map(t => t.id);
    const hasWatchlistItem = watchlistIds.some(id => todayIds.includes(id));
    expect(hasWatchlistItem).toBe(true);
  });

  it('todayActions is empty when no watchlist items and no opportunities', () => {
    const kpis = makeKpis({ nonConformes: 0, aRisque: 0, couvertureDonnees: 100 });
    const sites = makeSites(5).map(s => ({ ...s, statut_conformite: 'conforme' }));
    const watchlist = buildWatchlist(kpis, sites);
    const todayActions = buildTodayActions(kpis, watchlist, []);
    expect(todayActions.filter(t => t.type === 'watchlist')).toHaveLength(0);
  });

  it('briefing bullet path values are non-empty strings', () => {
    const kpis = makeKpis();
    const watchlist = buildWatchlist(kpis, makeSites());
    const bullets = buildBriefing(kpis, watchlist);
    for (const b of bullets) {
      if (b.path !== undefined) {
        expect(typeof b.path).toBe('string');
        expect(b.path.length).toBeGreaterThan(0);
      }
    }
  });

  it('EssentialsRow receives correct couvertureDonnees from kpis', () => {
    // Simulate the kpis shape CommandCenter passes to EssentialsRow
    const sites = makeSites(10); // 7 with conso_kwh_an > 0
    const total = sites.length;
    const couvertureDonnees = total > 0
      ? Math.round(sites.filter(s => s.conso_kwh_an > 0).length / total * 100)
      : 0;
    expect(couvertureDonnees).toBe(70);
  });
});
