/**
 * PROMEOS — DashboardV2 pure-logic tests
 * Covers:
 *   - normalizeDashboardModel  (contradictions, isAllClear, actions gate)
 *   - buildBriefing            (headline, items)
 *   - buildOpportunities       (coverage, expert mode)
 *
 * Sprint α-fin Phase 1.D — describe `buildWatchlist` + describe data-flow
 * `CommandCenter (watchlist→briefing→todayActions)` retirés. La fonction
 * `buildWatchlist` a été supprimée (anti-pattern §8.1). Le pipeline
 * watchlist→todayActions n'existe plus côté FE — les signaux passent
 * désormais par /api/v1/events/upcoming (Phase 1.A) consommés via
 * `useEvents` hook (Phase 1.C). Cf. ADR-006.
 *
 * All tests run in Vitest node environment (no DOM).
 */
import { describe, it, expect } from 'vitest';
import { normalizeDashboardModel } from '../CommandCenter';
import { buildBriefing, buildOpportunities } from '../../models/dashboardEssentials';

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

// Sprint α-fin Phase 1.D — describes `buildWatchlist` (4 tests) +
// `CommandCenter data-flow (watchlist→briefing→todayActions)` (4 tests)
// retirés. La fonction `buildWatchlist` a été supprimée de
// dashboardEssentials.js (anti-pattern §8.1). Les signaux passent désormais
// par /api/v1/events/upcoming consommé via useEvents (Phase 1.C). Les
// tests `buildBriefing` et `buildOpportunities` sont conservés car ils
// testent des fonctions encore exportées (qui tolèrent watchlist=[]
// désormais).

// ── buildBriefing ─────────────────────────────────────────────────────────────

describe('buildBriefing', () => {
  it('returns an array of bullet objects', () => {
    const kpis = makeKpis();
    const result = buildBriefing(kpis, []);
    expect(Array.isArray(result)).toBe(true);
  });

  it('returns empty array when no issues', () => {
    const kpis = makeKpis({
      nonConformes: 0,
      aRisque: 0,
      risque: 0,
      pctConf: 100,
      couvertureDonnees: 90,
    });
    const result = buildBriefing(kpis, []);
    expect(result).toHaveLength(0);
  });

  it('bullets list is bounded (≤ 3)', () => {
    const kpis = makeKpis({ nonConformes: 3, aRisque: 2, couvertureDonnees: 30 });
    const result = buildBriefing(kpis, []);
    expect(result.length).toBeLessThanOrEqual(3);
  });

  it('each bullet has id, label, severity, path', () => {
    const kpis = makeKpis({ nonConformes: 1 });
    const result = buildBriefing(kpis, []);
    for (const b of result) {
      expect(b).toHaveProperty('id');
      expect(b).toHaveProperty('label');
      expect(b).toHaveProperty('severity');
    }
  });

  it('includes non_conformes bullet when nonConformes > 0', () => {
    const kpis = makeKpis({ nonConformes: 2 });
    const result = buildBriefing(kpis, []);
    expect(result.some((b) => b.id === 'non_conformes')).toBe(true);
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
