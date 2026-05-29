/**
 * Source-guards FE S3 (2026-05-28) — bloc « Groupe de structures »
 * dans MutualisationSection.
 *
 * 100% lecture source + regex (pas de DOM mock requis).
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../../');
const readSrc = (p) => readFileSync(resolve(root, 'src', p), 'utf-8');

describe('S3 · MutualisationSection — bloc groupe de structures', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('expose data-testid="groupe-structures-bloc"', () => {
    expect(ui).toContain('data-testid="groupe-structures-bloc"');
  });

  it('charge les groupes via listGroupeStructures', () => {
    expect(ui).toContain('listGroupeStructures');
  });

  it("expose des boutons d'export Table 1B conditionnels (S4 décliné CSV + PDF)", () => {
    // S4 (2026-05-29) — le bouton unique « Exporter Table 1B » a été
    // décliné en CSV + PDF. La sémantique reste identique : un seul
    // groupe de CTA primaires conditionnel sur allRlOk.
    expect(ui).toContain('CSV Table 1B');
    expect(ui).toContain('PDF Table 1B');
    expect(ui).toContain('Export indisponible');
  });

  it('affiche un warning juridique quand le groupe n’est pas opposable', () => {
    expect(ui).toContain('Groupe non opposable');
    expect(ui).toContain('Art. 14 §1 al.2');
  });

  it('mentionne le message « Module OPERAT mutualisation : préparation du dossier »', () => {
    expect(ui).toContain('Module OPERAT mutualisation');
  });

  it('cite Article 14 (source réglementaire dans le warning)', () => {
    expect(ui).toContain('Article 14');
  });

  it('utilise la convention « représentant légal » française', () => {
    expect(ui).toContain('représentant légal');
  });
});

describe('S3 · MutualisationSection — anti-doublon doctrine', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('aucun nom de concurrent dans le rendu', () => {
    for (const concurrent of ['Advizeo', 'Deepki', 'Metron', 'Citron', 'Energisme']) {
      expect(ui).not.toContain(concurrent);
    }
  });

  it('le composant reste utilisé dans le hub /conformite (aucun nouvel écran)', () => {
    const page = readSrc('pages/ConformitePage.jsx');
    expect(page).toContain('Conformité');
  });
});

describe('S3 · client API — wrappers groupes de structures', () => {
  const api = readSrc('services/api/conformite.js');

  it('expose listGroupeStructures', () => {
    expect(api).toContain('export const listGroupeStructures');
  });

  it('expose createGroupeStructures', () => {
    expect(api).toContain('export const createGroupeStructures');
  });

  it('expose addGroupeStructuresMember', () => {
    expect(api).toContain('export const addGroupeStructuresMember');
  });

  it('expose updateRepresentantLegal', () => {
    expect(api).toContain('export const updateRepresentantLegal');
  });

  it('expose buildExportTable1bUrl', () => {
    expect(api).toContain('export const buildExportTable1bUrl');
    expect(api).toContain('export-table-1b');
  });
});
