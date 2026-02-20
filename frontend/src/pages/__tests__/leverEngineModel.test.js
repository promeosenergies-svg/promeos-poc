/**
 * PROMEOS — Levier Engine V1 tests
 *
 * 1) Compliance only → levers conformite
 * 2) Billing only → levers facturation
 * 3) Mix (compliance + billing + optimisation) → tous types
 * 4) Empty → totalLevers = 0
 * 5) Tri topLevers par impactEur desc
 * 6) Guard: pas d'import React ni API
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import { computeActionableLevers } from '../../models/leverEngineModel';

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeKpis(overrides = {}) {
  return {
    total: 10,
    conformes: 7,
    nonConformes: 2,
    aRisque: 1,
    risqueTotal: 30000,
    ...overrides,
  };
}

function makeBilling(overrides = {}) {
  return {
    total_invoices: 50,
    total_eur: 500000,
    total_loss_eur: 8000,
    invoices_with_anomalies: 5,
    ...overrides,
  };
}

// ══════════════════════════════════════════════════════════════════════════════
// TEST 1: Compliance only
// ══════════════════════════════════════════════════════════════════════════════

describe('computeActionableLevers — compliance only', () => {
  it('genere des leviers conformite quand nonConformes + aRisque > 0', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: {},
    });

    expect(result.leversByType.conformite).toBe(2); // nonConformes + aRisque
    expect(result.leversByType.facturation).toBe(0);
    expect(result.leversByType.optimisation).toBe(0);
    // V37: data_activation lever fires (2/5 briques actives < threshold 3)
    expect(result.leversByType.data_activation).toBe(1);
    expect(result.totalLevers).toBe(3);
  });

  it('repartit le risqueTotal au prorata nonConformes / aRisque', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 2, aRisque: 1, risqueTotal: 30000 }),
      billingSummary: {},
    });

    const conformLevers = result.topLevers.filter((l) => l.type === 'conformite');
    // 2/(2+1) * 30000 = 20000, 1/(2+1) * 30000 = 10000
    expect(conformLevers.find((l) => l.label.includes('non conforme')).impactEur).toBe(20000);
    expect(conformLevers.find((l) => l.label.includes('risque')).impactEur).toBe(10000);
  });

  it('impactEur null si risqueTotal = 0', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ risqueTotal: 0 }),
      billingSummary: {},
    });

    result.topLevers
      .filter((l) => l.type === 'conformite')
      .forEach((l) => expect(l.impactEur).toBeNull());
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 2: Billing only
// ══════════════════════════════════════════════════════════════════════════════

describe('computeActionableLevers — billing only', () => {
  it('genere un levier facturation quand anomalies > 0', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: makeBilling(),
    });

    expect(result.leversByType.facturation).toBe(1);
    expect(result.topLevers.find((l) => l.type === 'facturation').impactEur).toBe(8000);
  });

  it('genere un levier facturation via total_loss_eur meme sans anomalies count', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: { total_loss_eur: 5000, total_eur: 0 },
    });

    expect(result.leversByType.facturation).toBe(1);
    expect(result.topLevers.find((l) => l.type === 'facturation').label).toContain('surcout');
  });

  it('genere un levier optimisation quand total_eur > 0', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }),
      billingSummary: { total_eur: 200000 },
    });

    expect(result.leversByType.optimisation).toBe(1);
    expect(result.topLevers.find((l) => l.type === 'optimisation').impactEur).toBe(2000);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 3: Mix — all three types
// ══════════════════════════════════════════════════════════════════════════════

describe('computeActionableLevers — mix', () => {
  it('genere conformite + facturation + optimisation ensemble', () => {
    const result = computeActionableLevers({
      kpis: makeKpis(),
      billingSummary: makeBilling(),
    });

    expect(result.leversByType.conformite).toBe(2);
    expect(result.leversByType.facturation).toBe(1);
    expect(result.leversByType.optimisation).toBe(1);
    expect(result.totalLevers).toBe(4);
  });

  it('estimatedImpactEur = risqueTotal + totalLoss', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ risqueTotal: 30000 }),
      billingSummary: makeBilling({ total_loss_eur: 8000 }),
    });

    expect(result.estimatedImpactEur).toBe(38000);
  });

  it('topLevers tries par impactEur desc (null en dernier)', () => {
    const result = computeActionableLevers({
      kpis: makeKpis({ nonConformes: 2, aRisque: 1, risqueTotal: 30000 }),
      billingSummary: makeBilling({ total_loss_eur: 8000, total_eur: 500000 }),
    });

    const impacts = result.topLevers.map((l) => l.impactEur);
    for (let i = 0; i < impacts.length - 1; i++) {
      // null treated as -1, so non-null always before null
      expect((impacts[i] ?? -1) >= (impacts[i + 1] ?? -1)).toBe(true);
    }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 4: Empty — aucune donnee
// ══════════════════════════════════════════════════════════════════════════════

describe('computeActionableLevers — empty', () => {
  it('retourne 0 leviers quand tout est vide', () => {
    const result = computeActionableLevers({ kpis: {}, billingSummary: {} });

    expect(result.totalLevers).toBe(0);
    expect(result.leversByType.conformite).toBe(0);
    expect(result.leversByType.facturation).toBe(0);
    expect(result.leversByType.optimisation).toBe(0);
    expect(result.estimatedImpactEur).toBe(0);
    expect(result.topLevers).toEqual([]);
  });

  it('retourne 0 leviers avec input undefined', () => {
    const result = computeActionableLevers();

    expect(result.totalLevers).toBe(0);
    expect(result.topLevers).toEqual([]);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// GUARD: leverEngineModel est un module pur
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: leverEngineModel est un module pur', () => {
  const src = readFileSync(
    resolve(__dirname, '..', '..', 'models', 'leverEngineModel.js'),
    'utf8',
  );

  it('n\'importe pas React', () => {
    expect(src).not.toContain("from 'react'");
  });

  it('n\'importe aucun service API', () => {
    expect(src).not.toContain('services/api');
    expect(src).not.toContain('fetch(');
    expect(src).not.toContain('axios');
  });

  it('exporte computeActionableLevers', () => {
    expect(src).toContain('export function computeActionableLevers');
  });

  it('ne modifie pas impactDecisionModel (V30 intact)', () => {
    expect(src).not.toContain('computeImpactKpis');
    expect(src).not.toContain('computeRecommendation');
  });
});
