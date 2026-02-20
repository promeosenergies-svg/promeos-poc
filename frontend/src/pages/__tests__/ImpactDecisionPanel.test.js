/**
 * PROMEOS — ImpactDecisionPanel tests
 *
 * 1) computeImpactKpis: 3 KPIs labels FR + valeurs correctes
 * 2) computeRecommendation: 3 cas (conformité > facture > optimisation)
 * 3) Guard: le panneau utilise uniquement des données scopées (pas d'appel direct non scopé)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  computeImpactKpis,
  computeRecommendation,
} from '../../models/impactDecisionModel';

const readSrc = (relPath) =>
  readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeKpis(overrides = {}) {
  return {
    total: 10,
    conformes: 7,
    nonConformes: 2,
    aRisque: 1,
    risqueTotal: 25000,
    couvertureDonnees: 70,
    ...overrides,
  };
}

function makeBilling(overrides = {}) {
  return {
    total_invoices: 50,
    total_eur: 500000,
    total_loss_eur: 8000,
    ...overrides,
  };
}

// ══════════════════════════════════════════════════════════════════════════════
// TEST 1: computeImpactKpis — 3 KPIs avec valeurs correctes
// ══════════════════════════════════════════════════════════════════════════════

describe('computeImpactKpis', () => {
  it('calcule les 3 KPIs à partir de kpis + billingSummary', () => {
    const impact = computeImpactKpis(makeKpis(), makeBilling());

    // Risque conformité = kpis.risqueTotal
    expect(impact.risqueConformite).toBe(25000);
    expect(impact.risqueAvailable).toBe(true);

    // Surcoût facture = total_loss_eur clampé >= 0
    expect(impact.surcoutFacture).toBe(8000);
    expect(impact.surcoutAvailable).toBe(true);

    // Opportunité = 1% de total_eur
    expect(impact.opportuniteOptim).toBe(5000); // 500000 * 0.01
    expect(impact.optimAvailable).toBe(true);
  });

  it('retourne 0 avec données manquantes flaggées', () => {
    const impact = computeImpactKpis({}, {});

    expect(impact.risqueConformite).toBe(0);
    expect(impact.risqueAvailable).toBe(false);

    expect(impact.surcoutFacture).toBe(0);
    expect(impact.surcoutAvailable).toBe(false);

    expect(impact.opportuniteOptim).toBe(0);
    expect(impact.optimAvailable).toBe(false);
  });

  it('clampe le surcoût facture à >= 0', () => {
    const impact = computeImpactKpis(makeKpis(), { total_loss_eur: -500, total_invoices: 10 });
    expect(impact.surcoutFacture).toBe(0);
  });

  it('arrondit l\'opportunité à l\'entier', () => {
    const impact = computeImpactKpis(makeKpis(), { total_eur: 123456 });
    expect(impact.opportuniteOptim).toBe(1235); // Math.round(123456 * 0.01)
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 2: computeRecommendation — 3 cas selon max KPI
// ══════════════════════════════════════════════════════════════════════════════

describe('computeRecommendation', () => {
  it('recommande conformité quand risqueConformite est max', () => {
    const impact = { risqueConformite: 50000, surcoutFacture: 8000, opportuniteOptim: 5000 };
    const kpis = makeKpis({ nonConformes: 3, aRisque: 2 });
    const reco = computeRecommendation(impact, kpis);

    expect(reco.key).toBe('conformite');
    expect(reco.titre).toContain('conformité');
    expect(reco.ctaPath).toBe('/conformite');
    expect(reco.bullets).toHaveLength(3);
    expect(reco.bullets[0]).toContain('5 sites');
  });

  it('recommande facture quand surcoutFacture est max', () => {
    const impact = { risqueConformite: 5000, surcoutFacture: 20000, opportuniteOptim: 3000 };
    const reco = computeRecommendation(impact, makeKpis());

    expect(reco.key).toBe('facture');
    expect(reco.titre).toContain('anomalies facture');
    expect(reco.ctaPath).toBe('/bill-intel');
    expect(reco.bullets).toHaveLength(3);
  });

  it('recommande optimisation quand opportuniteOptim est max', () => {
    const impact = { risqueConformite: 1000, surcoutFacture: 2000, opportuniteOptim: 15000 };
    const reco = computeRecommendation(impact, makeKpis());

    expect(reco.key).toBe('optimisation');
    expect(reco.titre).toContain('optimisation');
    expect(reco.ctaPath).toBe('/diagnostic-conso');
    expect(reco.bullets).toHaveLength(3);
    expect(reco.bullets[1]).toContain('1 %'); // mentionne l'heuristique V1
  });

  it('retourne no_data quand tout est à 0', () => {
    const impact = { risqueConformite: 0, surcoutFacture: 0, opportuniteOptim: 0 };
    const reco = computeRecommendation(impact, makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 }));

    expect(reco.key).toBe('no_data');
    expect(reco.ctaPath).toBe('/patrimoine');
    expect(reco.bullets).toHaveLength(3);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// GUARD: ImpactDecisionPanel utilise uniquement des données scopées
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: Impact panel uses scoped data only', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');
  const modelSrc = readSrc('models/impactDecisionModel.js');

  it('panel reçoit kpis en prop (pas de fetch direct de sites)', () => {
    // Le composant prend kpis en prop — il ne fait pas de useScope() direct pour les sites
    expect(panelSrc).toMatch(/export\s+default\s+function\s+ImpactDecisionPanel\(\s*\{\s*kpis\s*\}/);
  });

  it('panel appelle uniquement getBillingSummary (API scopée via X-Org-Id interceptor)', () => {
    // Seule API appelée: getBillingSummary — qui est scopée via l'intercepteur api.js
    expect(panelSrc).toContain('getBillingSummary');
    // Pas d'appel API direct non scopé
    expect(panelSrc).not.toContain('fetch(');
    expect(panelSrc).not.toContain('axios.get(');
  });

  it('le modèle pur n\'importe pas React ni de service API', () => {
    expect(modelSrc).not.toContain("from 'react'");
    expect(modelSrc).not.toContain('import.*api');
    expect(modelSrc).not.toContain('fetch(');
  });
});
