/**
 * PROMEOS — useCockpitData hook — Source Guards + Structure Tests
 * Vérifie que le hook est display-only (aucun calcul métier) et exporte la shape attendue.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const hookPath = join(__dirname, '..', 'hooks', 'useCockpitData.js');
const hookSrc = readFileSync(hookPath, 'utf-8');

describe('useCockpitData — source guard (no-calc-in-hook)', () => {
  it('ne contient aucun calcul de pourcentage (/ total * 100)', () => {
    expect(hookSrc).not.toMatch(/\/\s*total\s*\*\s*100/);
  });

  it('ne contient aucun calcul de reduction (1 - x/y * 100)', () => {
    expect(hookSrc).not.toMatch(/1\s*-\s*.*\/\s*.*\)\s*\*\s*100/);
  });

  it('ne contient pas de Math.round( pour calcul metier', () => {
    expect(hookSrc).not.toMatch(/Math\.round\(/);
  });

  it('ne contient pas de formule de risque financier hardcodee', () => {
    expect(hookSrc).not.toMatch(/\*\s*7500/);
    expect(hookSrc).not.toMatch(/\*\s*3750/);
  });

  it('ne contient pas compliance_score = calcul', () => {
    expect(hookSrc).not.toMatch(/compliance_score\s*=\s*Math/);
    expect(hookSrc).not.toMatch(/conformiteScore\s*=\s*[^s]/);
  });
});

describe('useCockpitData — structure exports', () => {
  it('exporte useCockpitData comme named export', () => {
    expect(hookSrc).toMatch(/export function useCockpitData/);
  });

  it('importe useScope depuis ScopeContext', () => {
    expect(hookSrc).toMatch(/import.*useScope.*from.*ScopeContext/);
  });

  it('importe logger', () => {
    expect(hookSrc).toMatch(/import.*logger.*from.*logger/);
  });

  it('importe les 4 wrappers API', () => {
    expect(hookSrc).toMatch(/getCockpit/);
    expect(hookSrc).toMatch(/getCockpitTrajectory/);
    expect(hookSrc).toMatch(/getActionsSummary/);
    expect(hookSrc).toMatch(/getBillingSummary/);
  });

  it('utilise Promise.all pour appels paralleles', () => {
    expect(hookSrc).toMatch(/Promise\.all/);
  });

  it('contient mountedRef guard', () => {
    expect(hookSrc).toMatch(/mountedRef/);
  });
});

describe('useCockpitData — normalize functions display-only', () => {
  it('normalizeCockpitKpis expose les champs P0', () => {
    expect(hookSrc).toMatch(/conformiteScore/);
    expect(hookSrc).toMatch(/conformiteSource/);
    expect(hookSrc).toMatch(/conformiteComputedAt/);
    expect(hookSrc).toMatch(/risqueTotal/);
    expect(hookSrc).toMatch(/risqueBreakdown/);
  });

  it('normalizeTrajectory expose les champs trajectoire', () => {
    expect(hookSrc).toMatch(/refYear/);
    expect(hookSrc).toMatch(/reductionPctActuelle/);
    expect(hookSrc).toMatch(/objectifMwh/);
    expect(hookSrc).toMatch(/jalons/);
  });

  it('normalizeActions expose total/enCours/urgentes', () => {
    expect(hookSrc).toMatch(/enCours/);
    expect(hookSrc).toMatch(/urgentes/);
    expect(hookSrc).toMatch(/potentielEur/);
  });

  it('normalizeBilling expose anomalies/montantEur', () => {
    expect(hookSrc).toMatch(/anomalies/);
    expect(hookSrc).toMatch(/montantEur/);
  });
});

describe('useCockpitData — return shape', () => {
  it('retourne kpis, trajectoire, actions, billing, loading, error, lastFetchedAt, refetch', () => {
    const requiredFields = [
      'kpis',
      'trajectoire',
      'actions',
      'billing',
      'loading',
      'error',
      'lastFetchedAt',
      'refetch',
    ];
    for (const field of requiredFields) {
      expect(hookSrc).toContain(field);
    }
  });

  it('expose refetch comme fetchAll', () => {
    expect(hookSrc).toMatch(/refetch:\s*fetchAll/);
  });
});
