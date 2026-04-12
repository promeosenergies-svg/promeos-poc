/**
 * PROMEOS - Tests Sirene Onboarding
 * Structure guards : verifie que la page et l'API service existent et sont correctement cables.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..');

describe('SireneOnboardingPage — structure', () => {
  const pagePath = resolve(SRC, 'pages/SireneOnboardingPage.jsx');

  it('le fichier page existe', () => {
    expect(existsSync(pagePath)).toBe(true);
  });

  it('contient les 3 etapes (search, select, confirm)', () => {
    const src = readFileSync(pagePath, 'utf-8');
    expect(src).toContain("id: 'search'");
    expect(src).toContain("id: 'select'");
    expect(src).toContain("id: 'confirm'");
  });

  it('importe les fonctions API sirene', () => {
    const src = readFileSync(pagePath, 'utf-8');
    expect(src).toMatch(/import.*searchSirene/);
    expect(src).toMatch(/import.*getEtablissements/);
    expect(src).toMatch(/import.*createClientFromSirene/);
  });

  it('ne cree PAS de batiment ni compteur', () => {
    const src = readFileSync(pagePath, 'utf-8');
    expect(src).not.toMatch(/createBatiment|create_batiment|provision_site/i);
    expect(src).not.toMatch(/createCompteur|create_compteur/i);
  });

  it('affiche les micro-copy appropriees', () => {
    const src = readFileSync(pagePath, 'utf-8');
    expect(src).toContain('batiments, compteurs et contrats');
    expect(src).toContain('Sirene officielle');
  });
});

describe('API Sirene service — structure', () => {
  const apiPath = resolve(SRC, 'services/api/sirene.js');

  it('le fichier API existe', () => {
    expect(existsSync(apiPath)).toBe(true);
  });

  it('exporte les fonctions attendues', () => {
    const src = readFileSync(apiPath, 'utf-8');
    expect(src).toContain('export const searchSirene');
    expect(src).toContain('export const getUniteLegale');
    expect(src).toContain('export const getEtablissements');
    expect(src).toContain('export const getEtablissement');
    expect(src).toContain('export const createClientFromSirene');
    expect(src).toContain('export const importSireneFull');
    expect(src).toContain('export const importSireneDelta');
  });

  it('utilise les bons endpoints', () => {
    const src = readFileSync(apiPath, 'utf-8');
    expect(src).toContain('/reference/sirene/search');
    expect(src).toContain('/reference/sirene/unites-legales/');
    expect(src).toContain('/reference/sirene/etablissements/');
    expect(src).toContain('/onboarding/from-sirene');
    expect(src).toContain('/admin/sirene/import-full');
    expect(src).toContain('/admin/sirene/import-delta');
  });
});

describe('App.jsx — route sirene', () => {
  const appPath = resolve(SRC, 'App.jsx');

  it('contient la route /onboarding/sirene', () => {
    const src = readFileSync(appPath, 'utf-8');
    expect(src).toContain('/onboarding/sirene');
    expect(src).toContain('SireneOnboardingPage');
  });
});
