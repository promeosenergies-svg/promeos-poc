/**
 * PROMEOS — ImpactDecisionPanel tests
 *
 * 1) computeImpactKpis: 3 KPIs labels FR + valeurs correctes
 * 2) computeRecommendation: 3 cas (conformité > facture > optimisation)
 * 3) Guard: le panneau utilise uniquement des données scopées (pas d'appel direct non scopé)
 * 4) Drill-down: 3 KPIs cliquables → navigation vers pages cibles
 * 5) V32 — KPI dominant: mise en avant visuelle du max
 * 6) V32 — Compteurs contextuels: sub-labels sous chaque KPI
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import { computeImpactKpis, computeRecommendation } from '../../models/impactDecisionModel';

const readSrc = (relPath) => readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

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

  it("arrondit l'opportunité à l'entier", () => {
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
    const reco = computeRecommendation(
      impact,
      makeKpis({ nonConformes: 0, aRisque: 0, risqueTotal: 0 })
    );

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
    expect(panelSrc).toMatch(
      /export\s+default\s+function\s+ImpactDecisionPanel\(\s*\{\s*kpis\s*\}/
    );
  });

  it('panel appelle uniquement getBillingSummary (API scopée via X-Org-Id interceptor)', () => {
    // Seule API appelée: getBillingSummary — qui est scopée via l'intercepteur api.js
    expect(panelSrc).toContain('getBillingSummary');
    // Pas d'appel API direct non scopé
    expect(panelSrc).not.toContain('fetch(');
    expect(panelSrc).not.toContain('axios.get(');
  });

  it("le modèle pur n'importe pas React ni de service API", () => {
    expect(modelSrc).not.toContain("from 'react'");
    expect(modelSrc).not.toContain('import.*api');
    expect(modelSrc).not.toContain('fetch(');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 4: Drill-down — 3 KPIs cliquables avec navigation correcte
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: Drill-down KPI navigation', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');

  it('contient la fonction handleDrillDown', () => {
    expect(panelSrc).toContain('handleDrillDown');
  });

  it('navigue vers /patrimoine?filter=risque pour le KPI risque', () => {
    expect(panelSrc).toContain('/patrimoine?filter=risque');
  });

  it('navigue vers /bill-intel?filter=anomalies pour le KPI surcoût', () => {
    expect(panelSrc).toContain('/bill-intel?filter=anomalies');
  });

  it('navigue vers /consommations?filter=energivores pour le KPI optimisation', () => {
    expect(panelSrc).toContain('/consommations?filter=energivores');
  });

  it('chaque KPI tile reçoit un onClick', () => {
    const onClickCount = (panelSrc.match(/onClick=\{.*handleDrillDown/g) || []).length;
    expect(onClickCount).toBe(3);
  });

  it("chaque KPI tile a un aria-label pour l'accessibilité", () => {
    const ariaCount = (panelSrc.match(/ariaLabel="/g) || []).length;
    expect(ariaCount).toBeGreaterThanOrEqual(3);
  });

  it('les tiles utilisent cursor-pointer au hover', () => {
    expect(panelSrc).toContain('cursor-pointer');
    expect(panelSrc).toContain('hover:');
  });

  it('les tiles sont rendues en <button> quand cliquables', () => {
    expect(panelSrc).toContain("const Tag = onClick ? 'button' : 'div'");
  });

  it("la logique V30 (computeImpactKpis, computeRecommendation) n'est pas modifiée", () => {
    const modelSrc = readSrc('models/impactDecisionModel.js');
    // Le modèle exporte toujours les 2 fonctions pures
    expect(modelSrc).toContain('export function computeImpactKpis');
    expect(modelSrc).toContain('export function computeRecommendation');
    // Le panel importe bien ces 2 fonctions
    expect(panelSrc).toContain("from '../../models/impactDecisionModel'");
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 5: V32 — KPI dominant (mise en avant visuelle du max)
// ══════════════════════════════════════════════════════════════════════════════

describe('V32: KPI dominant', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');

  it('calcule dominantKey via useMemo (max des 3 montants)', () => {
    expect(panelSrc).toContain('dominantKey');
    expect(panelSrc).toContain('Math.max(risqueConformite, surcoutFacture, opportuniteOptim)');
  });

  it('dominant=null quand max === 0', () => {
    expect(panelSrc).toContain('if (max === 0) return null');
  });

  it('risque est dominant quand risqueConformite >= les deux autres', () => {
    expect(panelSrc).toMatch(
      /risqueConformite >= surcoutFacture.*risqueConformite >= opportuniteOptim.*return 'risque'/s
    );
  });

  it('surcout est dominant quand surcoutFacture >= opportuniteOptim', () => {
    expect(panelSrc).toMatch(/surcoutFacture >= opportuniteOptim.*return 'surcout'/s);
  });

  it('optimisation est dominant par défaut (fallback)', () => {
    expect(panelSrc).toContain("return 'optimisation'");
  });

  it('chaque tile reçoit dominant={dominantKey === ...}', () => {
    expect(panelSrc).toContain("dominant={dominantKey === 'risque'}");
    expect(panelSrc).toContain("dominant={dominantKey === 'surcout'}");
    expect(panelSrc).toContain("dominant={dominantKey === 'optimisation'}");
  });

  it('le tag "Prioritaire" s\'affiche quand dominant', () => {
    expect(panelSrc).toContain('Prioritaire');
    expect(panelSrc).toMatch(/dominant && \(/);
  });

  it('data-dominant est posé sur la tile dominante', () => {
    expect(panelSrc).toContain('data-dominant={dominant || undefined}');
  });

  it('la tile dominante a un style hero (border accent + tintBg + shadow)', () => {
    expect(panelSrc).toContain('a.border');
    expect(panelSrc).toContain('a.tintBg');
    expect(panelSrc).toContain('shadow-sm');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 6: V32 — Compteurs contextuels (sub-labels)
// ══════════════════════════════════════════════════════════════════════════════

describe('V32: Compteurs contextuels', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');

  it('calcule subLabels via useMemo', () => {
    expect(panelSrc).toContain('subLabels');
    expect(panelSrc).toMatch(/const subLabels = useMemo/);
  });

  it('risque: compteur basé sur nonConformes + aRisque', () => {
    expect(panelSrc).toContain('kpis?.nonConformes');
    expect(panelSrc).toContain('kpis?.aRisque');
    expect(panelSrc).toContain('concerné');
  });

  it('risque: pluriel correct (site/sites, concerné/concernés)', () => {
    expect(panelSrc).toMatch(/rs > 1 \? 's' : ''/);
  });

  it('surcout: compteur basé sur invoices_with_anomalies ou total_insights', () => {
    expect(panelSrc).toContain('invoices_with_anomalies');
    expect(panelSrc).toContain('total_insights');
    expect(panelSrc).toContain('impactée');
  });

  it('optimisation: compteur contextuel en V1', () => {
    expect(panelSrc).toMatch(/optimisation:.*impact\.optimAvailable/);
  });

  it('chaque tile reçoit subLabel={subLabels.xxx}', () => {
    expect(panelSrc).toContain('subLabel={subLabels.risque}');
    expect(panelSrc).toContain('subLabel={subLabels.surcout}');
    expect(panelSrc).toContain('subLabel={subLabels.optimisation}');
  });

  it("le subLabel s'affiche uniquement quand available && subLabel", () => {
    expect(panelSrc).toContain('available && subLabel');
  });

  it('uses useActivationData hook instead of direct API calls (V32)', () => {
    expect(panelSrc).toContain('useActivationData');
    // No direct API import — all fetches delegated to shared hook
    const apiCalls = panelSrc.match(/from '\.\.\/\.\.\/services\/api'/g) || [];
    expect(apiCalls).toHaveLength(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 7: V33 — Leviers activables (affichage + CTA navigate)
// ══════════════════════════════════════════════════════════════════════════════

describe('V33: Leviers activables', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');

  it('importe computeActionableLevers depuis leverEngineModel', () => {
    expect(panelSrc).toContain("from '../../models/leverEngineModel'");
    expect(panelSrc).toContain('computeActionableLevers');
  });

  it('appelle computeActionableLevers via useMemo', () => {
    expect(panelSrc).toMatch(/const levers = useMemo/);
    expect(panelSrc).toContain('computeActionableLevers({ kpis, billingSummary');
  });

  it('affiche "X leviers activables" quand totalLevers > 0', () => {
    expect(panelSrc).toContain('levier');
    expect(panelSrc).toContain('activable');
    expect(panelSrc).toContain('levers.totalLevers');
  });

  it('affiche le detail par type (conformite, facturation, optimisation)', () => {
    expect(panelSrc).toContain('levers.leversByType.conformite');
    expect(panelSrc).toContain('levers.leversByType.facturation');
    expect(panelSrc).toContain('levers.leversByType.optimisation');
  });

  it('affiche le separateur bullet entre types', () => {
    // U+2022 bullet separator between type labels
    expect(panelSrc).toContain('\\u2022');
  });

  it('contient un CTA action par levier (V34: deep-link)', () => {
    expect(panelSrc).toContain('buildLeverDeepLink');
    expect(panelSrc).toContain('er une action');
  });

  it('affiche "Aucun levier détecté" quand totalLevers = 0', () => {
    expect(panelSrc).toContain('Aucun levier');
  });

  it('la section leviers a un data-testid', () => {
    expect(panelSrc).toContain('data-testid="levers-section"');
  });

  it('impactDecisionModel.js est intact (V30 non modifie)', () => {
    const modelSrc = readSrc('models/impactDecisionModel.js');
    expect(modelSrc).toContain('export function computeImpactKpis');
    expect(modelSrc).toContain('export function computeRecommendation');
    expect(modelSrc).not.toContain('computeActionableLevers');
  });

  it('no direct API imports — uses shared hook (contrainte V33)', () => {
    expect(panelSrc).toContain('useActivationData');
    const apiImports = panelSrc.match(/from '\.\.\/\.\.\/services\/api'/g) || [];
    expect(apiImports).toHaveLength(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 8: V34 — Lever → Action CTA
// ══════════════════════════════════════════════════════════════════════════════

describe('V34: Lever CTA deep-link', () => {
  const panelSrc = readSrc('pages/cockpit/ImpactDecisionPanel.jsx');

  it('importe buildLeverDeepLink depuis leverActionModel', () => {
    expect(panelSrc).toContain("from '../../models/leverActionModel'");
    expect(panelSrc).toContain('buildLeverDeepLink');
  });

  it('affiche chaque levier individuellement (topLevers.map)', () => {
    expect(panelSrc).toContain('levers.topLevers.map');
  });

  it('utilise lever.actionKey comme key React', () => {
    expect(panelSrc).toContain('key={lever.actionKey}');
  });

  it('affiche le label du levier', () => {
    expect(panelSrc).toContain('lever.label');
  });

  it("affiche l'impact estime en euros si disponible", () => {
    expect(panelSrc).toContain('lever.impactEur');
    expect(panelSrc).toContain("toLocaleString('fr-FR')");
  });

  it('CTA "Creer une action" avec navigate vers deep-link', () => {
    expect(panelSrc).toContain('buildLeverDeepLink(lever)');
    expect(panelSrc).toContain('er une action');
  });

  it('chaque CTA a un aria-label accessible', () => {
    expect(panelSrc).toMatch(/aria-label=.*action pour/);
  });

  it('la liste a un data-testid', () => {
    expect(panelSrc).toContain('data-testid="levers-list"');
  });

  it('le leverEngineModel a des actionKey sur chaque levier', () => {
    const engineSrc = readSrc('models/leverEngineModel.js');
    expect(engineSrc).toContain("actionKey: 'lev-conf-nc'");
    expect(engineSrc).toContain("actionKey: 'lev-conf-ar'");
    expect(engineSrc).toContain("actionKey: 'lev-fact-anom'");
    expect(engineSrc).toContain("actionKey: 'lev-optim-ener'");
  });
});
