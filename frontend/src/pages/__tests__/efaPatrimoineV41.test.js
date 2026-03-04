/**
 * PROMEOS V41 — EFA Wizard lié au Patrimoine (zéro duplication)
 * Source guards : building picker, no manual surface, catalog API, buildings in payload
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. Wizard uses Patrimoine buildings
// ══════════════════════════════════════════════════════════════════════════════

describe('Wizard uses Patrimoine buildings (V41)', () => {
  const wizard = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('imports getTertiaireCatalog', () => {
    expect(wizard).toContain('getTertiaireCatalog');
  });

  it('no longer has manual surface_m2 input field', () => {
    expect(wizard).not.toContain("updateField('surface_m2'");
  });

  it('has selectedBuildings in form state', () => {
    expect(wizard).toContain('selectedBuildings');
  });

  it('passes buildings array to createTertiaireEfa', () => {
    expect(wizard).toContain('buildings:');
    expect(wizard).toContain('building_id:');
  });

  it('no longer imports addTertiaireBuilding', () => {
    expect(wizard).not.toContain('addTertiaireBuilding');
  });

  it('shows empty patrimoine banner with CTA', () => {
    expect(wizard).toContain('Aucun bâtiment dans le patrimoine');
    expect(wizard).toContain('Compléter le patrimoine');
  });

  it('shows read-only surface total', () => {
    expect(wizard).toContain('Surface totale');
  });

  it('shows Usage OPERAT select per building', () => {
    expect(wizard).toContain('Usage OPERAT');
    expect(wizard).toContain('usage_label');
  });

  it('preserves error display (regression guard)', () => {
    expect(wizard).toContain('data-testid="wizard-submit-error"');
    expect(wizard).toContain("Impossible de créer l'EFA");
  });

  it('preserves loading state (regression guard)', () => {
    expect(wizard).toContain('disabled={saving}');
    expect(wizard).toContain('Création…');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. API module exports getTertiaireCatalog
// ══════════════════════════════════════════════════════════════════════════════

describe('API module exports getTertiaireCatalog (V41)', () => {
  const api = src('services/api.js');

  it('exports getTertiaireCatalog function', () => {
    expect(api).toContain('getTertiaireCatalog');
  });

  it('calls /catalog endpoint', () => {
    expect(api).toContain('/catalog');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Backend guards — schema + validation
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend EfaCreate accepts buildings (V41)', () => {
  const code = backendSrc('routes/tertiaire.py');

  it('EfaCreate schema has buildings field', () => {
    expect(code).toContain('BuildingWithUsage');
  });

  it('create_efa validates building existence', () => {
    expect(code).toContain('introuvable');
  });

  it('create_efa snapshots surface_m2 from Batiment', () => {
    expect(code).toContain('bat.surface_m2');
  });

  it('catalog endpoint exists', () => {
    expect(code).toContain('def building_catalog');
  });

  it('imports Site and Batiment models', () => {
    expect(code).toContain('Site');
    expect(code).toContain('Batiment');
  });
});
