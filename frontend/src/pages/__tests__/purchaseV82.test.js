/**
 * PROMEOS — V82 — Composant "Option THS" structuré
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Option THS header (titre + badge Sans pénalité proéminent)
 * B. 2 bullets grand public
 * C. Structure badges + créneaux + CTAs preserved
 * D. Slider report expert-only
 * E. V81 backward compat
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Option THS header
// ============================================================
describe('A · Option THS header', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has option-ths-header data-testid', () => {
    expect(code).toContain('data-testid="option-ths-header"');
  });

  it('shows "Option Tarif Heures Solaires" title', () => {
    expect(code).toContain('Option Tarif Heures Solaires');
  });

  it('title uses Sun icon', () => {
    const match = code.match(/option-ths-header[\s\S]*?Sun/);
    expect(match).not.toBeNull();
  });

  it('Sans pénalité badge is in the header (prominent)', () => {
    const match = code.match(/option-ths-header[\s\S]*?reflex-sans-penalite/);
    expect(match).not.toBeNull();
  });

  it('Sans pénalité badge has prominent styling (border + larger)', () => {
    const match = code.match(/reflex-sans-penalite[\s\S]*?border[\s\S]*?emerald/);
    expect(match).not.toBeNull();
  });

  it('reflex-solar-detail has amber border card styling', () => {
    const match = code.match(/reflex-solar-detail[\s\S]*?border-amber-200/);
    expect(match).not.toBeNull();
  });
});

// ============================================================
// B. 2 bullets grand public
// ============================================================
describe('B · 2 bullets grand public', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has option-ths-bullets data-testid', () => {
    expect(code).toContain('data-testid="option-ths-bullets"');
  });

  it('bullet 1: mentions prix réduit + production solaire', () => {
    expect(code).toContain('prix réduit pendant les heures de forte production solaire');
  });

  it('bullet 2: mentions aucun engagement + facture identique', () => {
    expect(code).toContain('Aucun engagement de décalage');
    expect(code).toContain('facture reste identique');
  });

  it('bullets are NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}option-ths-bullets/);
    expect(match).toBeNull();
  });
});

// ============================================================
// C. Structure: badges + créneaux + CTAs preserved
// ============================================================
describe('C · Structure preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has reflex-badges container', () => {
    expect(code).toContain('data-testid="reflex-badges"');
  });

  it('still has reflex-creneaux with été/hiver', () => {
    expect(code).toContain('data-testid="reflex-creneaux"');
    expect(code).toContain('13h–16h');
    expect(code).toContain('8h–10h');
  });

  it('still has reflex-blocs-detail', () => {
    expect(code).toContain('data-testid="reflex-blocs-detail"');
  });

  it('still has reflex-delta-vs-fixe', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('still has reflex-cross-ctas with all 7 CTAs', () => {
    expect(code).toContain('data-testid="reflex-cross-ctas"');
    expect(code).toContain('data-testid="cta-conso-explorer-reflex"');
    expect(code).toContain('data-testid="cta-bill-intel-reflex"');
    expect(code).toContain('data-testid="cta-perf-monitoring-reflex"');
    expect(code).toContain('data-testid="cta-create-action-reflex"');
    expect(code).toContain('data-testid="cta-tester-tarif-solaire"');
    expect(code).toContain('data-testid="cta-assistant-ths"');
  });

  it('still has reflex-effort-badge', () => {
    expect(code).toContain('data-testid="reflex-effort-badge"');
  });

  it('still has reflex-report-pct', () => {
    expect(code).toContain('data-testid="reflex-report-pct"');
  });
});

// ============================================================
// D. Slider report is expert-only
// ============================================================
describe('D · Report slider expert-only', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('report toggle gated by isExpert', () => {
    const match = code.match(/reportEnabled && isExpert/);
    expect(match).not.toBeNull();
  });

  it('has data-testid="report-toggle"', () => {
    expect(code).toContain('data-testid="report-toggle"');
  });

  it('Option THS header is NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}option-ths-header/);
    expect(match).toBeNull();
  });
});

// ============================================================
// E. V81 backward compat
// ============================================================
describe('E · V81 backward compat', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('header is dynamic scenarios.length (V81)', () => {
    expect(code).toContain('{scenarios.length} stratégies comparées');
  });

  it('still has cta-assistant-ths (V81)', () => {
    expect(code).toContain('data-testid="cta-assistant-ths"');
  });

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('V82 header comment', () => {
    expect(code).toContain('V82:');
  });
});
