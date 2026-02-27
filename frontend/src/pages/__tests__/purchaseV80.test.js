/**
 * PROMEOS — V80 — Audit final THS: badge Sans pénalité, nettoyage jargon
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Badge "Sans pénalité" in reflex-solar-detail
 * B. Tooltip jargon cleanup
 * C. Grand public visibility audit
 * D. Cross-brique CTAs completeness
 * E. No hardcoded URLs (full re-check)
 * F. V79 backward compat
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Badge "Sans pénalité"
// ============================================================
describe('A · Badge Sans pénalité', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-sans-penalite data-testid', () => {
    expect(code).toContain('data-testid="reflex-sans-penalite"');
  });

  it('shows "Sans pénalité" text', () => {
    expect(code).toContain('Sans pénalité');
  });

  it('uses CheckCircle2 icon for badge', () => {
    const match = code.match(/reflex-sans-penalite[\s\S]*?CheckCircle2/);
    expect(match).not.toBeNull();
  });

  it('badge is inside option-ths-header (V82: promoted to header)', () => {
    const block = code.match(/option-ths-header[\s\S]*?<\/div>/);
    expect(block).not.toBeNull();
    expect(block[0]).toContain('reflex-sans-penalite');
  });

  it('badge is NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}reflex-sans-penalite/);
    expect(match).toBeNull();
  });
});

// ============================================================
// B. Tooltip jargon cleanup
// ============================================================
describe('B · Tooltip jargon cleanup', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('no "anciennement RéFlex" in tooltip', () => {
    expect(code).not.toContain('anciennement RéFlex');
  });

  it('no "anciennement" anywhere in user-visible text', () => {
    // Only version comments should contain old names
    const lines = code.split('\n');
    const nonCommentLines = lines.filter(
      (l) => !l.trim().startsWith('*') && !l.trim().startsWith('//')
    );
    const joined = nonCommentLines.join('\n');
    expect(joined).not.toContain('anciennement');
  });

  it('expert tooltip still exists with clean text', () => {
    expect(code).toContain('data-testid="reflex-expert-tooltip"');
    expect(code).toContain('Tarification dynamique par blocs horaires avec optimisation solaire');
  });

  it('no "RéFlex" in user-visible labels (non-comment lines)', () => {
    const lines = code.split('\n');
    const nonCommentLines = lines.filter(
      (l) => !l.trim().startsWith('*') && !l.trim().startsWith('//')
    );
    const joined = nonCommentLines.join('\n');
    // RéFlex should only appear in comments, not in labels
    expect(joined).not.toContain("'RéFlex");
    expect(joined).not.toContain('"RéFlex');
  });

  it('no "Budget Sécurisé" in user-visible labels', () => {
    const lines = code.split('\n');
    const nonCommentLines = lines.filter(
      (l) => !l.trim().startsWith('*') && !l.trim().startsWith('//')
    );
    const joined = nonCommentLines.join('\n');
    expect(joined).not.toContain('Budget Sécurisé');
    expect(joined).not.toContain('Budget Securise');
  });
});

// ============================================================
// C. Grand public visibility audit
// ============================================================
describe('C · Grand public visibility', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('reflex-solar-detail is NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}reflex-solar-detail/);
    expect(match).toBeNull();
  });

  it('reflex-badges is NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}reflex-badges/);
    expect(match).toBeNull();
  });

  it('reflex-creneaux is NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}reflex-creneaux/);
    expect(match).toBeNull();
  });

  it('cross-CTAs are NOT gated by isExpert', () => {
    const match = code.match(/isExpert[\s\S]{0,50}reflex-cross-ctas/);
    expect(match).toBeNull();
  });

  it('label "Tarif Heures Solaires" in STRATEGY_META', () => {
    expect(code).toContain("label: 'Tarif Heures Solaires'");
  });

  it('sous-titre grand public present', () => {
    expect(code).toContain('Payez moins quand le soleil brille');
  });

  it('has "Pourquoi ?" in STRATEGY_WHY for reflex_solar', () => {
    const match = code.match(/STRATEGY_WHY\s*=\s*\{[\s\S]*?reflex_solar:\s*["']/);
    expect(match).not.toBeNull();
  });

  it('no "Report HP" in user-facing labels', () => {
    expect(code).not.toContain('Report HP');
  });

  it('uses "Décalage heures pleines" instead', () => {
    expect(code).toContain('Décalage heures pleines');
  });
});

// ============================================================
// D. Cross-brique CTAs completeness
// ============================================================
describe('D · Cross-brique CTAs completeness', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has 5 CTAs in reflex-cross-ctas', () => {
    expect(code).toContain('data-testid="cta-conso-explorer-reflex"');
    expect(code).toContain('data-testid="cta-bill-intel-reflex"');
    expect(code).toContain('data-testid="cta-perf-monitoring-reflex"');
    expect(code).toContain('data-testid="cta-create-action-reflex"');
    expect(code).toContain('data-testid="cta-tester-tarif-solaire"');
  });

  it('Conso CTA uses date_from/date_to', () => {
    const block = code.match(/cta-conso-explorer-reflex[\s\S]*?cta-bill-intel-reflex/);
    expect(block).not.toBeNull();
    expect(block[0]).toContain('date_from');
    expect(block[0]).toContain('date_to');
  });

  it('Facture CTA uses month param', () => {
    const block = code.match(/cta-bill-intel-reflex[\s\S]*?cta-perf-monitoring-reflex/);
    expect(block).not.toBeNull();
    expect(block[0]).toContain('month');
  });

  it('Perf CTA uses toMonitoring with site_id', () => {
    const match = code.match(/cta-perf-monitoring-reflex[\s\S]*?toMonitoring\(\{[\s\S]*?site_id/);
    expect(match).not.toBeNull();
  });

  it('Action CTA uses source_type=achat + scenario_label', () => {
    const match = code.match(/cta-create-action-reflex[\s\S]*?source_type:\s*'achat'/);
    expect(match).not.toBeNull();
    const labelMatch = code.match(/cta-create-action-reflex[\s\S]*?scenario_label/);
    expect(labelMatch).not.toBeNull();
  });
});

// ============================================================
// E. No hardcoded URLs (full re-check)
// ============================================================
describe('E · No hardcoded URLs', () => {
  const purchase = readSrc('pages', 'PurchasePage.jsx');
  const monitoring = readSrc('pages', 'MonitoringPage.jsx');

  it('no hardcoded /monitoring in PurchasePage', () => {
    expect(purchase).not.toContain("'/monitoring");
  });

  it('no hardcoded /achat-energie in MonitoringPage', () => {
    expect(monitoring).not.toContain("'/achat-energie");
  });

  it('no hardcoded /consommations/ in PurchasePage', () => {
    expect(purchase).not.toContain("'/consommations/");
  });

  it('no hardcoded /bill-intel in PurchasePage', () => {
    expect(purchase).not.toContain("'/bill-intel");
  });

  it('no hardcoded /actions/ in PurchasePage', () => {
    expect(purchase).not.toContain("'/actions/");
  });
});

// ============================================================
// F. V79 backward compat
// ============================================================
describe('F · V79 backward compat', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has reflex-creneaux (V78)', () => {
    expect(code).toContain('data-testid="reflex-creneaux"');
  });

  it('still has delta-vs-fixe (V77)', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('still has report toggle (V75)', () => {
    expect(code).toContain('data-testid="report-toggle"');
  });

  it('still has Voir performance CTA (V79)', () => {
    expect(code).toContain('data-testid="cta-perf-monitoring-reflex"');
  });

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('Performance KPI card still has Tarif Heures Solaires', () => {
    const mon = readSrc('pages', 'MonitoringPage.jsx');
    expect(mon).toContain("title: 'Tarif Heures Solaires'");
    expect(mon).toContain('kpi-tarif-heures-solaires');
  });

  it('V80 header comment', () => {
    expect(code).toContain('V80:');
  });
});
