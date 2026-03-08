/**
 * KPI System Freeze — Source-guard tests
 * Validates: KpiCardInline unification, accent fixes, Performance layout,
 * NavPanel always-open sections.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

// ── A. KpiCardInline unification ────────────────────────────────────────────

describe('A. KpiCardInline shared component', () => {
  const code = src('ui/KpiCard.jsx');

  it('exports KpiCardInline', () => {
    expect(code).toMatch(/export function KpiCardInline/);
  });

  it('KpiCardInline has break-words on value', () => {
    expect(code).toMatch(/KpiCardInline[\s\S]*?break-words/);
  });

  it('KpiCardInline supports loading skeleton', () => {
    expect(code).toMatch(/KpiCardInline[\s\S]*?animate-pulse/);
  });

  it('KpiCardInline supports unit prop', () => {
    expect(code).toMatch(/KpiCardInline[\s\S]*?\{unit/);
  });

  it('ui/index.js re-exports KpiCardInline', () => {
    const idx = src('ui/index.js');
    expect(idx).toContain('KpiCardInline');
  });
});

describe('A2. Local KpiCard duplicates removed', () => {
  it('BacsOpsPanel uses KpiCardInline from ui', () => {
    const code = src('components/BacsOpsPanel.jsx');
    expect(code).toContain('KpiCardInline');
    expect(code).not.toMatch(/^function KpiCard/m);
  });

  it('SiteBillingMini uses KpiCardInline from ui', () => {
    const code = src('components/SiteBillingMini.jsx');
    expect(code).toContain('KpiCardInline');
    expect(code).not.toMatch(/^function KpiCard/m);
  });

  it('AnomaliesPage uses KpiCardInline from ui', () => {
    const code = src('pages/AnomaliesPage.jsx');
    expect(code).toContain('KpiCardInline');
    expect(code).not.toMatch(/^function KpiCard/m);
  });

  it('AperPage uses KpiCardInline from ui', () => {
    const code = src('pages/AperPage.jsx');
    expect(code).toContain('KpiCardInline');
    expect(code).not.toMatch(/^function KpiCard/m);
  });
});

// ── B. Performance page layout at 1280px ─────────────────────────────────

describe('B. Performance page layout', () => {
  const code = src('pages/MonitoringPage.jsx');

  it('executive summary uses xl:grid-cols-5', () => {
    expect(code).toMatch(/xl:grid-cols-5/);
  });

  it('KPI strip uses xl:grid-cols-4', () => {
    expect(code).toMatch(/xl:grid-cols-4/);
  });

  it('skeleton grid uses xl: breakpoint (not lg:)', () => {
    expect(code).toMatch(/xl:grid-cols-6 gap-3 mb-6/);
    expect(code).not.toMatch(/lg:grid-cols-6 gap-3 mb-6/);
  });

  it('CTA container uses flex-wrap to avoid overflow', () => {
    // The CTA div has flex-wrap and each button has the cta.label
    expect(code).toMatch(/gap-x-3 gap-y-1.*flex-wrap/);
    expect(code).toContain('cta.label');
  });

  it('CTA buttons use whitespace-nowrap', () => {
    expect(code).toContain('whitespace-nowrap');
    expect(code).toContain('cta.label');
  });
});

// ── C. French accent fixes ───────────────────────────────────────────────

describe('C. French accent correctness', () => {
  it('DevPanel: "enregistré" not "enregistre"', () => {
    const code = src('layout/DevPanel.jsx');
    expect(code).toContain('enregistré');
    expect(code).not.toMatch(/enregistre[^é]/);
  });

  it('DevPanel: "clé" not "cle"', () => {
    const code = src('layout/DevPanel.jsx');
    expect(code).toContain('clé');
  });

  it('DevPanel: "défini" not "defini"', () => {
    const code = src('layout/DevPanel.jsx');
    expect(code).toContain('défini');
  });

  it('EvidenceDrawer: "Méthode" not "Methode"', () => {
    const code = src('pages/consumption/EvidenceDrawer.jsx');
    expect(code).toContain('Méthode');
    expect(code).not.toMatch(/['"]Methode['"]/);
  });

  it('EvidenceDrawer: "créneau" not "creneau"', () => {
    const code = src('pages/consumption/EvidenceDrawer.jsx');
    expect(code).toContain('créneau');
  });

  it('PerformanceSnapshot: "Qualité" not "Qualite"', () => {
    const code = src('components/PerformanceSnapshot.jsx');
    expect(code).toMatch(/title="Qualité"/);
  });

  it('ConsoKpiHeader: "créneaux" not "creneaux"', () => {
    const code = src('components/ConsoKpiHeader.jsx');
    expect(code).toContain('créneaux');
  });

  it('ExportPackRFP: "électricité" not "electricite"', () => {
    const code = src('components/ExportPackRFP.jsx');
    expect(code).toContain('électricité');
    expect(code).not.toContain('electricite');
  });

  it('ExportPackRFP: "pondéré" and "économies"', () => {
    const code = src('components/ExportPackRFP.jsx');
    expect(code).toContain('pondéré');
    expect(code).toContain('économies');
  });

  it('scoring.js: "basée" and "données"', () => {
    const code = src('domain/purchase/scoring.js');
    expect(code).toContain('basée sur données');
  });
});

// ── D. NavPanel — always-open sections ───────────────────────────────────

describe('D. NavPanel always-open sections', () => {
  const code = src('layout/NavPanel.jsx');

  it('no ChevronDown import', () => {
    expect(code).not.toMatch(/ChevronDown/);
  });

  it('no useState for openSections', () => {
    expect(code).not.toMatch(/useState.*openSections/);
  });

  it('no toggleSection function', () => {
    expect(code).not.toMatch(/toggleSection/);
  });

  it('no aria-expanded on section headers', () => {
    expect(code).not.toMatch(/aria-expanded/);
  });

  it('SectionHeader is a static div (not button)', () => {
    expect(code).toMatch(/function SectionHeader[\s\S]*?<div className/);
  });
});
