/**
 * PROMEOS — Achat Énergie V78 — Audit & Fix Tarif Heures Solaires
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Sous-titre grand public
 * B. Créneaux été/hiver sur carte
 * C. Pourquoi ? 3 bullets été/hiver
 * D. CTAs enrichis (date_from, date_to, month)
 * E. Mode normal (visible sans isExpert)
 * F. Zéro URL hardcodée
 * G. V77 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Sous-titre grand public
// ============================================================
describe('A · Sous-titre grand public', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('desc is the new punchy subtitle', () => {
    expect(code).toContain(
      'Payez moins quand le soleil brille — sans surcoût si vous ne changez rien.'
    );
  });

  it('no old "Profitez des prix bas" subtitle remnant', () => {
    expect(code).not.toContain('Profitez des prix bas quand le soleil produit');
  });

  it('subtitle is in STRATEGY_META reflex_solar.desc', () => {
    const match = code.match(
      /reflex_solar:\s*\{[\s\S]*?desc:\s*["']Payez moins quand le soleil brille/
    );
    expect(match).not.toBeNull();
  });
});

// ============================================================
// B. Créneaux été/hiver sur carte
// ============================================================
describe('B · Créneaux été/hiver on card', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-creneaux with data-testid', () => {
    expect(code).toContain('data-testid="reflex-creneaux"');
  });

  it('shows "Créneaux Heures Solaires" header', () => {
    expect(code).toContain('Créneaux Heures Solaires');
  });

  it('shows été 13h–16h (sem.)', () => {
    expect(code).toContain('13h–16h (sem.)');
  });

  it('shows été 10h–17h (WE)', () => {
    expect(code).toContain('10h–17h (WE)');
  });

  it('shows hiver 8h–10h & 17h–20h', () => {
    expect(code).toContain('8h–10h & 17h–20h');
  });

  it('shows "Été" label', () => {
    expect(code).toContain('Été :');
  });

  it('shows "Hiver" label', () => {
    expect(code).toContain('Hiver :');
  });

  it('uses Clock icon for créneaux', () => {
    expect(code).toContain('Clock');
  });

  it('créneaux is inside reflex-solar-detail (not expert-gated)', () => {
    const match = code.match(/reflex-solar-detail[\s\S]*?reflex-creneaux/);
    expect(match).not.toBeNull();
  });
});

// ============================================================
// C. Pourquoi ? 3 bullets été/hiver
// ============================================================
describe('C · Pourquoi bullets été/hiver', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('STRATEGY_WHY reflex_solar has 3 bullet points', () => {
    const match = code.match(/reflex_solar:\s*["'].*•.*\\n.*•.*\\n.*•/);
    expect(match).not.toBeNull();
  });

  it('bullet 1 mentions été + surproduction solaire', () => {
    expect(code).toContain('surproduction solaire');
  });

  it('bullet 2 mentions hiver créneaux 8h–10h et 17h–20h', () => {
    expect(code).toContain('8h–10h et 17h–20h');
  });

  it('bullet 3 mentions "Aucune pénalité"', () => {
    expect(code).toContain('Aucune pénalité');
  });

  it('bullets mention Report optionnel en mode Expert', () => {
    expect(code).toContain('Report optionnel en mode Expert');
  });
});

// ============================================================
// D. CTAs enrichis
// ============================================================
describe('D · CTAs enrichis (date_from, date_to, month)', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('conso CTA uses date_from param', () => {
    const match = code.match(/cta-conso-explorer-reflex[\s\S]*?date_from:/);
    expect(match).not.toBeNull();
  });

  it('conso CTA uses date_to param', () => {
    const match = code.match(/cta-conso-explorer-reflex[\s\S]*?date_to:/);
    expect(match).not.toBeNull();
  });

  it('conso CTA computes 90-day window via setDate', () => {
    expect(code).toContain('from.setDate(from.getDate() - 90)');
  });

  it('conso CTA uses toISOString for date formatting', () => {
    const match = code.match(/cta-conso-explorer-reflex[\s\S]*?toISOString\(\)\.slice\(0, 10\)/);
    expect(match).not.toBeNull();
  });

  it('facture CTA passes month param', () => {
    const match = code.match(/cta-bill-intel-reflex[\s\S]*?month:/);
    expect(match).not.toBeNull();
  });

  it('facture CTA month is YYYY-MM format (slice 0,7)', () => {
    const match = code.match(/cta-bill-intel-reflex[\s\S]*?toISOString\(\)\.slice\(0, 7\)/);
    expect(match).not.toBeNull();
  });

  it('conso CTA uses date_from instead of days: 90', () => {
    // The cross-brique CTA block (between cta-conso-explorer-reflex and cta-bill-intel-reflex) should NOT have days: 90
    const block = code.match(/cta-conso-explorer-reflex[\s\S]*?cta-bill-intel-reflex/);
    expect(block).not.toBeNull();
    expect(block[0]).toContain('date_from');
    expect(block[0]).not.toContain('days: 90');
  });
});

// ============================================================
// E. Mode normal (visible sans isExpert)
// ============================================================
describe('E · Mode normal visibility', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('card is NOT gated by isExpert (visible for all)', () => {
    // reflex_solar card renders for all strategies without isExpert check
    const match = code.match(
      /const STRATEGY_META[\s\S]*?reflex_solar:\s*\{[\s\S]*?label:\s*'Tarif Heures Solaires'/
    );
    expect(match).not.toBeNull();
  });

  it('créneaux bloc is NOT gated by isExpert', () => {
    // reflex-creneaux should NOT have isExpert before it
    const match = code.match(/isExpert[\s\S]{0,50}reflex-creneaux/);
    expect(match).toBeNull();
  });

  it('subtitle is in STRATEGY_META (not conditional)', () => {
    expect(code).toContain('Payez moins quand le soleil brille');
  });

  it('expert tooltip IS gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]*?reflex-expert-tooltip/);
    expect(match).not.toBeNull();
  });

  it('report slider IS gated by isExpert', () => {
    expect(code).toContain('reportEnabled && isExpert');
  });
});

// ============================================================
// F. Zéro URL hardcodée
// ============================================================
describe('F · No hardcoded URLs', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('no hardcoded /consommations/ URLs', () => {
    expect(code).not.toContain("'/consommations/");
  });

  it('no hardcoded /bill-intel URLs', () => {
    expect(code).not.toContain("'/bill-intel");
  });

  it('no hardcoded /actions/ URLs', () => {
    expect(code).not.toContain("'/actions/");
  });

  it('no hardcoded /achat-energie URLs', () => {
    expect(code).not.toContain("'/achat-energie");
  });
});

// ============================================================
// G. V77 backward compat preserved
// ============================================================
describe('G · V77 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has delta-vs-fixe (V77)', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('still has tester CTA (V77)', () => {
    expect(code).toContain('data-testid="cta-tester-tarif-solaire"');
  });

  it('still has report toggle + slider (V75)', () => {
    expect(code).toContain('data-testid="report-toggle"');
    expect(code).toContain('data-testid="report-slider"');
  });

  it('still has DYNAMIQUE badge (V75)', () => {
    expect(code).toContain('DYNAMIQUE');
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

  it('V78 header comment', () => {
    expect(code).toContain('V78: + Audit THS');
  });
});
