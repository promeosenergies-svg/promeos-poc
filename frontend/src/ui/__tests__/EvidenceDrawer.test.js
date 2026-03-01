/**
 * PROMEOS — EvidenceDrawer V0 source-guard tests
 * Validates:
 *   1) Evidence model exports (CONFIDENCE_CFG, SOURCE_KIND, buildEvidence)
 *   2) EvidenceDrawer component structure (Drawer, sections, a11y)
 *   3) Evidence fixtures (4 factory functions)
 *   4) Barrel export in ui/index.js
 *   5) Cockpit integration (ExecutiveKpiRow + Cockpit.jsx)
 *   6) Explorer integration (ConsoKpiHeader + ConsumptionExplorerPage.jsx)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const readSrc = (relPath) =>
  readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

// ── 1) Evidence model ──────────────────────────────────────────────────────
describe('Evidence model (ui/evidence.js)', () => {
  const src = readSrc('ui/evidence.js');

  it('exports CONFIDENCE_CFG with high/medium/low', () => {
    expect(src).toContain('export const CONFIDENCE_CFG');
    expect(src).toContain('high:');
    expect(src).toContain('medium:');
    expect(src).toContain('low:');
  });

  it('exports SOURCE_KIND with 4 kinds', () => {
    expect(src).toContain('export const SOURCE_KIND');
    expect(src).toContain('enedis:');
    expect(src).toContain('invoice:');
    expect(src).toContain('manual:');
    expect(src).toContain('calc:');
  });

  it('exports buildEvidence factory function', () => {
    expect(src).toContain('export function buildEvidence');
  });

  it('defines Evidence JSDoc typedef', () => {
    expect(src).toContain('@typedef');
    expect(src).toContain('Evidence');
  });
});

// ── 2) EvidenceDrawer component ────────────────────────────────────────────
describe('EvidenceDrawer component (ui/EvidenceDrawer.jsx)', () => {
  const src = readSrc('ui/EvidenceDrawer.jsx');

  it('uses reusable Drawer from ui/', () => {
    expect(src).toContain("import Drawer from './Drawer'");
  });

  it('renders Sources section', () => {
    expect(src).toContain('Sources');
    expect(src).toContain('SourceCard');
  });

  it('renders Méthode de calcul section', () => {
    expect(src).toContain('thode de calcul');
  });

  it('renders Hypothèses section', () => {
    expect(src).toContain('Hypoth');
  });

  it('has ConfidencePill sub-component', () => {
    expect(src).toContain('ConfidencePill');
    expect(src).toContain('CONFIDENCE_CFG');
  });

  it('renders navigation links with aria-label', () => {
    expect(src).toContain('aria-label');
    expect(src).toContain('navigate(link.href)');
  });

  it('renders last computed timestamp', () => {
    expect(src).toContain('lastComputedAt');
    expect(src).toContain('Dernier calcul');
  });

  it('has props: open, onClose, evidence', () => {
    expect(src).toContain('open');
    expect(src).toContain('onClose');
    expect(src).toContain('evidence');
  });
});

// ── 3) Evidence fixtures ───────────────────────────────────────────────────
describe('Evidence fixtures (ui/evidence.fixtures.js)', () => {
  const src = readSrc('ui/evidence.fixtures.js');

  it('exports evidenceConformite factory', () => {
    expect(src).toContain('export function evidenceConformite');
  });

  it('exports evidenceRisque factory', () => {
    expect(src).toContain('export function evidenceRisque');
  });

  it('exports evidenceKwhTotal factory', () => {
    expect(src).toContain('export function evidenceKwhTotal');
  });

  it('exports evidenceCO2e factory', () => {
    expect(src).toContain('export function evidenceCO2e');
  });

  it('uses buildEvidence from evidence model', () => {
    expect(src).toContain("import { buildEvidence } from './evidence'");
  });
});

// ── 4) Barrel export ───────────────────────────────────────────────────────
describe('EvidenceDrawer barrel export', () => {
  const src = readSrc('ui/index.js');

  it('exports EvidenceDrawer from ui/index.js', () => {
    expect(src).toContain('EvidenceDrawer');
    expect(src).toContain("'./EvidenceDrawer'");
  });
});

// ── 5) Cockpit integration ─────────────────────────────────────────────────
describe('Cockpit EvidenceDrawer integration', () => {
  const kpiRowSrc = readSrc('pages/cockpit/ExecutiveKpiRow.jsx');
  const cockpitSrc = readSrc('pages/Cockpit.jsx');

  it('ExecutiveKpiRow has evidence-open data-testid', () => {
    expect(kpiRowSrc).toContain('data-testid');
    expect(kpiRowSrc).toContain('evidence-open-');
  });

  it('ExecutiveKpiRow has HelpCircle icon', () => {
    expect(kpiRowSrc).toContain('HelpCircle');
  });

  it('ExecutiveKpiRow accepts onEvidence prop', () => {
    expect(kpiRowSrc).toContain('onEvidence');
  });

  it('ExecutiveKpiRow defines EVIDENCE_KPIS set', () => {
    expect(kpiRowSrc).toContain('EVIDENCE_KPIS');
    expect(kpiRowSrc).toContain('conformite');
    expect(kpiRowSrc).toContain('risque');
  });

  it('Cockpit.jsx imports EvidenceDrawer', () => {
    expect(cockpitSrc).toContain('EvidenceDrawer');
  });

  it('Cockpit.jsx imports evidence fixtures', () => {
    expect(cockpitSrc).toContain('evidenceConformite');
    expect(cockpitSrc).toContain('evidenceRisque');
  });

  it('Cockpit.jsx renders EvidenceDrawer with evidenceOpen state', () => {
    expect(cockpitSrc).toContain('evidenceOpen');
    expect(cockpitSrc).toContain('evidenceMap');
  });

  it('Cockpit.jsx has Pourquoi ce chiffre aria-label', () => {
    expect(kpiRowSrc).toContain('Pourquoi ce chiffre');
  });
});

// ── 6) Explorer integration ────────────────────────────────────────────────
describe('ConsumptionExplorer EvidenceDrawer integration', () => {
  const headerSrc = readSrc('components/ConsoKpiHeader.jsx');
  const explorerSrc = readSrc('pages/ConsumptionExplorerPage.jsx');

  it('ConsoKpiHeader accepts onEvidence prop', () => {
    expect(headerSrc).toContain('onEvidence');
  });

  it('ConsoKpiHeader passes evidenceId for kWh and CO2e tiles', () => {
    expect(headerSrc).toContain('evidenceId="conso-kwh-total"');
    expect(headerSrc).toContain('evidenceId="conso-co2e"');
  });

  it('ConsoKpiHeader has Pourquoi ce chiffre aria-label', () => {
    expect(headerSrc).toContain('Pourquoi ce chiffre');
  });

  it('Explorer imports GenericEvidenceDrawer', () => {
    expect(explorerSrc).toContain('GenericEvidenceDrawer');
  });

  it('Explorer imports evidence fixtures', () => {
    expect(explorerSrc).toContain('evidenceKwhTotal');
    expect(explorerSrc).toContain('evidenceCO2e');
  });

  it('Explorer renders GenericEvidenceDrawer', () => {
    expect(explorerSrc).toContain('<GenericEvidenceDrawer');
    expect(explorerSrc).toContain('evidenceKpiOpen');
    expect(explorerSrc).toContain('consoEvidenceMap');
  });
});
