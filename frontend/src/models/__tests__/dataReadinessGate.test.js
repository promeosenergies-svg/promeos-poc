/**
 * PROMEOS — dataReadinessGate tests (Step 3.1)
 * Tests: popover content, computeDataConfidence, wording, trend, snapshot.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  computeDataReadinessState,
  computeDataConfidence,
  buildReadinessSnapshotKey,
  loadReadinessSnapshot,
  saveReadinessSnapshot,
  computeReadinessTrend,
  LEVEL_BADGE_LABEL,
  SOFT_GATE_TOOLTIP_FR,
} from '../dataReadinessModel';

// ── Helpers ─────────────────────────────────────────────────────────────────

function mkActivation(consoCoverage = 100) {
  return {
    dimensions: [{ key: 'consommation', coverage: consoCoverage }],
    activatedCount: 3,
  };
}

function mkSignals(overrides = {}) {
  return {
    billingMonthCount: 15,
    efaDashboard: { total_sites: 5, open_issues: 0 },
    connectors: [{ status: 'active' }],
    operatModuleActive: false,
    hasManualImport: false,
    ...overrides,
  };
}

// ── Popover content (reasons max 3 + CTA) ───────────────────────────────

describe('Popover content', () => {
  it('GREEN state has 0 reasons, title "Données complètes"', () => {
    const state = computeDataReadinessState(mkActivation(100), mkSignals());
    expect(state.level).toBe('GREEN');
    expect(state.title).toBe('Données complètes');
    expect(state.reasons).toHaveLength(0);
    expect(state.badgeLabel).toBe('OK');
  });

  it('RED state has correct title + reasons with CTA path', () => {
    const state = computeDataReadinessState(mkActivation(0), mkSignals({ billingMonthCount: 0 }));
    expect(state.level).toBe('RED');
    expect(state.title).toBe('Données incomplètes');
    expect(state.badgeLabel).toBe('Incomplet');
    expect(state.reasons.length).toBeGreaterThan(0);
    for (const r of state.reasons) {
      expect(r).toHaveProperty('path');
      expect(r).toHaveProperty('cta');
      expect(r.path).toMatch(/^\//);
    }
  });

  it('reasons capped at 3 with secondaryCta overflow', () => {
    // Force 4 reasons by having all evaluators fail
    const state = computeDataReadinessState(
      { dimensions: [{ key: 'consommation', coverage: 0 }], activatedCount: 0 },
      { billingMonthCount: 0, operatModuleActive: true, efaDashboard: { total_sites: 0 }, connectors: [], hasManualImport: false },
    );
    expect(state.reasons.length).toBeLessThanOrEqual(3);
    expect(state.allReasonCount).toBe(4);
    expect(state.secondaryCta).toBeDefined();
    expect(state.secondaryCta.label).toContain('4 points');
  });

  it('primaryCta points to first reason path', () => {
    const state = computeDataReadinessState(mkActivation(0), mkSignals());
    expect(state.primaryCta.to).toBe('/consommations/import');
    expect(state.primaryCta.label).toBe('Importer');
  });
});

// ── computeDataConfidence ───────────────────────────────────────────────

describe('computeDataConfidence', () => {
  it('all OK → Élevée', () => {
    const state = computeDataReadinessState(mkActivation(100), mkSignals());
    const conf = computeDataConfidence(state);
    expect(conf.label).toBe('Élevée');
    expect(conf.level).toBe('high');
    expect(conf.badgeStatus).toBe('ok');
  });

  it('partial conso → Moyenne', () => {
    const state = computeDataReadinessState(mkActivation(50), mkSignals());
    const conf = computeDataConfidence(state);
    expect(conf.label).toBe('Moyenne');
    expect(conf.level).toBe('medium');
    expect(conf.badgeStatus).toBe('warn');
  });

  it('KO factures → Faible', () => {
    const state = computeDataReadinessState(mkActivation(100), mkSignals({ billingMonthCount: 0 }));
    const conf = computeDataConfidence(state);
    expect(conf.label).toBe('Faible');
    expect(conf.level).toBe('low');
    expect(conf.badgeStatus).toBe('crit');
  });

  it('null readinessState → Faible', () => {
    const conf = computeDataConfidence(null);
    expect(conf.label).toBe('Faible');
  });
});

// ── Wording OK/Partiel/Incomplet ────────────────────────────────────────

describe('Wording FR', () => {
  it('LEVEL_BADGE_LABEL uses OK/Partiel/Incomplet', () => {
    expect(LEVEL_BADGE_LABEL.GREEN).toBe('OK');
    expect(LEVEL_BADGE_LABEL.AMBER).toBe('Partiel');
    expect(LEVEL_BADGE_LABEL.RED).toBe('Incomplet');
  });

  it('"points" used in overflow CTA, not "signaux"', () => {
    const state = computeDataReadinessState(
      { dimensions: [{ key: 'consommation', coverage: 0 }], activatedCount: 0 },
      { billingMonthCount: 0, operatModuleActive: true, efaDashboard: { total_sites: 0 }, connectors: [], hasManualImport: false },
    );
    if (state.secondaryCta) {
      expect(state.secondaryCta.label).toContain('points');
      expect(state.secondaryCta.label).not.toContain('signaux');
    }
  });

  it('SOFT_GATE_TOOLTIP_FR is in French, not English', () => {
    expect(SOFT_GATE_TOOLTIP_FR).toContain('Données insuffisantes');
    expect(SOFT_GATE_TOOLTIP_FR).not.toMatch(/insufficient|missing|data/i);
  });

  it('all reason labels are in French', () => {
    const state = computeDataReadinessState(
      { dimensions: [{ key: 'consommation', coverage: 0 }], activatedCount: 0 },
      { billingMonthCount: 0, operatModuleActive: true, efaDashboard: { total_sites: 0 }, connectors: [], hasManualImport: false },
    );
    for (const r of state.reasons) {
      expect(r.label).not.toMatch(/^[A-Z][a-z]+ data|No data|Missing/i);
    }
  });
});

// ── Trend readiness ─────────────────────────────────────────────────────

describe('Trend readiness', () => {
  it('no previous → delta 0, empty label', () => {
    const state = computeDataReadinessState(mkActivation(100), mkSignals());
    const trend = computeReadinessTrend(state, null);
    expect(trend.delta).toBe(0);
    expect(trend.labelFR).toBe('');
  });

  it('+1 dimension OK → positive delta', () => {
    const current = computeDataReadinessState(mkActivation(100), mkSignals());
    const prev = { okDimensions: 3, reasonCount: 1, _ts: Date.now() - 86400000 };
    const trend = computeReadinessTrend(current, prev);
    expect(trend.delta).toBe(1);
    expect(trend.labelFR).toContain('+1');
  });

  it('-1 → negative delta', () => {
    const current = computeDataReadinessState(mkActivation(50), mkSignals());
    const prev = { okDimensions: 4, reasonCount: 0, _ts: Date.now() - 86400000 };
    const trend = computeReadinessTrend(current, prev);
    expect(trend.delta).toBeLessThan(0);
    expect(trend.labelFR).toContain('-');
  });
});

// ── Snapshot scoping + purge ────────────────────────────────────────────

describe('Snapshot scoping', () => {
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

  it('buildReadinessSnapshotKey includes org + scope', () => {
    const key = buildReadinessSnapshotKey({ orgId: 42, scopeType: 'pf', scopeId: 7 });
    expect(key).toBe('promeos.readiness.org-42.pf-7');
  });

  it('save + load roundtrip', () => {
    const scope = { orgId: 1, scopeType: 'all', scopeId: 0 };
    const state = computeDataReadinessState(mkActivation(100), mkSignals());
    saveReadinessSnapshot(state, scope);
    const loaded = loadReadinessSnapshot(scope);
    expect(loaded).not.toBeNull();
    expect(loaded.level).toBe('GREEN');
  });

  it('expired snapshot returns null', () => {
    const scope = { orgId: 99 };
    const key = buildReadinessSnapshotKey(scope);
    localStorage.setItem(key, JSON.stringify({ level: 'RED', _ts: Date.now() - 15 * 86400000 }));
    const loaded = loadReadinessSnapshot(scope);
    expect(loaded).toBeNull();
  });

  it('different scopes are isolated', () => {
    const scope1 = { orgId: 1, scopeType: 'pf', scopeId: 10 };
    const scope2 = { orgId: 1, scopeType: 'site', scopeId: 20 };
    const state = computeDataReadinessState(mkActivation(100), mkSignals());
    saveReadinessSnapshot(state, scope1);
    const loaded2 = loadReadinessSnapshot(scope2);
    expect(loaded2).toBeNull(); // different scope
    const loaded1 = loadReadinessSnapshot(scope1);
    expect(loaded1).not.toBeNull();
  });
});

// ── Source guards (integration) ─────────────────────────────────────────

describe('Source guards — Step 3.1', () => {
  it('DataReadinessBadge has popover', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/components/DataReadinessBadge.jsx',
      'utf-8',
    );
    expect(src).toContain('readiness-popover');
    expect(src).toContain('Corriger maintenant');
    expect(src).toContain('readiness-reasons');
    expect(src).toContain('aria-haspopup');
  });

  it('PurchasePage has data confidence badge', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/PurchasePage.jsx',
      'utf-8',
    );
    expect(src).toContain('computeDataConfidence');
    expect(src).toContain('purchase-confidence');
    expect(src).toContain('Confiance');
  });
});
