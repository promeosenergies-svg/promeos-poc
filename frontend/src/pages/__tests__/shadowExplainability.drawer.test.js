/**
 * shadowExplainability.drawer.test.js — Phase 2 ELEC Explainability
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 6 groups: A–F.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Contributeurs dans InsightDrawer ── */
describe('A. Top contributeurs — InsightDrawer', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('references top_contributors', () => {
    expect(drawer).toMatch(/top_contributors/);
  });

  it('has "Principaux contributeurs" heading', () => {
    expect(drawer).toMatch(/Principaux contributeurs/);
  });

  it('renders contributor delta_eur', () => {
    expect(drawer).toMatch(/delta_eur/);
  });

  it('renders contributor pct_of_total', () => {
    expect(drawer).toMatch(/pct_of_total/);
  });

  it('renders explanation_fr', () => {
    expect(drawer).toMatch(/explanation_fr/);
  });
});

/* ── B. Diagnostics dans InsightDrawer ── */
describe('B. Diagnostics — InsightDrawer', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('references diagnostics object', () => {
    expect(drawer).toMatch(/diagnostics/);
  });

  it('references confidence field', () => {
    expect(drawer).toMatch(/confidence/);
  });

  it('references missing_fields', () => {
    expect(drawer).toMatch(/missing_fields/);
  });

  it('has confidence badge labels (Élevée/Moyenne/Basse)', () => {
    expect(drawer).toMatch(/Élevée|élevée/);
    expect(drawer).toMatch(/Moyenne|moyenne/);
    expect(drawer).toMatch(/Basse|basse/);
  });
});

/* ── C. Hypothèses dans InsightDrawer ── */
describe('C. Hypothèses — InsightDrawer', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('references assumptions field', () => {
    expect(drawer).toMatch(/assumptions/);
  });

  it('has "Hypothèses" or "hypothèses" heading', () => {
    expect(drawer).toMatch(/[Hh]ypothèses/);
  });
});

/* ── D. Catalogue trace dans InsightDrawer (Expert) ── */
describe('D. Catalog trace — InsightDrawer Expert section', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('references catalog_trace', () => {
    expect(drawer).toMatch(/catalog_trace/);
  });

  it('references catalog_version', () => {
    expect(drawer).toMatch(/catalog_version/);
  });

  it('references price_source', () => {
    expect(drawer).toMatch(/price_source/);
  });
});

/* ── E. Dossier billing breakdown dans DossierPrintView ── */
describe('E. Dossier billing — DossierPrintView', () => {
  const dossier = src('src/components/DossierPrintView.jsx');

  it('accepts insightDetail prop', () => {
    expect(dossier).toMatch(/insightDetail/);
  });

  it('has "Analyse de l\'écart" section', () => {
    expect(dossier).toMatch(/Analyse de l'écart/);
  });

  it('shows expected_ttc / actual_ttc', () => {
    expect(dossier).toMatch(/expected_ttc/);
    expect(dossier).toMatch(/actual_ttc/);
  });

  it('references top_contributors in dossier', () => {
    expect(dossier).toMatch(/top_contributors/);
  });

  it('shows confidence in dossier', () => {
    expect(dossier).toMatch(/confidence/);
  });
});

/* ── F. BillIntelPage fetch insightDetail pour dossier ── */
describe('F. Dossier fetch — BillIntelPage', () => {
  const page = src('src/pages/BillIntelPage.jsx');

  it('imports getInsightDetail', () => {
    expect(page).toMatch(/getInsightDetail/);
  });

  it('has dossierInsightDetail state', () => {
    expect(page).toMatch(/dossierInsightDetail/);
  });

  it('passes insightDetail to DossierPrintView', () => {
    expect(page).toMatch(/insightDetail/);
  });
});
