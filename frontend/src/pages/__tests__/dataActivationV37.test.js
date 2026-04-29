/**
 * PROMEOS — V37 Data Activation tests
 *
 * 1) dataActivationModel: buildActivationChecklist
 * 2) dataActivationModel: computeActivatedCount
 * 3) Lever Engine V37: data_activation lever
 * 4) LeverActionModel: data_activation template
 * 5) DataActivationPanel: guards source
 * 6) ActivationPage + App: guards
 * 7) Guard: modules purs
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  ACTIVATION_DIMENSIONS,
  ACTIVATION_THRESHOLD,
  buildActivationChecklist,
  computeActivatedCount,
} from '../../models/dataActivationModel';

import {
  LEVER_ACTION_TEMPLATES,
  buildActionPayload,
  buildLeverDeepLink,
} from '../../models/leverActionModel';

// ── Helpers ─────────────────────────────────────────────────────────────────

const readSrc = (relPath) => readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

// ── Fixtures ────────────────────────────────────────────────────────────────

const makeKpis = (ov = {}) => ({
  total: 10,
  conformes: 7,
  nonConformes: 2,
  aRisque: 1,
  risqueTotal: 30000,
  couvertureDonnees: 80,
  ...ov,
});

const makeBilling = (ov = {}) => ({
  total_invoices: 50,
  total_eur: 500000,
  total_loss_eur: 8000,
  invoices_with_anomalies: 5,
  ...ov,
});

const makePurchaseSignals = (ov = {}) => ({
  renewals: [],
  totalContracts: 8,
  totalSites: 10,
  expiringSoonCount: 2,
  expiringSoonSites: [1, 2],
  coverageContractsPct: 80,
  missingContractsCount: 2,
  estimatedExposureEur: null,
  isApproximate: true,
  ...ov,
});

// ═══════════════════════════════════════════════════════════════════════════
// 1) buildActivationChecklist
// ═══════════════════════════════════════════════════════════════════════════

describe('dataActivationModel — buildActivationChecklist', () => {
  it("retourne 5 dimensions dans l'ordre", () => {
    const result = buildActivationChecklist({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    expect(result.dimensions).toHaveLength(5);
    expect(result.dimensions.map((d) => d.key)).toEqual(ACTIVATION_DIMENSIONS);
  });

  it('activatedCount = 5 quand tout est fourni', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    expect(result.activatedCount).toBe(5);
    expect(result.totalDimensions).toBe(5);
  });

  it('activatedCount = 0 quand input vide', () => {
    const result = buildActivationChecklist({});
    expect(result.activatedCount).toBe(0);
    expect(result.totalDimensions).toBe(5);
  });

  it('overallCoverage calcule correctement', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    // patrimoine=100, conformite=100 (10/10), consommation=80, facturation=100, achat=80
    // (100 + 100 + 80 + 100 + 80) / 5 = 92
    expect(result.overallCoverage).toBe(92);
  });

  it('nextAction = premiere dimension manquante', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis({ couvertureDonnees: 0 }),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    expect(result.nextAction).not.toBeNull();
    expect(result.nextAction.key).toBe('consommation');
    expect(result.nextAction.ctaPath).toBe('/consommations/import');
  });

  it('nextAction = null quand tout est actif', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    expect(result.nextAction).toBeNull();
  });

  it('coverage patrimoine = 100 si total > 0', () => {
    const result = buildActivationChecklist({ kpis: makeKpis() });
    const dim = result.dimensions.find((d) => d.key === 'patrimoine');
    expect(dim.available).toBe(true);
    expect(dim.coverage).toBe(100);
  });

  it('coverage conformite proportionnelle', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis({ total: 10, conformes: 3, nonConformes: 2, aRisque: 1 }),
    });
    const dim = result.dimensions.find((d) => d.key === 'conformite');
    expect(dim.available).toBe(true);
    // (3+2+1)/10 * 100 = 60
    expect(dim.coverage).toBe(60);
  });

  it('coverage consommation = couvertureDonnees', () => {
    const result = buildActivationChecklist({ kpis: makeKpis({ couvertureDonnees: 45 }) });
    const dim = result.dimensions.find((d) => d.key === 'consommation');
    expect(dim.available).toBe(true);
    expect(dim.coverage).toBe(45);
  });

  it('coverage achat = coverageContractsPct', () => {
    const result = buildActivationChecklist({
      kpis: makeKpis(),
      purchaseSignals: makePurchaseSignals({ coverageContractsPct: 60 }),
    });
    const dim = result.dimensions.find((d) => d.key === 'achat');
    expect(dim.available).toBe(true);
    expect(dim.coverage).toBe(60);
  });

  it('ACTIVATION_THRESHOLD = 3', () => {
    expect(ACTIVATION_THRESHOLD).toBe(3);
  });

  it('chaque dimension a label, ctaPath, ctaLabel', () => {
    const result = buildActivationChecklist({ kpis: makeKpis() });
    for (const dim of result.dimensions) {
      expect(dim.label).toBeTruthy();
      expect(dim.ctaPath).toBeTruthy();
      expect(dim.ctaLabel).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2) computeActivatedCount
// ═══════════════════════════════════════════════════════════════════════════

describe('dataActivationModel — computeActivatedCount', () => {
  it('5 quand tout fourni', () => {
    expect(
      computeActivatedCount({
        kpis: makeKpis(),
        billingSummary: makeBilling(),
        purchaseSignals: makePurchaseSignals(),
      })
    ).toBe(5);
  });

  it('0 quand rien', () => {
    expect(computeActivatedCount({})).toBe(0);
    expect(computeActivatedCount()).toBe(0);
  });

  it('4 quand couvertureDonnees manquant', () => {
    expect(
      computeActivatedCount({
        kpis: makeKpis({ couvertureDonnees: 0 }),
        billingSummary: makeBilling(),
        purchaseSignals: makePurchaseSignals(),
      })
    ).toBe(4);
  });

  it('3 quand billing + purchase manquants', () => {
    expect(
      computeActivatedCount({
        kpis: makeKpis(),
        billingSummary: {},
        purchaseSignals: null,
      })
    ).toBe(3);
  });

  it('pas de crash avec null/undefined', () => {
    expect(() => computeActivatedCount(null)).not.toThrow();
    expect(() => computeActivatedCount(undefined)).not.toThrow();
    expect(computeActivatedCount(null)).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// NOTE Phase 1.4.c (29/04/2026) : section "Lever Engine V37 — data_activation
// lever" supprimée — la logique est désormais dans
// backend/services/lever_engine_service.py.
// Couverture dans backend/tests/test_lever_engine_service.py
// (classe TestV37DataActivation).
// ═══════════════════════════════════════════════════════════════════════════
// 4) LeverActionModel — data_activation template
// ═══════════════════════════════════════════════════════════════════════════

describe('LeverActionModel — data_activation template', () => {
  it('template lev-data-cover existe avec severity low', () => {
    const tpl = LEVER_ACTION_TEMPLATES['lev-data-cover'];
    expect(tpl).toBeDefined();
    expect(tpl.severity).toBe('low');
    expect(tpl.due_days).toBe(60);
    expect(tpl.priority).toBe(3);
  });

  it('buildActionPayload fonctionne pour lev-data-cover', () => {
    const lever = {
      type: 'data_activation',
      actionKey: 'lev-data-cover',
      label: 'Completer 3 briques de donnees manquantes',
      impactEur: null,
      ctaPath: '/activation',
    };
    const payload = buildActionPayload(lever);
    expect(payload).not.toBeNull();
    expect(payload.source_id).toBe('lev-data-cover');
    expect(payload.severity).toBe('low');
    expect(payload.estimated_gain_eur).toBeNull();
    expect(payload.idempotency_key).toBe('lever-lev-data-cover');
  });

  it('buildLeverDeepLink retourne URL avec type=data_activation', () => {
    const lever = { type: 'data_activation', actionKey: 'lev-data-cover', impactEur: null };
    const link = buildLeverDeepLink(lever);
    expect(link).toContain('type=data_activation');
    expect(link).toContain('ref_id=lev-data-cover');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5) DataActivationPanel — guards source
// ═══════════════════════════════════════════════════════════════════════════

describe('DataActivationPanel — V37 guards', () => {
  const src = readSrc('pages/cockpit/DataActivationPanel.jsx');

  it('importe Database de lucide-react', () => {
    expect(src).toContain('Database');
    expect(src).toContain('lucide-react');
  });

  it('importe buildActivationChecklist', () => {
    expect(src).toContain('buildActivationChecklist');
    expect(src).toContain('dataActivationModel');
  });

  it('receives activationData as prop (I4: hoisted to Cockpit.jsx)', () => {
    expect(src).toContain('activationData');
    expect(src).toContain('billingSummary');
    expect(src).toContain('purchaseSignals');
    expect(src).toContain('loading');
  });

  it('data-testid="data-activation-panel"', () => {
    expect(src).toContain('data-testid="data-activation-panel"');
  });

  it('aria-label FR sur lien detail', () => {
    expect(src).toContain('Voir le d');
    expect(src).toContain('activation des donn');
  });

  it('affiche couverture dynamique (briques + couverture moyenne)', () => {
    expect(src).toContain('briques');
    expect(src).toContain('couverture moyenne');
  });

  it('lien vers /activation', () => {
    expect(src).toContain('/activation');
  });

  it('activation data received via prop (I4: hoisted to Cockpit.jsx)', () => {
    expect(src).toContain('activationData');
  });

  it('affiche activatedCount/totalDimensions', () => {
    expect(src).toContain('activation.activatedCount');
    expect(src).toContain('activation.totalDimensions');
  });

  it('etat succes "Toutes les briques sont actives"', () => {
    expect(src).toContain('Toutes les briques sont actives');
  });

  it('CTA Completer avec ArrowRight', () => {
    expect(src).toContain('Compl');
    expect(src).toContain('ter');
    expect(src).toContain('ArrowRight');
  });

  it('Progress import et usage', () => {
    expect(src).toContain('Progress');
    expect(src).toContain('overallCoverage');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6) ActivationPage + App — guards
// ═══════════════════════════════════════════════════════════════════════════

describe('ActivationPage + App — V37 guards', () => {
  const appSrc = readSrc('App.jsx');
  const pageSrc = readSrc('pages/ActivationPage.jsx');

  it('App.jsx importe ActivationPage', () => {
    expect(appSrc).toContain('ActivationPage');
    expect(appSrc).toContain("import('./pages/ActivationPage')");
  });

  it('route /activation presente', () => {
    expect(appSrc).toContain('path="/activation"');
  });

  it('alias /donnees vers /activation', () => {
    const redirectsSrc = readFileSync(
      resolve(__dirname, '..', '..', 'routes', 'legacyRedirects.js'),
      'utf8'
    );
    expect(redirectsSrc).toMatch(/\['\/donnees',\s*'\/activation'\]/);
  });

  it('ActivationPage importe buildActivationChecklist', () => {
    expect(pageSrc).toContain('buildActivationChecklist');
  });

  it('ActivationPage importe ACTIVATION_DIMENSIONS', () => {
    expect(pageSrc).toContain('ACTIVATION_DIMENSIONS');
  });

  it('ActivationPage importe useScope', () => {
    expect(pageSrc).toContain('useScope');
  });

  it('ActivationPage a PageShell avec icon Database', () => {
    expect(pageSrc).toContain('PageShell');
    expect(pageSrc).toContain('Database');
  });

  it('ActivationPage supporte filtre dim via URL', () => {
    expect(pageSrc).toContain("sp.get('dim')");
  });

  it('ActivationPage a table par site avec 5 colonnes dimension', () => {
    expect(pageSrc).toContain('Patrimoine');
    expect(pageSrc).toContain('Conformit');
    expect(pageSrc).toContain('Conso');
    expect(pageSrc).toContain('Facture');
    expect(pageSrc).toContain('Contrat');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7) Guard: modules purs
// ═══════════════════════════════════════════════════════════════════════════

describe('Guard: modules purs V37', () => {
  it('dataActivationModel: pas React, pas API', () => {
    const src = readSrc('models/dataActivationModel.js');
    expect(src).not.toContain("from 'react'");
    expect(src).not.toContain('services/api');
  });

  it('dataActivationModel importe isPurchaseAvailable', () => {
    const src = readSrc('models/dataActivationModel.js');
    expect(src).toContain('isPurchaseAvailable');
    expect(src).toContain('purchaseSignalsContract');
  });

  // Phase 1.4.b (29/04/2026) : impactDecisionModel.js migré vers
  // backend/services/impact_decision_service.py. Source-guard équivalent
  // désormais côté pytest. Test JS supprimé.

  // Phase 1.4.c (29/04/2026) : leverEngineModel.js migré vers
  // backend/services/lever_engine_service.py. Guards leverEngineModel supprimés.
  // Couverture dans backend/tests/test_lever_engine_service.py.

  it('Cockpit.jsx importe SanteKpiGrid (V1+ remplace DataActivationPanel)', () => {
    const src = readSrc('pages/Cockpit.jsx');
    expect(src).toContain('SanteKpiGrid');
  });
});
