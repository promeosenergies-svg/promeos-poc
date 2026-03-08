/**
 * Step 20 — O5 : Import multi-entité dans le template
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 20 — Import mapping columns', () => {
  const src = fs.readFileSync('../backend/services/import_mapping.py', 'utf8');

  it('import_mapping.py has siren_entite column', () => {
    expect(src).toContain('siren_entite');
  });

  it('import_mapping.py has nom_entite column', () => {
    expect(src).toContain('nom_entite');
  });

  it('import_mapping.py has portefeuille column', () => {
    expect(src).toContain('"portefeuille"');
  });

  it('import_mapping.py has batiment_nom column', () => {
    expect(src).toContain('batiment_nom');
  });

  it('import_mapping.py has batiment_surface_m2 column', () => {
    expect(src).toContain('batiment_surface_m2');
  });

  it('import_mapping.py has building_name synonym', () => {
    expect(src).toContain('building_name');
  });

  it('import_mapping.py has entity_siren synonym', () => {
    expect(src).toContain('entity_siren');
  });
});

describe('Step 20 — Staging model', () => {
  const src = fs.readFileSync('../backend/models/patrimoine.py', 'utf8');

  it('staging model has siren_entite column', () => {
    expect(src).toContain('siren_entite');
  });

  it('staging model has portefeuille_nom column', () => {
    expect(src).toContain('portefeuille_nom');
  });

  it('staging model has batiment_nom column', () => {
    expect(src).toContain('batiment_nom');
  });
});

describe('Step 20 — Quality rules', () => {
  const src = fs.readFileSync('../backend/services/quality_rules.py', 'utf8');

  it('quality_rules has invalid_siren_entite rule', () => {
    expect(src).toContain('invalid_siren_entite');
  });

  it('quality_rules has orphan_portefeuille rule', () => {
    expect(src).toContain('orphan_portefeuille');
  });

  it('quality_rules has batiment_sans_surface rule', () => {
    expect(src).toContain('batiment_sans_surface');
  });
});
