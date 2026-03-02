/**
 * PROMEOS — computeHealthState + billing health + trend tests
 * Core invariant: GREEN banner + critical item = impossible.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { computeHealthState } from '../dashboardEssentials';
import {
  buildBillingWatchlist, computeBillingHealthState, computeHealthTrend,
  buildSnapshotKey, loadHealthSnapshot, saveHealthSnapshot,
} from '../billingHealthModel';

describe('computeHealthState', () => {
  const BASE_KPIS = { total: 10, conformes: 10, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 80 };

  it('returns GREEN when no issues', () => {
    const state = computeHealthState({ kpis: BASE_KPIS, watchlist: [], briefing: [], alertsCount: 0 });
    expect(state.level).toBe('GREEN');
    expect(state.title).toContain('sous contrôle');
    expect(state.reasons).toHaveLength(0);
  });

  it('returns RED when nonConformes > 0', () => {
    const kpis = { ...BASE_KPIS, nonConformes: 2, conformes: 8 };
    const watchlist = [{ id: 'nc', label: '2 sites non conformes', severity: 'critical', path: '/conformite', cta: 'Voir' }];
    const state = computeHealthState({ kpis, watchlist, alertsCount: 0 });
    expect(state.level).toBe('RED');
    expect(state.reasons.length).toBeGreaterThan(0);
    expect(state.primaryCta.to).toBe('/conformite');
  });

  it('returns RED when watchlist has critical item even if kpis clean', () => {
    const watchlist = [{ id: 'test', label: 'critical issue', severity: 'critical', path: '/', cta: 'Fix' }];
    const state = computeHealthState({ kpis: BASE_KPIS, watchlist, alertsCount: 0 });
    expect(state.level).toBe('RED');
  });

  it('returns AMBER when only warnings (aRisque)', () => {
    const kpis = { ...BASE_KPIS, aRisque: 1, conformes: 9 };
    const watchlist = [{ id: 'ar', label: '1 site à risque', severity: 'high', path: '/actions', cta: 'Plan' }];
    const state = computeHealthState({ kpis, watchlist, alertsCount: 0 });
    expect(state.level).toBe('AMBER');
  });

  it('returns AMBER when alerts > 0 even if kpis clean', () => {
    const state = computeHealthState({ kpis: BASE_KPIS, watchlist: [], alertsCount: 3 });
    expect(state.level).toBe('AMBER');
  });

  it('caps reasons at 3 and adds secondaryCta for overflow', () => {
    const watchlist = [
      { id: 'a', label: 'A', severity: 'warn', path: '/' },
      { id: 'b', label: 'B', severity: 'warn', path: '/' },
      { id: 'c', label: 'C', severity: 'warn', path: '/' },
      { id: 'd', label: 'D', severity: 'warn', path: '/' },
    ];
    const state = computeHealthState({ kpis: { ...BASE_KPIS, aRisque: 1 }, watchlist, alertsCount: 0 });
    expect(state.reasons).toHaveLength(3);
    expect(state.secondaryCta).toBeDefined();
    expect(state.secondaryCta.label).toMatch(/4 points/);
  });

  it('no secondaryCta when reasons <= 3', () => {
    const watchlist = [
      { id: 'a', label: 'A', severity: 'warn', path: '/' },
      { id: 'b', label: 'B', severity: 'warn', path: '/' },
    ];
    const state = computeHealthState({ kpis: { ...BASE_KPIS, aRisque: 1 }, watchlist, alertsCount: 0 });
    expect(state.reasons).toHaveLength(2);
    expect(state.secondaryCta).toBeUndefined();
  });

  it('includes consistency issues as warn reasons', () => {
    const consistency = { ok: false, issues: [{ code: 'test', label: 'Data issue' }] };
    const state = computeHealthState({ kpis: BASE_KPIS, consistency, alertsCount: 0 });
    expect(state.level).toBe('AMBER');
    expect(state.reasons.some(r => r.label === 'Data issue')).toBe(true);
  });

  it('CORE INVARIANT: GREEN + critical item is impossible', () => {
    // nonConformes > 0 always triggers RED, never GREEN
    const kpis = { ...BASE_KPIS, nonConformes: 1 };
    const state = computeHealthState({ kpis, watchlist: [], alertsCount: 0 });
    expect(state.level).toBe('RED');
  });

  it('returns valid HealthState shape', () => {
    const state = computeHealthState({ kpis: BASE_KPIS });
    expect(state).toHaveProperty('level');
    expect(state).toHaveProperty('title');
    expect(state).toHaveProperty('subtitle');
    expect(state).toHaveProperty('reasons');
    expect(state).toHaveProperty('primaryCta');
    expect(state.primaryCta).toHaveProperty('label');
    expect(state.primaryCta).toHaveProperty('to');
    expect(Array.isArray(state.reasons)).toBe(true);
    expect(['GREEN', 'AMBER', 'RED']).toContain(state.level);
  });

  it('handles missing optional params gracefully', () => {
    const state = computeHealthState({ kpis: BASE_KPIS });
    expect(state.level).toBe('GREEN');
  });
});

// ── Billing Health Model ───────────────────────────────────────────────────

describe('buildBillingWatchlist', () => {
  it('groups insights by type and picks highest severity', () => {
    const insights = [
      { id: 1, type: 'unit_price_high', severity: 'high', insight_status: 'open', estimated_loss_eur: 100 },
      { id: 2, type: 'unit_price_high', severity: 'critical', insight_status: 'open', estimated_loss_eur: 200 },
      { id: 3, type: 'shadow_gap', severity: 'medium', insight_status: 'open', estimated_loss_eur: 50 },
    ];
    const watchlist = buildBillingWatchlist(insights);
    expect(watchlist).toHaveLength(2);
    const priceItem = watchlist.find(w => w.id === 'billing-unit_price_high');
    expect(priceItem.severity).toBe('critical');
    expect(priceItem.estimatedLoss).toBe(300);
  });

  it('excludes resolved and false_positive insights', () => {
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'critical', insight_status: 'resolved' },
      { id: 2, type: 'shadow_gap', severity: 'high', insight_status: 'false_positive' },
      { id: 3, type: 'duplicate_invoice', severity: 'medium', insight_status: 'open' },
    ];
    const watchlist = buildBillingWatchlist(insights);
    expect(watchlist).toHaveLength(1);
    expect(watchlist[0].id).toBe('billing-duplicate_invoice');
  });

  it('generates business-language labels (no tech jargon)', () => {
    const insights = [
      { id: 1, type: 'unit_price_high', severity: 'high', insight_status: 'open' },
      { id: 2, type: 'unit_price_high', severity: 'medium', insight_status: 'open' },
    ];
    const watchlist = buildBillingWatchlist(insights);
    expect(watchlist[0].label).toContain('écarts de prix');
    expect(watchlist[0].label).not.toContain('unit_price_high');
  });

  it('caps watchlist at 5 items and sorts by severity', () => {
    const types = ['shadow_gap', 'unit_price_high', 'duplicate_invoice', 'missing_period', 'period_too_long', 'negative_kwh'];
    const insights = types.map((type, i) => ({
      id: i, type, severity: i === 0 ? 'critical' : 'medium', insight_status: 'open',
    }));
    const watchlist = buildBillingWatchlist(insights);
    expect(watchlist).toHaveLength(5);
    expect(watchlist[0].severity).toBe('critical');
  });

  it('returns empty array when no active insights', () => {
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'high', insight_status: 'resolved' },
    ];
    expect(buildBillingWatchlist(insights)).toHaveLength(0);
    expect(buildBillingWatchlist([])).toHaveLength(0);
    expect(buildBillingWatchlist()).toHaveLength(0);
  });
});

describe('computeBillingHealthState', () => {
  it('returns RED when critical billing insights exist', () => {
    const summary = { total_invoices: 10, total_estimated_loss_eur: 5000 };
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'critical', insight_status: 'open', estimated_loss_eur: 5000 },
    ];
    const state = computeBillingHealthState(summary, insights);
    expect(state.level).toBe('RED');
    expect(state.primaryCta.to).toBe('/bill-intel');
    expect(state.primaryCta.label).toContain('anomalies critiques');
  });

  it('returns GREEN when no active insights', () => {
    const summary = { total_invoices: 10, total_estimated_loss_eur: 0 };
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'high', insight_status: 'resolved' },
    ];
    const state = computeBillingHealthState(summary, insights);
    expect(state.level).toBe('GREEN');
    expect(state.primaryCta.to).toBe('/bill-intel');
  });
});

// ── Health Trend ────────────────────────────────────────────────────────────

describe('computeHealthTrend', () => {
  it('detects improvement when level drops from RED to AMBER', () => {
    const current = { level: 'AMBER', reasons: [{ id: 'a' }] };
    const previous = { level: 'RED', reasonsCount: 3 };
    const trend = computeHealthTrend(current, previous);
    expect(trend.direction).toBe('improving');
    expect(trend.label).toContain('amélioration');
  });

  it('detects degradation when level rises from GREEN to AMBER', () => {
    const current = { level: 'AMBER', reasons: [{ id: 'a' }, { id: 'b' }] };
    const previous = { level: 'GREEN', reasonsCount: 0 };
    const trend = computeHealthTrend(current, previous);
    expect(trend.direction).toBe('degrading');
    expect(trend.label).toContain('dégradation');
  });

  it('returns stable when same level and same reason count', () => {
    const current = { level: 'AMBER', reasons: [{ id: 'a' }] };
    const previous = { level: 'AMBER', reasonsCount: 1 };
    const trend = computeHealthTrend(current, previous);
    expect(trend.direction).toBe('stable');
    expect(trend.label).toBe('Stable');
  });

  it('returns stable label for first analysis when no previous', () => {
    const current = { level: 'AMBER', reasons: [] };
    const trend = computeHealthTrend(current, null);
    expect(trend.direction).toBe('stable');
    expect(trend.label).toContain('Première');
  });

  it('trend labels use "points" not "signaux"', () => {
    const current = { level: 'AMBER', reasons: [{ id: 'a' }, { id: 'b' }] };
    const previous = { level: 'AMBER', reasonsCount: 4 };
    const trend = computeHealthTrend(current, previous);
    expect(trend.direction).toBe('improving');
    expect(trend.label).toContain('points');
    expect(trend.label).not.toContain('signaux');
  });
});

// ── V2.2: Scoped Snapshot Key ──────────────────────────────────────────────

describe('buildSnapshotKey', () => {
  it('returns simple key when no scope', () => {
    expect(buildSnapshotKey('billing')).toBe('promeos.health.billing');
  });

  it('returns simple key when scope has no orgId', () => {
    expect(buildSnapshotKey('billing', {})).toBe('promeos.health.billing');
  });

  it('returns scoped key with orgId and scopeType', () => {
    expect(buildSnapshotKey('billing', { orgId: 1, scopeType: 'portfolio', scopeId: 2 }))
      .toBe('promeos.health.billing.org-1.portfolio-2');
  });

  it('defaults scopePart to all-sites when no scopeType', () => {
    expect(buildSnapshotKey('billing', { orgId: 5 }))
      .toBe('promeos.health.billing.org-5.all-sites');
  });

  it('handles string orgId', () => {
    expect(buildSnapshotKey('patrimoine', { orgId: 'demo', scopeType: 'site', scopeId: 42 }))
      .toBe('promeos.health.patrimoine.org-demo.site-42');
  });
});

// ── V2.2: Snapshot Retention ─────────────────────────────────────────────

describe('loadHealthSnapshot + saveHealthSnapshot (scoped + retention)', () => {
  const store = {};
  const localStorageMock = {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, val) => { store[key] = val; }),
    removeItem: vi.fn((key) => { delete store[key]; }),
    key: vi.fn((i) => Object.keys(store)[i] ?? null),
    get length() { return Object.keys(store).length; },
  };
  vi.stubGlobal('localStorage', localStorageMock);

  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    vi.clearAllMocks();
  });

  it('save + load round-trip with scope', () => {
    const state = { level: 'RED', reasons: [{ id: 'a' }, { id: 'b' }] };
    const scope = { orgId: 1, scopeType: 'billing', scopeId: 1 };
    saveHealthSnapshot('billing', state, scope);
    const loaded = loadHealthSnapshot('billing', scope);
    expect(loaded.level).toBe('RED');
    expect(loaded.reasonsCount).toBe(2);
    expect(loaded.timestamp).toBeGreaterThan(0);
  });

  it('returns null for expired snapshot (> 14 days)', () => {
    const key = buildSnapshotKey('billing', { orgId: 1 });
    store[key] = JSON.stringify({
      level: 'AMBER',
      reasonsCount: 1,
      timestamp: Date.now() - 15 * 24 * 60 * 60 * 1000, // 15 days ago
    });
    const loaded = loadHealthSnapshot('billing', { orgId: 1 });
    expect(loaded).toBeNull();
  });

  it('returns valid snapshot within retention window', () => {
    const key = buildSnapshotKey('billing', { orgId: 1 });
    store[key] = JSON.stringify({
      level: 'GREEN',
      reasonsCount: 0,
      timestamp: Date.now() - 7 * 24 * 60 * 60 * 1000, // 7 days ago
    });
    const loaded = loadHealthSnapshot('billing', { orgId: 1 });
    expect(loaded).not.toBeNull();
    expect(loaded.level).toBe('GREEN');
  });

  it('backward compat: works without scope', () => {
    const state = { level: 'AMBER', reasons: [{ id: 'x' }] };
    saveHealthSnapshot('billing', state);
    const loaded = loadHealthSnapshot('billing');
    expect(loaded.level).toBe('AMBER');
  });

  it('returns null on corrupt JSON', () => {
    store['promeos.health.billing'] = 'not-json{{{';
    expect(loadHealthSnapshot('billing')).toBeNull();
  });
});

// ── V2.2: Billing CTAs normalised ────────────────────────────────────────

describe('computeBillingHealthState — CTAs V2.2', () => {
  const SUMMARY = { total_invoices: 10, total_estimated_loss_eur: 5000 };

  it('RED → 2 stable CTAs (anomalies + plan action)', () => {
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'critical', insight_status: 'open', estimated_loss_eur: 5000 },
    ];
    const state = computeBillingHealthState(SUMMARY, insights);
    expect(state.level).toBe('RED');
    expect(state.primaryCta.label).toContain('anomalies critiques');
    expect(state.primaryCta.to).toBe('/bill-intel');
    expect(state.secondaryCta).toBeDefined();
    expect(state.secondaryCta.label).toContain("Plan d'action");
    expect(state.secondaryCta.to).toBe('/actions');
  });

  it('AMBER → 2 stable CTAs (analyser + explorer)', () => {
    const insights = [
      { id: 1, type: 'shadow_gap', severity: 'high', insight_status: 'open' },
    ];
    const state = computeBillingHealthState(SUMMARY, insights);
    expect(state.level).toBe('AMBER');
    expect(state.primaryCta.label).toContain('Analyser');
    expect(state.secondaryCta).toBeDefined();
    expect(state.secondaryCta.label).toContain('Explorer');
  });

  it('GREEN → single CTA (explorer), no secondary', () => {
    const insights = [];
    const state = computeBillingHealthState(SUMMARY, insights);
    expect(state.level).toBe('GREEN');
    expect(state.primaryCta.label).toContain('Explorer');
    expect(state.secondaryCta).toBeUndefined();
  });

  it('"Voir tout" overflow when > 3 watchlist items', () => {
    const types = ['shadow_gap', 'unit_price_high', 'duplicate_invoice', 'missing_period'];
    const insights = types.map((type, i) => ({
      id: i, type, severity: 'high', insight_status: 'open',
    }));
    const state = computeBillingHealthState(SUMMARY, insights);
    expect(state.secondaryCta).toBeDefined();
    expect(state.secondaryCta.label).toMatch(/4 points/);
    expect(state.secondaryCta.to).toBe('/bill-intel');
  });
});

// ── V2.2: Low severity does NOT elevate to AMBER ───────────────────────

describe('SEVERITY_RANK low coherence', () => {
  it('only-low-severity billing insights → GREEN (not AMBER)', () => {
    const summary = { total_invoices: 10, total_estimated_loss_eur: 0 };
    const insights = [
      { id: 1, type: 'zero_amount', severity: 'low', insight_status: 'open' },
      { id: 2, type: 'negative_kwh', severity: 'low', insight_status: 'open' },
    ];
    const state = computeBillingHealthState(summary, insights);
    // Low severity should NOT elevate to AMBER
    expect(state.level).toBe('GREEN');
  });
});

// ── V2.2: Microcopy FR — no English tech jargon ────────────────────────

describe('Microcopy FR coherence', () => {
  const BASE_KPIS = { total: 10, conformes: 10, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 80 };

  it('AMBER subtitle uses "points" not "signaux"', () => {
    const watchlist = [{ id: 'a', label: 'A', severity: 'warn', path: '/' }];
    const state = computeHealthState({ kpis: { ...BASE_KPIS, aRisque: 1 }, watchlist, alertsCount: 0 });
    expect(state.subtitle).toContain('point');
    expect(state.subtitle).not.toContain('signal');
  });

  it('overflow CTA uses "points" not "signaux"', () => {
    const watchlist = Array.from({ length: 5 }, (_, i) => ({
      id: `w${i}`, label: `W${i}`, severity: 'warn', path: '/',
    }));
    const state = computeHealthState({ kpis: { ...BASE_KPIS, aRisque: 1 }, watchlist, alertsCount: 0 });
    expect(state.secondaryCta.label).toContain('points');
    expect(state.secondaryCta.label).not.toContain('signaux');
  });
});
