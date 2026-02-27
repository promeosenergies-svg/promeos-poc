/**
 * PROMEOS — V79 — Cross-brique Performance + Audit Tarif Heures Solaires
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Performance KPI card (MonitoringPage)
 * B. Cross-brique retour (PurchasePage → Performance)
 * C. Routes registry (toMonitoring)
 * D. No hardcoded URLs
 * E. Mode normal (non-expert)
 * F. V78 backward compat
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Performance KPI card — Tarif Heures Solaires
// ============================================================
describe('A · Performance KPI card', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has "Tarif Heures Solaires" text in ExecutiveSummary', () => {
    expect(code).toContain("title: 'Tarif Heures Solaires'");
  });

  it('has kpi-tarif-heures-solaires testid', () => {
    expect(code).toContain('kpi-tarif-heures-solaires');
  });

  it('uses Sun icon for THS card', () => {
    const match = code.match(/icon: Sun[\s\S]*?Tarif Heures Solaires/);
    expect(match).not.toBeNull();
  });

  it('shows "% solaire" value from off_hours_ratio', () => {
    expect(code).toContain('% solaire');
    expect(code).toContain('off_hours_ratio');
  });

  it('shows gain estimé from offHoursEst', () => {
    expect(code).toContain('Gain estimé');
  });

  it('has "Simuler" CTA linking to toPurchase', () => {
    const match = code.match(/Simuler[\s\S]*?toPurchase/);
    expect(match).not.toBeNull();
  });

  it('Simuler CTA passes tab=simulation + site_id', () => {
    const match = code.match(/toPurchase\(\{[\s\S]*?tab:\s*'simulation'[\s\S]*?site_id/);
    expect(match).not.toBeNull();
  });

  it('has "Créer action" CTA for TARIF_HEURES_SOLAIRES', () => {
    expect(code).toContain('TARIF_HEURES_SOLAIRES');
  });

  it('imports toPurchase from routes', () => {
    expect(code).toContain('toPurchase');
    expect(code).toContain("from '../services/routes'");
  });

  it('ExecutiveSummary grid is 5 columns on lg', () => {
    expect(code).toContain('lg:grid-cols-5');
  });

  it('V79 header comment', () => {
    expect(code).toContain('V79:');
  });
});

// ============================================================
// B. Cross-brique retour (Purchase → Performance)
// ============================================================
describe('B · Cross-brique retour', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has cta-perf-monitoring-reflex with data-testid', () => {
    expect(code).toContain('data-testid="cta-perf-monitoring-reflex"');
  });

  it('CTA text says "Voir performance"', () => {
    expect(code).toContain('Voir performance');
  });

  it('CTA navigates via toMonitoring with site_id', () => {
    const match = code.match(/cta-perf-monitoring-reflex[\s\S]*?toMonitoring\(\{[\s\S]*?site_id/);
    expect(match).not.toBeNull();
  });

  it('uses Activity icon', () => {
    expect(code).toContain('Activity');
  });

  it('imports toMonitoring from routes', () => {
    expect(code).toContain('toMonitoring');
    expect(code).toContain("from '../services/routes'");
  });
});

// ============================================================
// C. Routes registry
// ============================================================
describe('C · Routes registry', () => {
  const routes = readSrc('services', 'routes.js');

  it('exports toMonitoring function', () => {
    expect(routes).toContain('export function toMonitoring');
  });

  it('toMonitoring accepts site_id param', () => {
    const match = routes.match(/toMonitoring[\s\S]*?opts\.site_id/);
    expect(match).not.toBeNull();
  });

  it('toMonitoring returns /monitoring path', () => {
    expect(routes).toContain('/monitoring');
  });
});

// ============================================================
// D. No hardcoded URLs
// ============================================================
describe('D · No hardcoded URLs', () => {
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
// E. Mode normal (non-expert)
// ============================================================
describe('E · Mode normal visibility', () => {
  const purchase = readSrc('pages', 'PurchasePage.jsx');
  const monitoring = readSrc('pages', 'MonitoringPage.jsx');

  it('THS KPI card is NOT gated by isExpert in Performance', () => {
    // The card is in the cards array, not wrapped in isExpert check
    const match = monitoring.match(/isExpert[\s\S]{0,50}Tarif Heures Solaires/);
    expect(match).toBeNull();
  });

  it('Voir performance CTA is NOT gated by isExpert in Purchase', () => {
    const match = purchase.match(/isExpert[\s\S]{0,50}cta-perf-monitoring-reflex/);
    expect(match).toBeNull();
  });

  it('dejargon: no "Report HP" in user-facing labels', () => {
    expect(purchase).not.toContain('Report HP');
  });

  it('dejargon: uses "Décalage heures pleines" instead', () => {
    expect(purchase).toContain('Décalage heures pleines');
  });
});

// ============================================================
// F. V78 backward compat
// ============================================================
describe('F · V78 backward compat', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has créneaux bloc (V78)', () => {
    expect(code).toContain('data-testid="reflex-creneaux"');
  });

  it('still has punchy subtitle (V78)', () => {
    expect(code).toContain('Payez moins quand le soleil brille');
  });

  it('still has delta-vs-fixe (V77)', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('still has report toggle (V75)', () => {
    expect(code).toContain('data-testid="report-toggle"');
  });

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('V79 header comment in PurchasePage', () => {
    expect(code).toContain('V79:');
  });
});
