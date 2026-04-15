/**
 * Tests structurels EmissionFactorsContext (fix P0 #1-5 QA Guardian 2026-04-15).
 *
 * Vitest config = `environment: 'node'` (pas de DOM). Pour tester le provider
 * avec rendering React, il faudrait jsdom + update vite.config.js (hors scope).
 * Ici on teste : imports, fallback, doctrine, parité constants.js <> context.
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

import { CO2E_FACTOR_KG_PER_KWH } from '../../pages/consumption/constants';

const __dirname = dirname(fileURLToPath(import.meta.url));
const contextSrc = readFileSync(resolve(__dirname, '../EmissionFactorsContext.jsx'), 'utf8');

describe('EmissionFactorsContext — structure', () => {
  it('exporte Provider + 2 hooks', () => {
    expect(contextSrc).toContain('export function EmissionFactorsProvider');
    expect(contextSrc).toContain('export function useElecCo2Factor');
    expect(contextSrc).toContain('export function useEmissionFactors');
  });

  it('fetch /api/config/emission-factors au mount', () => {
    expect(contextSrc).toContain("fetch('/api/config/emission-factors')");
  });

  it('a un FALLBACK_FACTORS avec elec et gaz', () => {
    expect(contextSrc).toContain('FALLBACK_FACTORS');
    expect(contextSrc).toContain('elec:');
    expect(contextSrc).toContain('gaz:');
  });

  it('importe le constant depuis constants.js pour alignement', () => {
    expect(contextSrc).toContain(
      "import { CO2E_FACTOR_KG_PER_KWH } from '../pages/consumption/constants'"
    );
  });

  it('gère les erreurs fetch silencieusement avec fallback (pas de throw)', () => {
    expect(contextSrc).toContain('.catch(');
    expect(contextSrc).toContain('console.warn');
  });
});

describe('EmissionFactorsContext — doctrine CO₂', () => {
  it('fallback ELEC aligné sur constants.js (ADEME V23.6 = 0.052)', () => {
    expect(CO2E_FACTOR_KG_PER_KWH).toBe(0.052);
  });

  it('garde-fou : 0.0569 est un tarif TURPE HPH, pas un facteur CO₂', () => {
    // Le fallback ne doit JAMAIS contenir cette valeur.
    expect(CO2E_FACTOR_KG_PER_KWH).not.toBe(0.0569);
    expect(contextSrc).not.toContain('0.0569');
  });

  it('fallback gaz = 0.227 ADEME (combustion + amont, PCI)', () => {
    // Valeur hardcodée dans le fallback du context, doit matcher emission_factors.py
    expect(contextSrc).toContain('0.227');
  });
});

describe('EmissionFactorsContext — read-only exposition', () => {
  it("n'expose aucun setter depuis le Context.Provider value", () => {
    // Garde-fou : le useState setter reste interne au Provider. Le `value=`
    // passé au Provider ne doit contenir que les champs read-only.
    const providerValueMatch = contextSrc.match(
      /EmissionFactorsContext\.Provider[\s\S]*?value=\{([^}]+)\}/
    );
    expect(providerValueMatch).not.toBeNull();
    const valueBlock = providerValueMatch[1];
    // Le value block expose factors, sourceVersion, loading, error — pas de setter.
    expect(valueBlock).not.toContain('setFactors');
    expect(valueBlock).not.toContain('setSourceVersion');
    expect(valueBlock).toContain('factors');
    expect(valueBlock).toContain('sourceVersion');
  });
});
