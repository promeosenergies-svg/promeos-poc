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

import { computeActionableLevers } from '../../models/leverEngineModel';
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
// 3) Lever Engine V37 — data_activation lever
// ═══════════════════════════════════════════════════════════════════════════

describe('Lever Engine V37 — data_activation lever', () => {
  it('pas de levier quand activatedCount >= 3 (scenario standard V36)', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    const daLevers = result.topLevers.filter((l) => l.type === 'data_activation');
    expect(daLevers).toHaveLength(0);
    expect(result.leversByType.data_activation).toBe(0);
  });

  it('levier quand activatedCount < 3', () => {
    // kpis.total > 0, pas de conformite, pas de conso, pas de billing, pas de purchase → 1 brique (patrimoine)
    const result = computeActionableLevers({
      kpis: {
        total: 5,
        conformes: 0,
        nonConformes: 0,
        aRisque: 0,
        couvertureDonnees: 0,
        risqueTotal: 0,
      },
      billingSummary: {},
    });
    const daLevers = result.topLevers.filter((l) => l.type === 'data_activation');
    expect(daLevers).toHaveLength(1);
    expect(daLevers[0].actionKey).toBe('lev-data-cover');
    expect(daLevers[0].ctaPath).toBe('/activation');
    expect(result.leversByType.data_activation).toBe(1);
  });

  it('leversByType.data_activation = 0 quand pas actif', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
      purchaseSignals: makePurchaseSignals(),
    });
    expect(result.leversByType.data_activation).toBe(0);
  });

  it('pas de levier quand kpis.total === 0', () => {
    const result = computeActionableLevers({
      kpis: { total: 0 },
      billingSummary: {},
    });
    const daLevers = result.topLevers.filter((l) => l.type === 'data_activation');
    expect(daLevers).toHaveLength(0);
  });

  it('label indique le nombre de briques manquantes', () => {
    const result = computeActionableLevers({
      kpis: {
        total: 5,
        conformes: 0,
        nonConformes: 0,
        aRisque: 0,
        couvertureDonnees: 0,
        risqueTotal: 0,
      },
      billingSummary: {},
    });
    const lever = result.topLevers.find((l) => l.type === 'data_activation');
    expect(lever.label).toContain('4');
    expect(lever.label).toContain('briques');
    expect(lever.label).toContain('manquantes');
  });
});

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

  it('uses useActivationData hook (shared fetch)', () => {
    expect(src).toContain('useActivationData');
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

  it('activation data fetched via shared hook', () => {
    expect(src).toContain('useActivationData');
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
    expect(appSrc).toContain('path="/donnees"');
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

  it('leverEngineModel importe computeActivatedCount + ACTIVATION_THRESHOLD', () => {
    const src = readSrc('models/leverEngineModel.js');
    expect(src).toContain('computeActivatedCount');
    expect(src).toContain('ACTIVATION_THRESHOLD');
    expect(src).toContain('dataActivationModel');
  });

  it('leverEngineModel importe toujours V35/V36 contracts', () => {
    const src = readSrc('models/leverEngineModel.js');
    expect(src).toContain('complianceSignalsContract');
    expect(src).toContain('billingInsightsContract');
    expect(src).toContain('purchaseSignalsContract');
  });

  it("impactDecisionModel inchange (pas d'import dataActivation)", () => {
    const src = readSrc('models/impactDecisionModel.js');
    expect(src).not.toContain('dataActivation');
  });

  it('Cockpit.jsx importe DataActivationPanel', () => {
    const src = readSrc('pages/Cockpit.jsx');
    expect(src).toContain('DataActivationPanel');
    expect(src).toContain("'./cockpit/DataActivationPanel'");
  });
});
