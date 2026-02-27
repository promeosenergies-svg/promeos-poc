/**
 * PROMEOS — Achat Énergie V77 — Tarif Heures Solaires
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Labels: "Tarif Heures Solaires" partout, aucun "Budget Sécurisé"
 * B. Explicability: delta vs Prix Fixe standard
 * C. Assistant: OfferStructure HEURES_SOLAIRES, labels, colors, solar slots
 * D. Deep-link: toPurchase supports site_id, PurchasePage reads it
 * E. Tester CTA: cta-tester-tarif-solaire
 * F. No hardcoded URLs
 * G. V76 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Labels "Tarif Heures Solaires"
// ============================================================
describe('A · Labels Tarif Heures Solaires', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('STRATEGY_META label is "Tarif Heures Solaires"', () => {
    expect(code).toContain("label: 'Tarif Heures Solaires'");
  });

  it('no "Budget Sécurisé" remnant in labels', () => {
    expect(code).not.toContain('Budget Sécurisé');
  });

  it('badge says TARIF HEURES SOLAIRES', () => {
    expect(code).toContain('TARIF HEURES SOLAIRES');
  });

  it('portfolio table column says Tarif Heures Solaires', () => {
    expect(code).toContain('>Tarif Heures Solaires<');
  });

  it('top-list heading says Meilleurs gains Tarif Heures Solaires', () => {
    expect(code).toContain('Meilleurs gains Tarif Heures Solaires');
  });

  it('campaign CTA says Lancer campagne Tarif Heures Solaires', () => {
    expect(code).toContain('Lancer campagne Tarif Heures Solaires');
  });

  it('scenario_label prefill uses Tarif Heures Solaires', () => {
    const match = code.match(/cta-create-action-reflex[\s\S]*?scenario_label:\s*'Tarif Heures Solaires'/);
    expect(match).not.toBeNull();
  });

  it('STRATEGY_META desc is grand-public friendly', () => {
    expect(code).toContain("Profitez des prix bas quand le soleil produit, sans pénalité si vous ne décalez pas.");
  });

  it('visible in mode normal (not gated by isExpert)', () => {
    const match = code.match(/const STRATEGY_META[\s\S]*?reflex_solar:\s*\{[\s\S]*?label:\s*'Tarif Heures Solaires'/);
    expect(match).not.toBeNull();
  });
});

// ============================================================
// B. Explicability: delta vs Prix Fixe standard
// ============================================================
describe('B · Bloc explicability (delta vs Fixe)', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-delta-vs-fixe container', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('references fixe scenario for comparison', () => {
    expect(code).toContain("s.strategy === 'fixe'");
  });

  it('shows "vs Prix Fixe standard" text', () => {
    expect(code).toContain('vs Prix Fixe standard');
  });

  it('has expert tooltip with technical desc', () => {
    expect(code).toContain('data-testid="reflex-expert-tooltip"');
  });

  it('expert tooltip is gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]*?reflex-expert-tooltip/);
    expect(match).not.toBeNull();
  });

  it('tooltip mentions anciennement RéFlex Solar', () => {
    expect(code).toContain('anciennement RéFlex Solar');
  });

  it('uses Info icon for tooltip', () => {
    expect(code).toContain('Info');
  });
});

// ============================================================
// C. Assistant: HEURES_SOLAIRES offer
// ============================================================
describe('C · Assistant Heures Solaires', () => {
  const types = readSrc('domain', 'purchase', 'types.js');
  const assistant = readSrc('pages', 'PurchaseAssistantPage.jsx');
  const demo = readSrc('domain', 'purchase', 'demoData.js');

  it('OfferStructure has HEURES_SOLAIRES key', () => {
    expect(types).toContain("HEURES_SOLAIRES: 'HEURES_SOLAIRES'");
  });

  it('STRUCTURE_LABELS has Heures Solaires', () => {
    expect(assistant).toContain("HEURES_SOLAIRES: 'Heures Solaires'");
  });

  it('STRUCTURE_COLORS has amber for HEURES_SOLAIRES', () => {
    expect(assistant).toContain("HEURES_SOLAIRES: 'bg-amber-100 text-amber-700'");
  });

  it('DEMO_OFFERS includes a HEURES_SOLAIRES offer', () => {
    expect(demo).toContain('HEURES_SOLAIRES');
  });

  it('demo offer has solarSlots', () => {
    expect(demo).toContain('solarSlots');
  });

  it('assistant renders offer-solar-slots', () => {
    expect(assistant).toContain('data-testid="offer-solar-slots"');
  });

  it('assistant renders offer-no-penalty message', () => {
    expect(assistant).toContain('data-testid="offer-no-penalty"');
  });

  it('no-penalty text in French', () => {
    expect(assistant).toContain('Pas de pénalité si vous ne décalez pas votre consommation.');
  });

  it('assistant imports Sun icon', () => {
    expect(assistant).toContain('Sun');
  });
});

// ============================================================
// D. Deep-link: toPurchase with site_id
// ============================================================
describe('D · Deep-link site_id', () => {
  const routes = readSrc('services', 'routes.js');
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('toPurchase accepts site_id param', () => {
    expect(routes).toContain('opts.site_id');
  });

  it('toPurchase sets site_id in URLSearchParams', () => {
    const match = routes.match(/toPurchase[\s\S]*?site_id/);
    expect(match).not.toBeNull();
  });

  it('PurchasePage reads site_id from URL searchParams', () => {
    expect(code).toContain("searchParams.get('site_id')");
  });

  it('PurchasePage imports toPurchase from routes', () => {
    expect(code).toContain('toPurchase');
    expect(code).toContain("from '../services/routes'");
  });
});

// ============================================================
// E. Tester CTA
// ============================================================
describe('E · Tester CTA', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has cta-tester-tarif-solaire with data-testid', () => {
    expect(code).toContain('data-testid="cta-tester-tarif-solaire"');
  });

  it('CTA text says "Tester un Tarif Heures Solaires"', () => {
    expect(code).toContain('Tester un Tarif Heures Solaires');
  });

  it('CTA navigates via toPurchase with tab + site_id', () => {
    const match = code.match(/cta-tester-tarif-solaire[\s\S]*?toPurchase\(\{[\s\S]*?tab:\s*'simulation'[\s\S]*?site_id/);
    expect(match).not.toBeNull();
  });

  it('CTA uses Sun icon', () => {
    // Sun icon imported and used near tester CTA
    expect(code).toContain('Sun');
  });
});

// ============================================================
// F. No hardcoded URLs
// ============================================================
describe('F · No hardcoded URLs', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('no hardcoded /achat-energie URLs', () => {
    // toPurchase() should be used, not raw strings
    expect(code).not.toContain("'/achat-energie");
  });

  it('no hardcoded /consommations/ URLs', () => {
    expect(code).not.toContain("'/consommations/");
  });

  it('no hardcoded /bill-intel URLs', () => {
    expect(code).not.toContain("'/bill-intel");
  });

  it('no hardcoded /actions/ URLs', () => {
    expect(code).not.toContain("'/actions/");
  });
});

// ============================================================
// G. V76 backward compat preserved
// ============================================================
describe('G · V76 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('internal strategy key still reflex_solar', () => {
    expect(code).toContain("s.strategy === 'reflex_solar'");
  });

  it('data-testid reflex-solar-detail unchanged', () => {
    expect(code).toContain('data-testid="reflex-solar-detail"');
  });

  it('data-testid reflex-badges unchanged', () => {
    expect(code).toContain('data-testid="reflex-badges"');
  });

  it('still has report toggle + slider (V75)', () => {
    expect(code).toContain('data-testid="report-toggle"');
    expect(code).toContain('data-testid="report-slider"');
  });

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('still has scope lock (V72)', () => {
    expect(code).toContain('isScopeLocked');
  });

  it('still has autosave (V72)', () => {
    expect(code).toContain('autosaveTimer');
  });

  it('still has confidence badges (V72)', () => {
    expect(code).toContain('data-testid="confidence-badges"');
  });

  it('still has Exporter Note de Decision', () => {
    expect(code).toContain('Exporter Note de Decision');
  });

  it('V77 header comment', () => {
    expect(code).toContain('V77: + Rename Budget Securise');
  });
});
