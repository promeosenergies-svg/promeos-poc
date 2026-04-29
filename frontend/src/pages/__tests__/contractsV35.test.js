/**
 * PROMEOS — V35 Contracts tests
 *
 * 1) ComplianceSignalsContract: normalize, empty, invalid
 * 2) BillingInsightsContract: normalize, empty, invalid
 * 3) Guard: modules purs (no React, no API)
 *
 * NOTE Phase 1.4.c (29/04/2026) : Les sections Lever Engine (3, 4, 5 legacy)
 * qui invoquaient computeActionableLevers ont été supprimées — la logique
 * est désormais dans backend/services/lever_engine_service.py.
 * Couverture équivalente dans backend/tests/test_lever_engine_service.py.
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

// ── Fixtures ─────────────────────────────────────────────────────────────────

const makeComplianceSignals = () => ({
  signals: [
    {
      source: 'operat',
      code: 'DT-2030',
      severity: 'critical',
      due_date: '2030-12-31',
      proof_expected: 'Declaration OPERAT',
      label: 'Echeance 2030',
    },
    {
      source: 'bacs',
      code: 'BACS-CL1',
      severity: 'high',
      proof_expected: 'Certificat BACS classe A',
      label: 'GTB classe A',
    },
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
    expect(normalizeBillingInsights({ anomalies_count: 0, total_loss_eur: 0 })).toBe(
      EMPTY_BILLING_INSIGHTS
    );
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
// 3) Guard: modules purs
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: V35 contracts sont des modules purs', () => {
  const compSrc = readFileSync(
    resolve(__dirname, '..', '..', 'models', 'complianceSignalsContract.js'),
    'utf8'
  );
  const billSrc = readFileSync(
    resolve(__dirname, '..', '..', 'models', 'billingInsightsContract.js'),
    'utf8'
  );

  it("complianceSignalsContract n'importe pas React", () => {
    expect(compSrc).not.toContain("from 'react'");
  });

  it("billingInsightsContract n'importe pas React", () => {
    expect(billSrc).not.toContain("from 'react'");
  });

  it("aucun contract n'importe d'API", () => {
    expect(compSrc).not.toContain('services/api');
    expect(billSrc).not.toContain('services/api');
  });

  // Phase 1.4.c (29/04/2026) : leverEngineModel.js migré vers
  // backend/services/lever_engine_service.py. Source-guard équivalent
  // désormais côté pytest dans backend/tests/test_lever_engine_service.py.
  // Tests JS invoquant computeActionableLevers supprimés.
});
