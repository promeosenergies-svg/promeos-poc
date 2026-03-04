/**
 * PROMEOS — Data Readiness Gate tests
 * Unit tests for computeDataReadinessState + source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import { computeDataReadinessState } from '../dataReadinessModel';
import fs from 'fs';
import path from 'path';

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeActivation({ consoCoverage = 100, activatedCount = 3 } = {}) {
  return {
    dimensions: [
      { key: 'patrimoine', available: true, coverage: 100 },
      { key: 'conformite', available: true, coverage: 100 },
      { key: 'consommation', available: consoCoverage > 0, coverage: consoCoverage },
      { key: 'facturation', available: true, coverage: 100 },
      { key: 'achat', available: true, coverage: 100 },
    ],
    activatedCount,
    totalDimensions: 5,
    overallCoverage: 80,
    nextAction: null,
  };
}

const OK_SIGNALS = {
  billingMonthCount: 14,
  efaDashboard: { total_sites: 5, open_issues: 0 },
  connectors: [{ status: 'active', name: 'enedis' }],
  operatModuleActive: false,
  hasManualImport: true,
};

// ── Shape & purity ──────────────────────────────────────────────────────────

describe('computeDataReadinessState — shape', () => {
  it('returns valid ReadinessState shape', () => {
    const state = computeDataReadinessState(makeActivation(), OK_SIGNALS);
    expect(state).toHaveProperty('level');
    expect(state).toHaveProperty('title');
    expect(state).toHaveProperty('subtitle');
    expect(state).toHaveProperty('reasons');
    expect(state).toHaveProperty('primaryCta');
    expect(state).toHaveProperty('gating');
    expect(state).toHaveProperty('badgeStatus');
    expect(state).toHaveProperty('badgeLabel');
    expect(state.primaryCta).toHaveProperty('label');
    expect(state.primaryCta).toHaveProperty('to');
    expect(Array.isArray(state.reasons)).toBe(true);
    expect(['GREEN', 'AMBER', 'RED']).toContain(state.level);
  });

  it('is a pure function (no React, no API in source)', () => {
    const src = fs.readFileSync(path.resolve(__dirname, '../dataReadinessModel.js'), 'utf-8');
    expect(src).not.toMatch(/from\s+['"]react['"]/);
    expect(src).not.toMatch(/from\s+['"]\.\.\/services\/api['"]/);
  });
});

// ── Conso dimension ─────────────────────────────────────────────────────────

describe('computeDataReadinessState — conso', () => {
  it('returns RED when 0 conso coverage', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 0 }), OK_SIGNALS);
    expect(state.level).toBe('RED');
    expect(state.reasons.some((r) => r.id === 'conso-ko')).toBe(true);
  });

  it('returns AMBER when conso < 80%', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 50 }), OK_SIGNALS);
    expect(state.level).toBe('AMBER');
    expect(state.reasons.some((r) => r.id === 'conso-partial')).toBe(true);
  });

  it('returns GREEN when conso >= 80%', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 85 }), OK_SIGNALS);
    expect(state.level).toBe('GREEN');
    expect(state.reasons.some((r) => r.id?.startsWith('conso'))).toBe(false);
  });
});

// ── Facturation dimension ───────────────────────────────────────────────────

describe('computeDataReadinessState — facturation', () => {
  it('returns RED when < 3 months billing', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      billingMonthCount: 1,
    });
    expect(state.level).toBe('RED');
    expect(state.reasons.some((r) => r.id === 'factures-ko')).toBe(true);
  });

  it('returns AMBER when 3-11 months billing', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      billingMonthCount: 8,
    });
    expect(state.level).toBe('AMBER');
    expect(state.reasons.some((r) => r.id === 'factures-partial')).toBe(true);
  });

  it('returns GREEN when >= 12 months billing', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      billingMonthCount: 14,
    });
    expect(state.level).toBe('GREEN');
  });
});

// ── OPERAT dimension ────────────────────────────────────────────────────────

describe('computeDataReadinessState — OPERAT', () => {
  it('returns RED when OPERAT active + 0 EFA', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      operatModuleActive: true,
      efaDashboard: { total_sites: 0 },
    });
    expect(state.level).toBe('RED');
    expect(state.reasons.some((r) => r.id === 'operat-ko')).toBe(true);
  });

  it('returns AMBER when OPERAT active + issues > 2', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      operatModuleActive: true,
      efaDashboard: { total_sites: 5, open_issues: 4 },
    });
    expect(state.level).toBe('AMBER');
    expect(state.reasons.some((r) => r.id === 'operat-partial')).toBe(true);
  });

  it('ignores OPERAT when operatModuleActive = false', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      operatModuleActive: false,
      efaDashboard: { total_sites: 0 },
    });
    expect(state.reasons.some((r) => r.id?.startsWith('operat'))).toBe(false);
  });
});

// ── Gating flags ────────────────────────────────────────────────────────────

describe('computeDataReadinessState — gating', () => {
  it('canExportOperat = false when operat KO', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      operatModuleActive: true,
      efaDashboard: { total_sites: 0 },
    });
    expect(state.gating.canExportOperat).toBe(false);
  });

  it('canAuditAll = false when factures KO', () => {
    const state = computeDataReadinessState(makeActivation(), {
      ...OK_SIGNALS,
      billingMonthCount: 1,
    });
    expect(state.gating.canAuditAll).toBe(false);
  });

  it('canSimulatePurchase = false when conso KO', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 0 }), OK_SIGNALS);
    expect(state.gating.canSimulatePurchase).toBe(false);
  });

  it('all gates open when everything OK', () => {
    const state = computeDataReadinessState(makeActivation(), OK_SIGNALS);
    expect(state.gating.canExportOperat).toBe(true);
    expect(state.gating.canAuditAll).toBe(true);
    expect(state.gating.canSimulatePurchase).toBe(true);
  });
});

// ── Badge mapping ───────────────────────────────────────────────────────────

describe('computeDataReadinessState — badge', () => {
  it('GREEN → ok / OK', () => {
    const state = computeDataReadinessState(makeActivation(), OK_SIGNALS);
    expect(state.badgeStatus).toBe('ok');
    expect(state.badgeLabel).toBe('OK');
  });

  it('AMBER → warn / Partiel', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 50 }), OK_SIGNALS);
    expect(state.badgeStatus).toBe('warn');
    expect(state.badgeLabel).toBe('Partiel');
  });

  it('RED → crit / Incomplet', () => {
    const state = computeDataReadinessState(makeActivation({ consoCoverage: 0 }), OK_SIGNALS);
    expect(state.badgeStatus).toBe('crit');
    expect(state.badgeLabel).toBe('Incomplet');
  });
});

// ── Reasons cap ─────────────────────────────────────────────────────────────

describe('computeDataReadinessState — reasons cap', () => {
  it('caps reasons at 3', () => {
    // Trigger ALL possible reasons: conso-ko + factures-ko + operat-ko + connecteurs-ko
    const state = computeDataReadinessState(
      makeActivation({ consoCoverage: 0, activatedCount: 0 }),
      {
        billingMonthCount: 0,
        efaDashboard: { total_sites: 0 },
        connectors: [],
        operatModuleActive: true,
        hasManualImport: false,
      }
    );
    expect(state.reasons.length).toBeLessThanOrEqual(3);
  });
});

// ── Source-guard tests ──────────────────────────────────────────────────────

describe('source-guard', () => {
  it('constants.js exports READINESS_GATE', () => {
    const src = fs.readFileSync(path.resolve(__dirname, '../../lib/constants.js'), 'utf-8');
    expect(src).toMatch(/export\s+const\s+READINESS_GATE/);
  });

  it('AppShell imports DataReadinessBadge', () => {
    const src = fs.readFileSync(path.resolve(__dirname, '../../layout/AppShell.jsx'), 'utf-8');
    expect(src).toMatch(/DataReadinessBadge/);
  });

  it('useActivationData fetches tertiaire dashboard', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../hooks/useActivationData.js'),
      'utf-8'
    );
    expect(src).toMatch(/getTertiaireDashboard/);
  });

  it('DataReadinessBadge uses Badge + popover', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../components/DataReadinessBadge.jsx'),
      'utf-8'
    );
    expect(src).toMatch(/Badge/);
    expect(src).toMatch(/aria-haspopup/);
  });
});
