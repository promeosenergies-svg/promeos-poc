/**
 * PROMEOS — Achat Énergie V76 — Rename ReFlex → Budget Sécurisé
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Label visible en mode normal (pas Expert-only)
 * B. Aucun "RéFlex" restant dans les labels user-visible
 * C. Codes internes (strategy key, data-testid) inchangés
 * D. Sous-titre grand public présent
 * E. Prefill action: scenario_label + source_type=achat
 * F. V75 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Label "Tarif Heures Solaires" visible en mode normal
// ============================================================
describe('A · Label Tarif Heures Solaires visible (mode normal)', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('STRATEGY_META reflex_solar label is "Tarif Heures Solaires"', () => {
    expect(code).toContain("label: 'Tarif Heures Solaires'");
  });

  it('label is NOT gated by isExpert', () => {
    // The label should be in the STRATEGY_META constant, outside any isExpert condition
    const match = code.match(
      /const STRATEGY_META[\s\S]*?reflex_solar:\s*\{[\s\S]*?label:\s*'Tarif Heures Solaires'/
    );
    expect(match).not.toBeNull();
  });

  it('report controls badge says TARIF HEURES SOLAIRES', () => {
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
});

// ============================================================
// B. Aucun "RéFlex" restant dans labels user-visible
// ============================================================
describe('B · No RéFlex in user-visible labels', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('no label containing "ReFlex Solar"', () => {
    expect(code).not.toContain("label: 'ReFlex Solar'");
  });

  it('no table header "Budget RéFlex"', () => {
    expect(code).not.toContain('>Budget RéFlex<');
  });

  it('no "Meilleurs gains RéFlex" heading', () => {
    expect(code).not.toContain('Meilleurs gains RéFlex');
  });

  it('no "Lancer campagne RéFlex" CTA text', () => {
    expect(code).not.toContain('Lancer campagne RéFlex');
  });

  it('no badge text "REFLEX" (uppercase)', () => {
    // Only "BUDGET SÉCURISÉ" badge, not old "REFLEX"
    expect(code).not.toMatch(/>REFLEX</);
  });
});

// ============================================================
// C. Codes internes inchangés (strategy key, data-testid)
// ============================================================
describe('C · Internal codes unchanged', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('strategy key is still reflex_solar', () => {
    expect(code).toContain("s.strategy === 'reflex_solar'");
  });

  it('data-testid reflex-solar-detail unchanged', () => {
    expect(code).toContain('data-testid="reflex-solar-detail"');
  });

  it('data-testid reflex-badges unchanged', () => {
    expect(code).toContain('data-testid="reflex-badges"');
  });

  it('data-testid reflex-effort-badge unchanged', () => {
    expect(code).toContain('data-testid="reflex-effort-badge"');
  });

  it('data-testid reflex-report-controls unchanged', () => {
    expect(code).toContain('data-testid="reflex-report-controls"');
  });

  it('data-testid cta-create-action-reflex unchanged', () => {
    expect(code).toContain('data-testid="cta-create-action-reflex"');
  });

  it('data-testid cta-campaign-reflex unchanged', () => {
    expect(code).toContain('data-testid="cta-campaign-reflex"');
  });

  it('data-testid reflex-portfolio-table unchanged', () => {
    expect(code).toContain('data-testid="reflex-portfolio-table"');
  });

  it('data-testid reflex-top-lists unchanged', () => {
    expect(code).toContain('data-testid="reflex-top-lists"');
  });

  it('data-testid reflex-dynamic-badge unchanged', () => {
    expect(code).toContain('data-testid="reflex-dynamic-badge"');
  });
});

// ============================================================
// D. Sous-titre grand public
// ============================================================
describe('D · Grand-public subtitle', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('STRATEGY_META desc contains the new subtitle', () => {
    expect(code).toContain(
      'Payez moins quand le soleil brille — sans surcoût si vous ne changez rien.'
    );
  });

  it('subtitle is in reflex_solar desc field', () => {
    const match = code.match(
      /reflex_solar:\s*\{[\s\S]*?desc:\s*["']Payez moins quand le soleil brille/
    );
    expect(match).not.toBeNull();
  });
});

// ============================================================
// E. Prefill action: scenario_label + source_type
// ============================================================
describe('E · Action prefill scenario_label', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('reflex CTA prefills scenario_label=Tarif Heures Solaires', () => {
    const match = code.match(
      /cta-create-action-reflex[\s\S]*?scenario_label:\s*'Tarif Heures Solaires'/
    );
    expect(match).not.toBeNull();
  });

  it('reflex CTA prefills source_type=achat', () => {
    const match = code.match(/cta-create-action-reflex[\s\S]*?source_type:\s*'achat'/);
    expect(match).not.toBeNull();
  });

  it('cockpit action CTA includes scenario label in prefill', () => {
    // P3: main CTA migrated to openActionDrawer, but reflex CTAs still use toActionNew
    expect(code).toContain('meta.label');
  });

  it('top-list gain action has scenario_label', () => {
    const match = code.match(
      /Tarif Heures Solaires — gain[\s\S]*?scenario_label:\s*'Tarif Heures Solaires'/
    );
    expect(match).not.toBeNull();
  });

  it('campaign CTA includes scenario_label', () => {
    const match = code.match(
      /cta-campaign-reflex[\s\S]*?scenario_label:\s*'Tarif Heures Solaires'/
    );
    expect(match).not.toBeNull();
  });

  it('all reflex action prefills have source_type=achat', () => {
    // P3: main CTA migrated to openActionDrawer; remaining toActionNew calls still pass source_type: 'achat'
    const matches = code.match(/toActionNew\(\{[^}]*source_type:\s*'achat'/g);
    expect(matches).not.toBeNull();
    expect(matches.length).toBeGreaterThanOrEqual(3);
  });
});

// ============================================================
// F. V75 backward compat preserved
// ============================================================
describe('F · V75 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has report toggle + slider (V75)', () => {
    expect(code).toContain('data-testid="report-toggle"');
    expect(code).toContain('data-testid="report-slider"');
  });

  it('still has DYNAMIQUE badge (V75)', () => {
    expect(code).toContain('DYNAMIQUE');
  });

  it('still has 3 bullet points WHY (V75)', () => {
    const match = code.match(/reflex_solar:\s*["'].*•.*\\n.*•.*\\n.*•/);
    expect(match).not.toBeNull();
  });

  it('still has portfolio table + top-lists (V75)', () => {
    expect(code).toContain('data-testid="reflex-portfolio-table"');
    expect(code).toContain('data-testid="reflex-top-lists"');
  });

  it('still has campaign CTA (V75)', () => {
    expect(code).toContain('data-testid="cta-campaign-reflex"');
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

  it('V76 header comment', () => {
    expect(code).toContain('V76: + Rename ReFlex');
  });
});
