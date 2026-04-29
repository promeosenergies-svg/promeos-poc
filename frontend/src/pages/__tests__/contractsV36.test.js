/**
 * PROMEOS — V36 Achat d'Energie Contracts + Lever Engine tests
 *
 * 1) PurchaseSignalsContract: normalize, empty, available
 * 2) Lever Engine V36: achat levers (renewal, missing, none)
 * 3) Lever Engine V36: fallback (sans purchaseSignals)
 * 4) LeverActionModel: achat templates
 * 5) ImpactDecisionPanel: V36 guards
 * 6) Guard: modules purs (no React, no API)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  normalizePurchaseSignals,
  EMPTY_PURCHASE_SIGNALS,
  isPurchaseAvailable,
} from '../../models/purchaseSignalsContract';

import { computeActionableLevers } from '../../models/leverEngineModel';
import { LEVER_ACTION_TEMPLATES, buildActionPayload } from '../../models/leverActionModel';

// ── Helpers ─────────────────────────────────────────────────────────────────

const readSrc = (relPath) => readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

// ── Fixtures ────────────────────────────────────────────────────────────────

const makeKpis = (ov = {}) => ({
  total: 10,
  conformes: 7,
  nonConformes: 2,
  aRisque: 1,
  risqueTotal: 30000,
  ...ov,
});

const makeBilling = (ov = {}) => ({
  total_invoices: 50,
  total_eur: 500000,
  total_loss_eur: 8000,
  invoices_with_anomalies: 5,
  ...ov,
});

const makeRenewalsResponse = (count = 3) => ({
  total: count,
  renewals: Array.from({ length: count }, (_, i) => ({
    contract_id: 100 + i,
    site_id: 1 + (i % 2),
    site_nom: `Site ${1 + (i % 2)}`,
    supplier_name: 'EDF',
    energy_type: 'elec',
    end_date: '2026-05-15',
    notice_period_days: 90,
    auto_renew: false,
    days_until_expiry: 60 + i * 20, // 60, 80, 100
  })),
});

const makeContractsResponse = (count = 5) => ({
  total: count,
  contracts: Array.from({ length: count }, (_, i) => ({
    id: 200 + i,
    site_id: 1 + i,
    energy_type: 'elec',
    supplier_name: 'EDF',
    start_date: '2024-01-01',
    end_date: '2026-12-31',
  })),
});

const makePurchaseSignals = (ov = {}) => {
  const raw = {
    renewals: makeRenewalsResponse(3),
    contracts: makeContractsResponse(5),
    totalSites: 10,
    ...ov,
  };
  return normalizePurchaseSignals(raw);
};

// ══════════════════════════════════════════════════════════════════════════════
// 1) PurchaseSignalsContract
// ══════════════════════════════════════════════════════════════════════════════

describe('PurchaseSignalsContract', () => {
  it('normalise des donnees valides', () => {
    const result = makePurchaseSignals();
    expect(result.totalContracts).toBe(5);
    expect(result.totalSites).toBe(10);
    expect(result.renewals).toHaveLength(3);
  });

  it('calcule expiringSoonCount (contrats <= 90j)', () => {
    const result = makePurchaseSignals();
    // days_until_expiry: 60, 80, 100 — 60 et 80 sont <= 90
    expect(result.expiringSoonCount).toBe(2);
  });

  it('deduplique expiringSoonSites', () => {
    const result = makePurchaseSignals();
    // site_ids: 1, 2, 1 — seuls 60 et 80 qualifient, sites 1 et 2
    expect(result.expiringSoonSites).toContain(1);
    expect(result.expiringSoonSites).toContain(2);
    expect(new Set(result.expiringSoonSites).size).toBe(result.expiringSoonSites.length);
  });

  it('calcule coverageContractsPct', () => {
    const result = makePurchaseSignals();
    // 5 contrats sur sites 1-5, total 10 sites => 50%
    expect(result.coverageContractsPct).toBe(50);
  });

  it('calcule missingContractsCount', () => {
    const result = makePurchaseSignals();
    // 10 sites - 5 avec contrat = 5 manquants
    expect(result.missingContractsCount).toBe(5);
  });

  it('estimatedExposureEur est null en V1', () => {
    const result = makePurchaseSignals();
    expect(result.estimatedExposureEur).toBeNull();
  });

  it('isApproximate est true en V1', () => {
    const result = makePurchaseSignals();
    expect(result.isApproximate).toBe(true);
  });

  it('retourne EMPTY pour null/undefined/invalide', () => {
    expect(normalizePurchaseSignals(null)).toBe(EMPTY_PURCHASE_SIGNALS);
    expect(normalizePurchaseSignals(undefined)).toBe(EMPTY_PURCHASE_SIGNALS);
    expect(normalizePurchaseSignals('string')).toBe(EMPTY_PURCHASE_SIGNALS);
    expect(normalizePurchaseSignals({})).toBe(EMPTY_PURCHASE_SIGNALS);
  });

  it('retourne EMPTY quand tout vide', () => {
    const result = normalizePurchaseSignals({
      renewals: { total: 0, renewals: [] },
      contracts: { total: 0, contracts: [] },
      totalSites: 0,
    });
    expect(result).toBe(EMPTY_PURCHASE_SIGNALS);
  });

  it('filtre les renewals invalides (sans site_id ou days_until_expiry)', () => {
    const result = normalizePurchaseSignals({
      renewals: {
        total: 3,
        renewals: [
          { contract_id: 1, site_id: 1, days_until_expiry: 30, supplier_name: 'EDF' },
          { contract_id: 2, site_id: null, days_until_expiry: 30 },
          { missing_fields: true },
        ],
      },
      contracts: { total: 1, contracts: [{ id: 1, site_id: 1 }] },
      totalSites: 1,
    });
    expect(result.renewals).toHaveLength(1);
  });

  it('isPurchaseAvailable detecte la presence', () => {
    expect(isPurchaseAvailable(null)).toBe(false);
    expect(isPurchaseAvailable(undefined)).toBe(false);
    expect(isPurchaseAvailable(EMPTY_PURCHASE_SIGNALS)).toBe(false);
    expect(isPurchaseAvailable(makePurchaseSignals())).toBe(true);
  });

  it('EMPTY_PURCHASE_SIGNALS est freeze', () => {
    expect(Object.isFrozen(EMPTY_PURCHASE_SIGNALS)).toBe(true);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2) Lever Engine V36 — achat levers
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever Engine V36 — achat levers', () => {
  it('genere lev-achat-renew quand expiringSoonCount > 0', () => {
    const ps = makePurchaseSignals();
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    const renew = result.topLevers.find((l) => l.actionKey === 'lev-achat-renew');
    expect(renew).toBeTruthy();
    expect(renew.type).toBe('achat');
    expect(renew.label).toContain('contrat');
    expect(renew.label).toContain('énergie');
    expect(renew.ctaPath).toContain('/achat-energie');
  });

  it('genere lev-achat-data quand missingContractsCount > 0', () => {
    const ps = makePurchaseSignals();
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    const data = result.topLevers.find((l) => l.actionKey === 'lev-achat-data');
    expect(data).toBeTruthy();
    expect(data.type).toBe('achat');
    expect(data.label).toContain('sans contrat');
    expect(data.ctaPath).toContain('/achat-energie');
  });

  it('leversByType.achat reflete le compte', () => {
    const ps = makePurchaseSignals();
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    expect(result.leversByType.achat).toBe(2);
  });

  it('impactEur est null pour les levers achat V1', () => {
    const ps = makePurchaseSignals();
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    const achatLevers = result.topLevers.filter((l) => l.type === 'achat');
    achatLevers.forEach((l) => expect(l.impactEur).toBeNull());
  });

  it("pas de levers achat quand tout couvert et pas d'echeances", () => {
    const ps = normalizePurchaseSignals({
      renewals: { total: 0, renewals: [] },
      contracts: makeContractsResponse(10),
      totalSites: 10,
    });
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    expect(result.leversByType.achat).toBe(0);
  });

  it('uniquement lev-achat-renew quand couverture complete mais echeances', () => {
    const renewals = makeRenewalsResponse(2);
    const contracts = makeContractsResponse(10);
    const ps = normalizePurchaseSignals({ renewals, contracts, totalSites: 10 });

    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: {},
      purchaseSignals: ps,
    });

    expect(result.topLevers.find((l) => l.actionKey === 'lev-achat-renew')).toBeTruthy();
    expect(result.topLevers.find((l) => l.actionKey === 'lev-achat-data')).toBeFalsy();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3) Lever Engine V36 — fallback sans purchaseSignals
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever Engine V36 — fallback sans purchaseSignals', () => {
  it('fonctionne identiquement a V35 sans purchaseSignals', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
    });

    expect(result.leversByType.achat).toBe(0);
    expect(result.leversByType.conformite).toBe(2);
    expect(result.leversByType.facturation).toBe(1);
    expect(result.leversByType.optimisation).toBe(1);
    expect(result.totalLevers).toBe(4);
  });

  it('pas de crash avec purchaseSignals null', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: null,
    });
    expect(result.leversByType.achat).toBe(0);
    expect(result.totalLevers).toBe(4);
  });

  it('pas de crash avec purchaseSignals EMPTY', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: EMPTY_PURCHASE_SIGNALS,
    });
    expect(result.leversByType.achat).toBe(0);
    expect(result.totalLevers).toBe(4);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4) LeverActionModel — achat templates
// ══════════════════════════════════════════════════════════════════════════════

describe('LeverActionModel V36 — achat templates', () => {
  it('contient le template lev-achat-renew', () => {
    const tpl = LEVER_ACTION_TEMPLATES['lev-achat-renew'];
    expect(tpl).toBeTruthy();
    expect(tpl.source_type).toBe('lever_engine');
    expect(tpl.severity).toBe('high');
    expect(tpl.due_days).toBe(30);
    expect(tpl.priority).toBe(1);
    expect(tpl.rationale.length).toBeGreaterThanOrEqual(2);
    expect(tpl.proof_expected).toBeTruthy();
    expect(tpl.proof_owner).toBeTruthy();
  });

  it('contient le template lev-achat-data', () => {
    const tpl = LEVER_ACTION_TEMPLATES['lev-achat-data'];
    expect(tpl).toBeTruthy();
    expect(tpl.source_type).toBe('lever_engine');
    expect(tpl.severity).toBe('medium');
    expect(tpl.due_days).toBe(60);
    expect(tpl.priority).toBe(2);
    expect(tpl.rationale.length).toBeGreaterThanOrEqual(2);
  });

  it('buildActionPayload fonctionne pour lev-achat-renew', () => {
    const lever = {
      type: 'achat',
      actionKey: 'lev-achat-renew',
      label: "Renouveler 2 contrats d'energie (2 sites)",
      impactEur: null,
      ctaPath: '/achat-energie?filter=renewal',
    };
    const payload = buildActionPayload(lever);
    expect(payload).not.toBeNull();
    expect(payload.source_id).toBe('lev-achat-renew');
    expect(payload.severity).toBe('high');
    expect(payload.estimated_gain_eur).toBeNull();
    expect(payload.idempotency_key).toBe('lever-lev-achat-renew');
  });

  it('buildActionPayload fonctionne pour lev-achat-data', () => {
    const lever = {
      type: 'achat',
      actionKey: 'lev-achat-data',
      label: 'Completer 5 sites sans contrat energie',
      impactEur: null,
      ctaPath: '/achat-energie?filter=missing',
    };
    const payload = buildActionPayload(lever);
    expect(payload).not.toBeNull();
    expect(payload.source_id).toBe('lev-achat-data');
    expect(payload.severity).toBe('medium');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5) ImpactDecisionPanel — DÉCOMMISSIONNÉ Phase 0.3 sprint Cockpit dual sol2
//
// Le contrat V36 (purchase signals + section "Achats d'énergie" + drill-downs
// /achat-energie + computeActionableLevers) sera vérifié sur le futur
// <DecisionsTopThree> (3 décisions arbitrales narrées) + son point d'entrée
// "Quelle stratégie de renouvellement post-ARENH ?" en Phase 2.3
// (cf docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html
// section #decision-renouvellement-paris).
// ══════════════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════════════
// 6) Guard: modules purs (no React, no API)
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: V36 purchaseSignalsContract est un module pur', () => {
  const purchaseSrc = readFileSync(
    resolve(__dirname, '..', '..', 'models', 'purchaseSignalsContract.js'),
    'utf8'
  );

  it("n'importe pas React", () => {
    expect(purchaseSrc).not.toContain("from 'react'");
  });

  it("n'importe pas d'API", () => {
    expect(purchaseSrc).not.toContain('services/api');
  });

  it('exporte normalizePurchaseSignals et isPurchaseAvailable', () => {
    expect(purchaseSrc).toContain('export function normalizePurchaseSignals');
    expect(purchaseSrc).toContain('export function isPurchaseAvailable');
    expect(purchaseSrc).toContain('export const EMPTY_PURCHASE_SIGNALS');
  });

  it('leverEngineModel importe purchaseSignalsContract', () => {
    const engineSrc = readSrc('models/leverEngineModel.js');
    expect(engineSrc).toContain('purchaseSignalsContract');
  });

  it('leverEngineModel importe toujours les 2 contracts V35', () => {
    const engineSrc = readSrc('models/leverEngineModel.js');
    expect(engineSrc).toContain('complianceSignalsContract');
    expect(engineSrc).toContain('billingInsightsContract');
  });

  // Phase 1.4.b (29/04/2026) : impactDecisionModel.js migré vers
  // backend/services/impact_decision_service.py (CLAUDE.md règle d'or
  // zero business logic frontend). Source-guard équivalent désormais
  // côté pytest dans backend/tests/test_impact_decision_service.py.
  // Test JS supprimé pour éviter référence à un fichier disparu.
});
