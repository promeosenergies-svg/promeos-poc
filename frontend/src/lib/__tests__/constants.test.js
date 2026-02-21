/**
 * PROMEOS — constants.test.js (Phase 2B)
 * Unit tests for centralized thresholds & helpers.
 */
import { describe, it, expect } from 'vitest';
import {
  RISK_THRESHOLDS,
  COVERAGE_THRESHOLDS,
  CONFORMITY_THRESHOLDS,
  MATURITY_THRESHOLDS,
  READINESS_WEIGHTS,
  ACTIONS_SCORE,
  ANOMALY_THRESHOLDS,
  STATUS_CONFIG,
  getStatusBadgeProps,
  getRiskStatus,
} from '../constants';

// ── STATUS_CONFIG completeness ──────────────────────────────────────────────

describe('STATUS_CONFIG', () => {
  it('has all 5 conformité statuses', () => {
    expect(Object.keys(STATUS_CONFIG)).toEqual(
      expect.arrayContaining(['conforme', 'non_conforme', 'a_risque', 'a_evaluer', 'derogation'])
    );
  });

  it('each entry has variant + label', () => {
    for (const [, cfg] of Object.entries(STATUS_CONFIG)) {
      expect(cfg).toHaveProperty('variant');
      expect(cfg).toHaveProperty('label');
      expect(typeof cfg.variant).toBe('string');
      expect(typeof cfg.label).toBe('string');
    }
  });

  it('labels use proper French accents', () => {
    expect(STATUS_CONFIG.a_risque.label).toBe('À risque');
    expect(STATUS_CONFIG.a_evaluer.label).toBe('À évaluer');
  });
});

// ── getStatusBadgeProps ─────────────────────────────────────────────────────

describe('getStatusBadgeProps', () => {
  it('known status → returns matching variant and label', () => {
    const { variant, label } = getStatusBadgeProps('conforme');
    expect(variant).toBe('ok');
    expect(label).toBe('Conforme');
  });

  it('non_conforme → crit', () => {
    expect(getStatusBadgeProps('non_conforme').variant).toBe('crit');
  });

  it('a_risque → warn with accented label', () => {
    const { variant, label } = getStatusBadgeProps('a_risque');
    expect(variant).toBe('warn');
    expect(label).toBe('À risque');
  });

  it('unknown status → neutral fallback with raw status as label', () => {
    const { variant, label } = getStatusBadgeProps('unknown_status');
    expect(variant).toBe('neutral');
    expect(label).toBe('unknown_status');
  });

  it('null/undefined → neutral fallback', () => {
    expect(getStatusBadgeProps(null).variant).toBe('neutral');
    expect(getStatusBadgeProps(undefined).variant).toBe('neutral');
  });
});

// ── getRiskStatus ───────────────────────────────────────────────────────────

describe('getRiskStatus', () => {
  it('above org crit threshold → crit', () => {
    expect(getRiskStatus(60000)).toBe('crit');
  });

  it('between org warn and crit → warn', () => {
    expect(getRiskStatus(25000)).toBe('warn');
  });

  it('below org warn → ok', () => {
    expect(getRiskStatus(5000)).toBe('ok');
  });

  it('exactly at crit boundary → warn (not strictly >)', () => {
    expect(getRiskStatus(50000)).toBe('warn');
  });

  it('exactly at warn boundary → ok (not strictly >)', () => {
    expect(getRiskStatus(10000)).toBe('ok');
  });

  it('custom thresholds (site-level)', () => {
    expect(getRiskStatus(15000, RISK_THRESHOLDS.site)).toBe('crit');
    expect(getRiskStatus(5000, RISK_THRESHOLDS.site)).toBe('warn');
    expect(getRiskStatus(2000, RISK_THRESHOLDS.site)).toBe('ok');
  });

  it('zero amount → ok', () => {
    expect(getRiskStatus(0)).toBe('ok');
  });
});

// ── Threshold sanity ────────────────────────────────────────────────────────

describe('threshold sanity', () => {
  it('RISK_THRESHOLDS.org.crit > warn', () => {
    expect(RISK_THRESHOLDS.org.crit).toBeGreaterThan(RISK_THRESHOLDS.org.warn);
  });

  it('RISK_THRESHOLDS.site.crit > warn', () => {
    expect(RISK_THRESHOLDS.site.crit).toBeGreaterThan(RISK_THRESHOLDS.site.warn);
  });

  it('COVERAGE_THRESHOLDS hierarchy: suspicious < warn < opportunity', () => {
    expect(COVERAGE_THRESHOLDS.suspicious).toBeLessThan(COVERAGE_THRESHOLDS.warn);
    expect(COVERAGE_THRESHOLDS.warn).toBeLessThan(COVERAGE_THRESHOLDS.opportunity);
  });

  it('CONFORMITY_THRESHOLDS: warn < positive', () => {
    expect(CONFORMITY_THRESHOLDS.warn).toBeLessThan(CONFORMITY_THRESHOLDS.positive);
  });

  it('MATURITY_THRESHOLDS: crit < warn', () => {
    expect(MATURITY_THRESHOLDS.crit).toBeLessThan(MATURITY_THRESHOLDS.warn);
  });

  it('READINESS_WEIGHTS sum to 1.0', () => {
    const sum = READINESS_WEIGHTS.data + READINESS_WEIGHTS.conformity + READINESS_WEIGHTS.actions;
    expect(sum).toBeCloseTo(1.0, 5);
  });

  it('ACTIONS_SCORE.withIssues < noIssues', () => {
    expect(ACTIONS_SCORE.withIssues).toBeLessThan(ACTIONS_SCORE.noIssues);
  });

  it('ANOMALY_THRESHOLDS.critical is positive integer', () => {
    expect(ANOMALY_THRESHOLDS.critical).toBeGreaterThan(0);
    expect(Number.isInteger(ANOMALY_THRESHOLDS.critical)).toBe(true);
  });
});
