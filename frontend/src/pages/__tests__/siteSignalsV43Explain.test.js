/**
 * PROMEOS V43 — Explainable Site Signals: source guards + UI guards
 * Why drawer, filters, lever rationale, 100% FR labels
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. Dashboard — Why drawer source guards
// ══════════════════════════════════════════════════════════════════════════════

describe('Dashboard has V43 Why drawer (source guards)', () => {
  const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('imports Drawer component', () => {
    expect(dash).toContain('Drawer');
  });

  it('has whySite state', () => {
    expect(dash).toContain('whySite');
  });

  it('has "Pourquoi ce classement" title', () => {
    expect(dash).toContain('Pourquoi ce classement');
  });

  it('renders rules_applied section', () => {
    expect(dash).toContain('rules_applied');
    expect(dash).toContain('Règles appliquées');
  });

  it('renders reasons_fr section', () => {
    expect(dash).toContain('reasons_fr');
    expect(dash).toContain('Constats');
  });

  it('renders missing_fields section', () => {
    expect(dash).toContain('missing_fields');
    expect(dash).toContain('À compléter');
  });

  it('has V1 disclaimer', () => {
    expect(dash).toContain('Heuristique V1');
    expect(dash).toContain('à confirmer par analyse réglementaire');
  });

  it('has why-drawer-content test id', () => {
    expect(dash).toContain('why-drawer-content');
  });

  it('has why-disclaimer test id', () => {
    expect(dash).toContain('why-disclaimer');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. Dashboard — Filter chips source guards
// ══════════════════════════════════════════════════════════════════════════════

describe('Dashboard has V43 filter chips (source guards)', () => {
  const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('has signal-filters test id', () => {
    expect(dash).toContain('signal-filters');
  });

  it('has signal filter state', () => {
    expect(dash).toContain('signalFilter');
  });

  it('has uncovered filter toggle', () => {
    expect(dash).toContain('uncoveredOnly');
    expect(dash).toContain('Sans EFA');
  });

  it('has missing field filter', () => {
    expect(dash).toContain('missingFieldFilter');
  });

  it('has filter-uncovered test id', () => {
    expect(dash).toContain('filter-uncovered');
  });

  it('has Réinitialiser button', () => {
    expect(dash).toContain('Réinitialiser');
  });

  it('has signal label "Assujetti probable"', () => {
    expect(dash).toContain('Assujetti probable');
  });

  it('has signal label "À vérifier"', () => {
    expect(dash).toContain('À vérifier');
  });

  it('has signal label "Non concerné"', () => {
    expect(dash).toContain('Non concerné');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Dashboard — Deep links
// ══════════════════════════════════════════════════════════════════════════════

describe('Dashboard V43 deep-links work', () => {
  const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('deep-links to patrimoine with site_id', () => {
    expect(dash).toContain('patrimoine?site_id=');
  });

  it('uses recommended_cta.to for navigation', () => {
    expect(dash).toContain('recommended_cta.to');
  });

  it('uses recommended_cta.label_fr for button text', () => {
    expect(dash).toContain('recommended_cta.label_fr');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Lever engine — reasons_fr injected (V43)
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever engine V43 rationale bullets', () => {
  const engine = src('models/leverEngineModel.js');

  it('injects reasons_fr into lev-tertiaire-create-efa', () => {
    expect(engine).toContain('reasons_fr');
    expect(engine).toContain('lev-tertiaire-create-efa');
  });

  it('injects reasons_fr into lev-tertiaire-complete-patrimoine', () => {
    expect(engine).toContain('lev-tertiaire-complete-patrimoine');
  });

  it('reads top_missing_fields from signals', () => {
    expect(engine).toContain('top_missing_fields');
  });

  it('reads signal sites for sample reasons', () => {
    expect(engine).toContain('signalSites');
  });

  it('includes V1 heuristic disclaimer in rationale', () => {
    expect(engine).toContain('Heuristique V1');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. ImpactDecisionPanel — DÉCOMMISSIONNÉ Phase 0.3 sprint Cockpit dual sol2
//
// Le contrat lever.reasons_fr + lever-reasons-* sera vérifié sur le futur
// <DecisionsTopThree> (3 décisions arbitrales narrées) en Phase 2.3
// (cf docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html).
// ══════════════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════════════
// 6. Backend V43 source guards (from frontend test)
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend V43 explainability (source guards)', () => {
  const service = backendSrc('services/tertiaire_service.py');

  it('has _build_site_explanation function', () => {
    expect(service).toContain('def _build_site_explanation');
  });

  it('returns signal_version V1', () => {
    expect(service).toContain('signal_version');
  });

  it('returns rules_applied', () => {
    expect(service).toContain('rules_applied');
  });

  it('returns reasons_fr', () => {
    expect(service).toContain('reasons_fr');
  });

  it('returns recommended_next_step', () => {
    expect(service).toContain('recommended_next_step');
  });

  it('returns recommended_cta', () => {
    expect(service).toContain('recommended_cta');
  });

  it('returns top_missing_fields', () => {
    expect(service).toContain('top_missing_fields');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 7. Labels 100% FR guard
// ══════════════════════════════════════════════════════════════════════════════

describe('V43 labels are 100% FR', () => {
  const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('has "Compléter le patrimoine" CTA', () => {
    expect(dash).toContain('Compléter le patrimoine');
  });

  it('has "Données manquantes" label', () => {
    expect(dash).toContain('Données manquantes');
  });

  it('has "Sites à traiter" section title', () => {
    expect(dash).toContain('Sites à traiter');
  });

  it('has "Entités Fonctionnelles Assujetties" section title', () => {
    expect(dash).toContain('Entités Fonctionnelles Assujetties');
  });

  const engine = src('models/leverEngineModel.js');

  it('lever rationale uses FR text', () => {
    expect(engine).toContain('Aucune EFA créée — action recommandée');
  });

  it('lever rationale mentions "données incomplètes"', () => {
    expect(engine).toContain('données incomplètes');
  });
});
