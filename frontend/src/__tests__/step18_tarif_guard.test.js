/**
 * Step 18 — M2 : Référentiel TURPE/taxes YAML
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 18 — API function', () => {
  it('api.js exports getReferentielTarifs', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('getReferentielTarifs');
  });

  it('api.js calls /referentiel/tarifs', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('/referentiel/tarifs');
  });
});

describe('Step 18 — Glossary', () => {
  it('glossary.js has turpe long description', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('TURPE 7');
  });

  it('glossary.js has accise_electricite entry', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('accise_electricite');
  });

  it('glossary.js mentions TIEE', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('TIEE');
  });

  it('glossary.js mentions EUR/MWh for accise', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('EUR/MWh');
  });

  it('glossary.js mentions C5/C4/C3 segments', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('C5/C4/C3');
  });
});
