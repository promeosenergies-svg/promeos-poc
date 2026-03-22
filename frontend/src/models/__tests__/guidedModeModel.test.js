/**
 * guidedModeModel.test.js — Unit tests for Guided Mode, NBA, Données metrics.
 * Pure function tests + source-guard.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
  GUIDED_STEPS,
  computeGuidedSteps,
  computeNextBestAction,
  computeDonneesMetrics,
} from '../guidedModeModel';

const modelSrc = readFileSync(resolve(__dirname, '../guidedModeModel.js'), 'utf-8');

// ── Fixtures ──
const FIXTURE_SUMMARY = { total_findings: 10, pct_ok: 60 };
const FIXTURE_SITES = [
  {
    site_id: 1,
    site_nom: 'Site A',
    data_quality_gate: 'OK',
    findings: [{ status: 'NOK' }],
    conso_kwh_an: 1000,
    surface_m2: 500,
  },
  {
    site_id: 2,
    site_nom: 'Site B',
    data_quality_gate: 'OK',
    findings: [{ status: 'OK' }],
    conso_kwh_an: 2000,
    surface_m2: 800,
  },
];
const FIXTURE_BUNDLE = { summary: FIXTURE_SUMMARY, sites: FIXTURE_SITES };
const NOW = new Date('2026-03-01');

// ============================================================
// Source-guard
// ============================================================
describe('source-guard — guidedModeModel', () => {
  it('has no React imports', () => {
    expect(modelSrc).not.toMatch(/from\s+['"]react['"]/);
  });

  it('has no API service imports', () => {
    expect(modelSrc).not.toMatch(/from\s+['"]\.\.\/services\/api['"]/);
  });

  it('exports GUIDED_STEPS', () => {
    expect(modelSrc).toMatch(/export const GUIDED_STEPS/);
  });

  it('exports computeGuidedSteps', () => {
    expect(modelSrc).toMatch(/export function computeGuidedSteps/);
  });

  it('exports computeNextBestAction', () => {
    expect(modelSrc).toMatch(/export function computeNextBestAction/);
  });

  it('exports computeDonneesMetrics', () => {
    expect(modelSrc).toMatch(/export function computeDonneesMetrics/);
  });
});

// ============================================================
// GUIDED_STEPS constant
// ============================================================
describe('GUIDED_STEPS', () => {
  it('has 5 steps', () => {
    expect(GUIDED_STEPS).toHaveLength(5);
  });

  it('step IDs are correct', () => {
    const ids = GUIDED_STEPS.map((s) => s.id);
    expect(ids).toEqual(['assujettissement', 'donnees', 'deadlines', 'plan', 'preuves']);
  });

  it('all steps have FR labels and descriptions', () => {
    for (const step of GUIDED_STEPS) {
      expect(step.label.length).toBeGreaterThan(2);
      expect(step.description.length).toBeGreaterThan(10);
      expect(step.cta.length).toBeGreaterThan(3);
    }
  });

  it('step donnees has blocking: true', () => {
    const donnees = GUIDED_STEPS.find((s) => s.id === 'donnees');
    expect(donnees.blocking).toBe(true);
  });

  it('all steps have ctaTarget', () => {
    for (const step of GUIDED_STEPS) {
      expect(step.ctaTarget).toBeDefined();
      expect(step.ctaTarget.tab || step.ctaTarget.path).toBeTruthy();
    }
  });
});

// ============================================================
// computeGuidedSteps
// ============================================================
describe('computeGuidedSteps', () => {
  it('returns 5 steps', () => {
    const steps = computeGuidedSteps(FIXTURE_BUNDLE, FIXTURE_SITES, FIXTURE_SUMMARY, {});
    expect(steps).toHaveLength(5);
  });

  it('step 1 (assujettissement) is complete when findings exist', () => {
    const steps = computeGuidedSteps(FIXTURE_BUNDLE, FIXTURE_SITES, FIXTURE_SUMMARY, {
      obligations: [{ id: 'bacs', statut: 'non_conforme' }],
    });
    expect(steps[0].status).toBe('complete');
  });

  it('step 1 is pending when no sites', () => {
    const steps = computeGuidedSteps(null, [], null, {});
    expect(steps[0].status).toBe('pending');
  });

  it('step 2 (donnees) is blocked when any site BLOCKED', () => {
    const blockedSites = [{ site_id: 1, data_quality_gate: 'BLOCKED', findings: [] }];
    const steps = computeGuidedSteps(null, blockedSites, FIXTURE_SUMMARY, {});
    expect(steps[1].status).toBe('blocked');
  });

  it('cascade: steps 3-5 blocked when donnees is blocked', () => {
    const blockedSites = [{ site_id: 1, data_quality_gate: 'BLOCKED', findings: [] }];
    const steps = computeGuidedSteps(null, blockedSites, FIXTURE_SUMMARY, {
      obligations: [{ id: 'bacs' }],
    });
    expect(steps[0].status).toBe('complete'); // assujettissement
    expect(steps[1].status).toBe('blocked'); // donnees
    expect(steps[2].status).toBe('blocked'); // deadlines
    expect(steps[3].status).toBe('blocked'); // plan
    expect(steps[4].status).toBe('blocked'); // preuves
  });

  it('all steps can reach complete', () => {
    const signals = {
      obligations: [{ id: 'bacs', statut: 'conforme', echeance: '2030-01-01' }],
      actionableFindings: [],
      proofFiles: { bacs: [{ name: 'proof.pdf' }] },
    };
    const goodSites = [{ site_id: 1, data_quality_gate: 'OK', findings: [{ status: 'OK' }] }];
    const steps = computeGuidedSteps(FIXTURE_BUNDLE, goodSites, FIXTURE_SUMMARY, signals);
    expect(steps[0].status).toBe('complete');
    expect(steps[1].status).toBe('complete');
    expect(steps[2].status).toBe('complete');
    expect(steps[3].status).toBe('complete');
    expect(steps[4].status).toBe('complete');
  });

  it('plan step is in_progress when actionable findings remain', () => {
    const steps = computeGuidedSteps(FIXTURE_BUNDLE, FIXTURE_SITES, FIXTURE_SUMMARY, {
      obligations: [{ id: 'bacs' }],
      actionableFindings: [{ id: 1 }],
    });
    expect(steps[3].status).toBe('in_progress');
  });
});

// ============================================================
// computeNextBestAction — deterministic waterfall
// ============================================================
describe('computeNextBestAction', () => {
  it('P1: returns data-blocker when any site BLOCKED', () => {
    const blockedSites = [{ site_id: 1, data_quality_gate: 'BLOCKED' }];
    const nba = computeNextBestAction(null, blockedSites, null, {}, NOW);
    expect(nba.id).toBe('nba-data-blocker');
    expect(nba.severity).toBe('critical');
    expect(nba.ctaAction).toEqual({ type: 'tab', tab: 'donnees' });
  });

  it('P2: returns deadline when obligation deadline < 90 days', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [
          {
            code: 'bacs',
            regulation: 'BACS',
            statut: 'non_conforme',
            echeance: '2026-04-15',
            sites_concernes: 3,
          },
        ],
        actionableFindings: [{ id: 1 }],
      },
      NOW
    );
    expect(nba.id).toBe('nba-deadline-bacs');
    expect(nba.severity).toBe('high');
    expect(nba.ctaAction.tab).toBe('obligations');
  });

  it('P2: skips deadline > 90 days away', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [
          {
            code: 'bacs',
            regulation: 'BACS',
            statut: 'non_conforme',
            echeance: '2030-01-01',
            sites_concernes: 2,
          },
        ],
        actionableFindings: [{ id: 1, severity: 'high' }],
      },
      NOW
    );
    // Should skip P2 and hit P4 (findings)
    expect(nba.id).toBe('nba-findings');
  });

  it('P3: returns missing-proofs when conforme obligations have no proof', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [
          { id: 'bacs', code: 'bacs', statut: 'conforme', echeance: null },
          { id: 'dt', code: 'dt', statut: 'conforme', echeance: null },
        ],
        actionableFindings: [],
        proofFiles: {},
      },
      NOW
    );
    expect(nba.id).toBe('nba-missing-proofs');
    expect(nba.severity).toBe('medium');
    expect(nba.ctaAction.tab).toBe('preuves');
  });

  it('P4: returns findings when NOK exist', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [],
        actionableFindings: [
          { id: 1, severity: 'high' },
          { id: 2, severity: 'medium' },
        ],
      },
      NOW
    );
    expect(nba.id).toBe('nba-findings');
    expect(nba.title).toContain('2');
  });

  it('P4: severity is critical when any finding is critical', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [],
        actionableFindings: [{ id: 1, severity: 'critical' }],
      },
      NOW
    );
    expect(nba.severity).toBe('critical');
  });

  it('P5: returns all-good when nothing actionable', () => {
    const nba = computeNextBestAction(
      null,
      FIXTURE_SITES,
      FIXTURE_SUMMARY,
      {
        obligations: [{ id: 'bacs', code: 'bacs', statut: 'conforme' }],
        actionableFindings: [],
        proofFiles: { bacs: [{ name: 'proof.pdf' }] },
      },
      NOW
    );
    expect(nba.id).toBe('nba-all-good');
    expect(nba.severity).toBe('low');
  });

  it('is deterministic: same input → same output', () => {
    const signals = {
      obligations: [
        {
          code: 'dt',
          regulation: 'DT',
          statut: 'non_conforme',
          echeance: '2026-05-01',
          sites_concernes: 5,
        },
      ],
      actionableFindings: [{ id: 1 }],
    };
    const a = computeNextBestAction(null, FIXTURE_SITES, FIXTURE_SUMMARY, signals, NOW);
    const b = computeNextBestAction(null, FIXTURE_SITES, FIXTURE_SUMMARY, signals, NOW);
    expect(a).toEqual(b);
  });

  it('all NBAs have required fields', () => {
    const scenarios = [
      computeNextBestAction(null, [{ data_quality_gate: 'BLOCKED' }], null, {}, NOW),
      computeNextBestAction(
        null,
        FIXTURE_SITES,
        FIXTURE_SUMMARY,
        { obligations: [], actionableFindings: [] },
        NOW
      ),
    ];
    for (const nba of scenarios) {
      expect(nba).toHaveProperty('id');
      expect(nba).toHaveProperty('title');
      expect(nba).toHaveProperty('description');
      expect(nba).toHaveProperty('severity');
      expect(nba).toHaveProperty('ctaLabel');
      expect(nba).toHaveProperty('ctaAction');
      expect(nba).toHaveProperty('icon');
    }
  });
});

// ============================================================
// computeDonneesMetrics
// ============================================================
describe('computeDonneesMetrics', () => {
  it('returns valid shape', () => {
    const m = computeDonneesMetrics(FIXTURE_SITES, [], {});
    expect(m).toHaveProperty('completude_pct');
    expect(m).toHaveProperty('confiance_level');
    expect(m).toHaveProperty('confiance_label');
    expect(m).toHaveProperty('couverture_factures_mois');
    expect(m).toHaveProperty('couverture_factures_cible');
    expect(m).toHaveProperty('gaps');
    expect(Array.isArray(m.gaps)).toBe(true);
  });

  it('computes completude from DQ results when available', () => {
    const m = computeDonneesMetrics(
      FIXTURE_SITES,
      [
        { coverage_pct: 80, confidence_score: 90 },
        { coverage_pct: 60, confidence_score: 70 },
      ],
      {}
    );
    expect(m.completude_pct).toBe(70);
  });

  it('falls back to site-level estimation when no DQ', () => {
    const m = computeDonneesMetrics(FIXTURE_SITES, [], {});
    expect(m.completude_pct).toBe(100); // both sites have findings + conso
  });

  it('confiance is high when avgConfidence >= 70', () => {
    const m = computeDonneesMetrics([], [{ coverage_pct: 90, confidence_score: 85 }], {});
    expect(m.confiance_level).toBe('high');
    expect(m.confiance_label).toBe('Élevée');
  });

  it('confiance is low when avgConfidence < 40', () => {
    const m = computeDonneesMetrics([], [{ coverage_pct: 20, confidence_score: 20 }], {});
    expect(m.confiance_level).toBe('low');
    expect(m.confiance_label).toBe('Faible');
  });

  it('identifies gaps for missing data', () => {
    const emptySites = [{ site_id: 1, findings: [] }];
    const m = computeDonneesMetrics(emptySites, [], { billingMonthCount: 6 });
    expect(m.gaps.length).toBeGreaterThan(0);
    expect(m.gaps.every((g) => g.ctaPath && g.ctaLabel)).toBe(true);
  });

  it('no patrimoine gap when completude >= 80', () => {
    const m = computeDonneesMetrics(
      FIXTURE_SITES,
      [
        { coverage_pct: 90, confidence_score: 80 },
        { coverage_pct: 85, confidence_score: 80 },
      ],
      { billingMonthCount: 24 }
    );
    expect(m.gaps.find((g) => g.id === 'patrimoine_incomplet')).toBeUndefined();
  });

  it('billing gap when months < cible', () => {
    const m = computeDonneesMetrics(FIXTURE_SITES, [], { billingMonthCount: 12 });
    expect(m.gaps.find((g) => g.id === 'factures_insuffisantes')).toBeDefined();
  });

  it('no billing gap when months >= cible', () => {
    const m = computeDonneesMetrics(FIXTURE_SITES, [{ coverage_pct: 90, confidence_score: 80 }], {
      billingMonthCount: 24,
    });
    expect(m.gaps.find((g) => g.id === 'factures_insuffisantes')).toBeUndefined();
  });
});
