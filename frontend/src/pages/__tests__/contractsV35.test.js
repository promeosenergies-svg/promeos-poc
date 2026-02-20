/**
 * PROMEOS — V35 Contracts + Lever Engine enrichment tests
 *
 * 1) ComplianceSignalsContract: normalize, empty, invalid
 * 2) BillingInsightsContract: normalize, empty, invalid
 * 3) Lever Engine: fallback V33 (sans contracts)
 * 4) Lever Engine: enrichment avec complianceSignals
 * 5) Lever Engine: enrichment avec billingInsights
 * 6) Guard: aucun crash si contracts absents/vides
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  normalizeComplianceSignals,
  EMPTY_COMPLIANCE_SIGNALS,
  isComplianceAvailable,
} from '../../models/complianceSignalsContract';

import {
  normalizeBillingInsights,
  EMPTY_BILLING_INSIGHTS,
  isBillingInsightsAvailable,
} from '../../models/billingInsightsContract';

import { computeActionableLevers } from '../../models/leverEngineModel';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const makeKpis = (ov = {}) => ({
  total: 10, conformes: 7, nonConformes: 2, aRisque: 1, risqueTotal: 30000, ...ov,
});

const makeBilling = (ov = {}) => ({
  total_invoices: 50, total_eur: 500000, total_loss_eur: 8000, invoices_with_anomalies: 5, ...ov,
});

const makeComplianceSignals = () => ({
  signals: [
    { source: 'operat', code: 'DT-2030', severity: 'critical', due_date: '2030-12-31', proof_expected: 'Declaration OPERAT', label: 'Echeance 2030' },
    { source: 'bacs', code: 'BACS-CL1', severity: 'high', proof_expected: 'Certificat BACS classe A', label: 'GTB classe A' },
    { source: 'decret_tertiaire', code: 'DT-SUIVI', severity: 'medium', label: 'Suivi annuel' },
  ],
});

const makeBillingInsights = () => ({
  anomalies_count: 8,
  total_loss_eur: 12000,
  invoices_impacted: 15,
  confidence: 'high',
  proof_links: ['invoice-audit-2024-q3.pdf'],
});

// ══════════════════════════════════════════════════════════════════════════════
// 1) ComplianceSignalsContract
// ══════════════════════════════════════════════════════════════════════════════

describe('ComplianceSignalsContract', () => {
  it('normalise des signaux valides', () => {
    const result = normalizeComplianceSignals(makeComplianceSignals());
    expect(result.signals).toHaveLength(3);
    expect(result.coverage.total).toBe(3);
    expect(result.coverage.with_proof).toBe(2);
    expect(result.coverage.with_due_date).toBe(1);
    expect(result.missing).toContain('due_date');
  });

  it('retourne EMPTY pour null/undefined/invalide', () => {
    expect(normalizeComplianceSignals(null)).toBe(EMPTY_COMPLIANCE_SIGNALS);
    expect(normalizeComplianceSignals(undefined)).toBe(EMPTY_COMPLIANCE_SIGNALS);
    expect(normalizeComplianceSignals('string')).toBe(EMPTY_COMPLIANCE_SIGNALS);
    expect(normalizeComplianceSignals({})).toBe(EMPTY_COMPLIANCE_SIGNALS);
    expect(normalizeComplianceSignals({ signals: [] })).toBe(EMPTY_COMPLIANCE_SIGNALS);
  });

  it('filtre les signaux invalides (sans source/code)', () => {
    const result = normalizeComplianceSignals({
      signals: [
        { source: 'operat', code: 'DT-2030', severity: 'high' },
        { source: null, code: 'X' },
        { noSource: true },
      ],
    });
    expect(result.signals).toHaveLength(1);
  });

  it('isComplianceAvailable detecte la presence', () => {
    expect(isComplianceAvailable(null)).toBe(false);
    expect(isComplianceAvailable(EMPTY_COMPLIANCE_SIGNALS)).toBe(false);
    expect(isComplianceAvailable(normalizeComplianceSignals(makeComplianceSignals()))).toBe(true);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2) BillingInsightsContract
// ══════════════════════════════════════════════════════════════════════════════

describe('BillingInsightsContract', () => {
  it('normalise des insights valides', () => {
    const result = normalizeBillingInsights(makeBillingInsights());
    expect(result.anomalies_count).toBe(8);
    expect(result.total_loss_eur).toBe(12000);
    expect(result.invoices_impacted).toBe(15);
    expect(result.confidence).toBe('high');
    expect(result.proof_links).toHaveLength(1);
  });

  it('retourne EMPTY pour null/undefined/invalide', () => {
    expect(normalizeBillingInsights(null)).toBe(EMPTY_BILLING_INSIGHTS);
    expect(normalizeBillingInsights(undefined)).toBe(EMPTY_BILLING_INSIGHTS);
    expect(normalizeBillingInsights(42)).toBe(EMPTY_BILLING_INSIGHTS);
    expect(normalizeBillingInsights({ anomalies_count: 0, total_loss_eur: 0 })).toBe(EMPTY_BILLING_INSIGHTS);
  });

  it('clampe les valeurs negatives a 0', () => {
    const result = normalizeBillingInsights({ anomalies_count: -5, total_loss_eur: 100 });
    expect(result.anomalies_count).toBe(0);
    expect(result.total_loss_eur).toBe(100);
  });

  it('normalise la confiance en "low" par defaut', () => {
    const result = normalizeBillingInsights({ anomalies_count: 1, confidence: 'invalid' });
    expect(result.confidence).toBe('low');
  });

  it('isBillingInsightsAvailable detecte la presence', () => {
    expect(isBillingInsightsAvailable(null)).toBe(false);
    expect(isBillingInsightsAvailable(EMPTY_BILLING_INSIGHTS)).toBe(false);
    expect(isBillingInsightsAvailable(normalizeBillingInsights(makeBillingInsights()))).toBe(true);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3) Lever Engine: fallback V33 (sans contracts)
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever Engine V35 — fallback sans contracts', () => {
  it('fonctionne identiquement a V33 sans contracts', () => {
    const result = computeActionableLevers({ kpis: makeKpis(), billingSummary: makeBilling() });

    expect(result.totalLevers).toBe(4);
    expect(result.leversByType.conformite).toBe(2);
    expect(result.leversByType.facturation).toBe(1);
    expect(result.leversByType.optimisation).toBe(1);
  });

  it('pas de crash avec contracts undefined', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      complianceSignals: undefined,
      billingInsights: undefined,
    });
    expect(result.totalLevers).toBe(4);
  });

  it('pas de crash avec contracts null', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      complianceSignals: null,
      billingInsights: null,
    });
    expect(result.totalLevers).toBe(4);
  });

  it('pas de crash avec contracts EMPTY', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      complianceSignals: EMPTY_COMPLIANCE_SIGNALS,
      billingInsights: EMPTY_BILLING_INSIGHTS,
    });
    expect(result.totalLevers).toBe(4);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4) Lever Engine: enrichment avec complianceSignals
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever Engine V35 — complianceSignals enrichment', () => {
  it('enrichit le label conformite avec le compte de signaux critiques', () => {
    const signals = normalizeComplianceSignals(makeComplianceSignals());
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: {},
      complianceSignals: signals,
    });

    const ncLever = result.topLevers.find((l) => l.actionKey === 'lev-conf-nc');
    expect(ncLever).toBeTruthy();
    expect(ncLever.label).toContain('signal');
    expect(ncLever.label).toContain('critique');
  });

  it('ajoute proofHint depuis le premier signal avec proof_expected', () => {
    const signals = normalizeComplianceSignals(makeComplianceSignals());
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: {},
      complianceSignals: signals,
    });

    const ncLever = result.topLevers.find((l) => l.actionKey === 'lev-conf-nc');
    expect(ncLever.proofHint).toContain('OPERAT');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5) Lever Engine: enrichment avec billingInsights
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever Engine V35 — billingInsights enrichment', () => {
  it('utilise anomalies_count de billingInsights quand disponible', () => {
    const insights = normalizeBillingInsights(makeBillingInsights());
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: makeBilling({ invoices_with_anomalies: 3 }),
      billingInsights: insights,
    });

    const factLever = result.topLevers.find((l) => l.actionKey === 'lev-fact-anom');
    expect(factLever).toBeTruthy();
    // billingInsights.anomalies_count = 8 overrides billingSummary.invoices_with_anomalies = 3
    expect(factLever.label).toContain('8 anomalie');
  });

  it('ajoute le label confiance dans le label facturation', () => {
    const insights = normalizeBillingInsights(makeBillingInsights());
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: makeBilling(),
      billingInsights: insights,
    });

    const factLever = result.topLevers.find((l) => l.actionKey === 'lev-fact-anom');
    expect(factLever.label).toContain('confiance haute');
  });

  it('prend le max entre billingInsights.total_loss et billingSummary.total_loss', () => {
    const insights = normalizeBillingInsights({ anomalies_count: 2, total_loss_eur: 15000, confidence: 'medium' });
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: { total_loss_eur: 8000, total_eur: 0 },
      billingInsights: insights,
    });

    const factLever = result.topLevers.find((l) => l.type === 'facturation');
    expect(factLever.impactEur).toBe(15000); // max(15000, 8000)
  });

  it('ajoute proofLinks depuis billingInsights', () => {
    const insights = normalizeBillingInsights(makeBillingInsights());
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: makeBilling(),
      billingInsights: insights,
    });

    const factLever = result.topLevers.find((l) => l.type === 'facturation');
    expect(factLever.proofLinks).toContain('invoice-audit-2024-q3.pdf');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 6) Guard: modules purs
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: V35 contracts sont des modules purs', () => {
  const compSrc = readFileSync(resolve(__dirname, '..', '..', 'models', 'complianceSignalsContract.js'), 'utf8');
  const billSrc = readFileSync(resolve(__dirname, '..', '..', 'models', 'billingInsightsContract.js'), 'utf8');

  it('complianceSignalsContract n\'importe pas React', () => {
    expect(compSrc).not.toContain("from 'react'");
  });

  it('billingInsightsContract n\'importe pas React', () => {
    expect(billSrc).not.toContain("from 'react'");
  });

  it('aucun contract n\'importe d\'API', () => {
    expect(compSrc).not.toContain('services/api');
    expect(billSrc).not.toContain('services/api');
  });

  it('leverEngineModel importe les 2 contracts', () => {
    const engineSrc = readFileSync(resolve(__dirname, '..', '..', 'models', 'leverEngineModel.js'), 'utf8');
    expect(engineSrc).toContain('complianceSignalsContract');
    expect(engineSrc).toContain('billingInsightsContract');
  });
});
