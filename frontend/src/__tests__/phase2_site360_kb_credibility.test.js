/**
 * Phase 2 — KB crédibilité source guards.
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';

const SITE360 = fs.readFileSync('src/pages/Site360.jsx', 'utf-8');
const INTEL_PANEL = fs.readFileSync('src/components/SiteIntelligencePanel.jsx', 'utf-8');
const API_ENERGY = fs.readFileSync('src/services/api/energy.js', 'utf-8');

describe('Phase 2 — KB crédibilité', () => {
  test('Site360 ne contient plus le if/else reco hardcodé en JSX direct', () => {
    // "Déclarer vos consommations sur OPERAT" ne doit plus être dans du JSX direct
    // Il peut rester dans un fallback .catch()
    const lines = SITE360.split('\n');
    const _operatInJsx = lines.filter(
      (l) =>
        l.includes('OPERAT') &&
        !l.includes('catch') &&
        !l.includes('fallback') &&
        !l.includes('setTopReco') &&
        !l.includes("'") === false // must be in a string
    );
    // Le texte doit être dans un setTopReco fallback, pas dans du JSX ternaire
    expect(SITE360).not.toMatch(
      /\{site\.statut_conformite\s*===\s*'non_conforme'\s*\?\s*'Déclarer/
    );
  });

  test('Site360 appelle getTopRecommendation', () => {
    expect(SITE360).toMatch(/getTopRecommendation/);
  });

  test('Site360 affiche ICE score sur la reco principale', () => {
    expect(SITE360).toMatch(/ice_score/);
    expect(SITE360).toMatch(/ICE/);
  });

  test('Site360 affiche "Source : KB"', () => {
    expect(SITE360).toMatch(/Source\s*:\s*KB/);
  });

  test('getTopRecommendation is exported from API', () => {
    expect(API_ENERGY).toMatch(/export\s+const\s+getTopRecommendation/);
    expect(API_ENERGY).toMatch(/top-recommendation/);
  });

  test('SiteIntelligencePanel has deduplication via Map', () => {
    expect(INTEL_PANEL).toMatch(/new Map|seen\.has|seen\.set/);
  });

  test('SiteIntelligencePanel shows count for duplicates', () => {
    expect(INTEL_PANEL).toMatch(/r\.count\s*>/);
    expect(INTEL_PANEL).toMatch(/compteurs/);
  });

  test('SiteIntelligencePanel uses useMemo for dedup', () => {
    expect(INTEL_PANEL).toMatch(/useMemo/);
  });
});
