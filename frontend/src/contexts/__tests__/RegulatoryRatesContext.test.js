/**
 * Tests structurels RegulatoryRatesContext (Sprint C-3 Phase 3.3).
 *
 * Vitest config = `environment: 'node'` (pas de DOM, pas de @testing-library/react).
 * Pattern aligné avec EmissionFactorsContext.test.js (Phase 4.4 Sprint C-2) :
 * tests structurels via readFileSync + regex sur le source du module.
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const contextSrc = readFileSync(resolve(__dirname, '../RegulatoryRatesContext.jsx'), 'utf8');

describe('RegulatoryRatesContext — structure', () => {
  it('exports Provider + 2 hooks (useRegulatoryRates + useRegulatorySource)', () => {
    expect(contextSrc).toContain('export function RegulatoryRatesProvider');
    expect(contextSrc).toContain('export function useRegulatoryRates');
    expect(contextSrc).toContain('export function useRegulatorySource');
  });

  it('fetch /api/regulatory/rates au mount du Provider', () => {
    expect(contextSrc).toContain("fetch('/api/regulatory/rates')");
  });

  it('cache module-level partagé (évite N fetches simultanés)', () => {
    // Cache module-level : variables hors composant React
    expect(contextSrc).toMatch(/let\s+_ratesCache\s*=\s*null/);
    expect(contextSrc).toMatch(/let\s+_fetchPromise\s*=\s*null/);
  });

  it('reset cache helper exporté pour tests', () => {
    expect(contextSrc).toContain('export function resetRegulatoryRatesCache');
  });

  it('gère les erreurs fetch silencieusement avec fallback (pas de throw render)', () => {
    expect(contextSrc).toContain('.catch(');
    expect(contextSrc).toContain('console.warn');
    // Hors Provider : retourne fallback safe
    expect(contextSrc).toMatch(/rates:\s*null/);
  });
});

describe('RegulatoryRatesContext — hooks API', () => {
  it('useRegulatorySource(termId) retourne null si rates non chargé', () => {
    // Pattern explicite : if (loading || error || !rates?.terms || !termId) return null
    expect(contextSrc).toMatch(/loading\s*\|\|\s*error\s*\|\|\s*!rates\?\.terms/);
  });

  it('useRegulatoryRates fallback safe hors Provider', () => {
    // if (!ctx) return { rates: null, loading: false, error: null };
    expect(contextSrc).toMatch(/if\s*\(!ctx\)/);
    expect(contextSrc).toMatch(/loading:\s*false/);
  });
});

describe('RegulatoryRatesContext — App wiring', () => {
  it('Provider wrappé dans App.jsx', () => {
    const appSrc = readFileSync(resolve(__dirname, '../../App.jsx'), 'utf8');
    expect(appSrc).toContain('RegulatoryRatesProvider');
    expect(appSrc).toContain("from './contexts/RegulatoryRatesContext'");
  });
});
