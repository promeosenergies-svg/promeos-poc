/**
 * Tests structurels RegulatoryConstantsContext (Phase L29.3 — anti-régression pilot).
 *
 * Vitest config = `environment: 'node'` (pas de DOM, pas de @testing-library/react).
 * Pattern aligné EmissionFactorsContext.test.js + RegulatoryRatesContext.test.js.
 *
 * Cible : pilot-readiness pré-prod externe Marie DAF / Jean-Marc CFO — le frontend
 * ne doit jamais afficher de seuil obsolète si décret modifie YAML backend.
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const contextSrc = readFileSync(resolve(__dirname, '../RegulatoryConstantsContext.jsx'), 'utf8');

describe('RegulatoryConstantsContext — structure', () => {
  it('exports Provider + hook useRegulatoryConstants', () => {
    expect(contextSrc).toContain('export function RegulatoryConstantsProvider');
    expect(contextSrc).toContain('export function useRegulatoryConstants');
  });

  it('fetch /api/config/regulatory-constants au mount du Provider', () => {
    expect(contextSrc).toContain("fetch('/api/config/regulatory-constants')");
  });

  it('gère les erreurs fetch silencieusement avec fallback', () => {
    expect(contextSrc).toContain('.catch(');
    expect(contextSrc).toContain('console.warn');
    expect(contextSrc).toContain('FALLBACK_CONSTANTS');
  });

  it('hors Provider : retourne FALLBACK_CONSTANTS au lieu de crasher', () => {
    expect(contextSrc).toMatch(/constants:\s*FALLBACK_CONSTANTS/);
  });
});

describe('RegulatoryConstantsContext — FALLBACK_CONSTANTS complet (Phase L29.3)', () => {
  it('FALLBACK_CONSTANTS contient les 4 dicts historiques (vnu/aper/turpe7_hc/operat)', () => {
    expect(contextSrc).toMatch(/vnu:\s*\{/);
    expect(contextSrc).toMatch(/aper:\s*\{/);
    expect(contextSrc).toMatch(/turpe7_hc:\s*\{/);
    expect(contextSrc).toMatch(/operat:\s*\{/);
  });

  it('FALLBACK_CONSTANTS contient les 3 nouveaux dicts L28.1a (dt/primary_energy/readiness_weights)', () => {
    // Anti-régression Phase L29.3 : sans ces dicts, un consumer accédant à
    // constants.dt.penalty_eur recevrait undefined si l'API échoue.
    expect(contextSrc).toMatch(/dt:\s*\{[\s\S]*penalty_eur:\s*7500/);
    expect(contextSrc).toMatch(/primary_energy:\s*\{[\s\S]*coef_elec:\s*1\.9/);
    expect(contextSrc).toMatch(/readiness_weights:\s*\{[\s\S]*data:\s*0\.3/);
  });

  it('FALLBACK_CONSTANTS.vnu contient tarif_unitaire_2026_eur_mwh (champ enrichi L28.1a)', () => {
    expect(contextSrc).toMatch(/tarif_unitaire_2026_eur_mwh:\s*0\.0/);
  });

  it('FALLBACK_CONSTANTS.aper contient surface_large_m2 et solar_ratio_pct (champs enrichis L28.1a)', () => {
    expect(contextSrc).toMatch(/surface_large_m2:\s*10000/);
    expect(contextSrc).toMatch(/solar_ratio_pct:\s*50\.0/);
  });

  it('FALLBACK_CONSTANTS.dt aligne sur SoT doctrine.constants (DT_PENALTY_EUR=7500, DT_PENALTY_AT_RISK=3750)', () => {
    expect(contextSrc).toMatch(/penalty_eur:\s*7500/);
    expect(contextSrc).toMatch(/penalty_at_risk_eur:\s*3750/);
  });

  it('FALLBACK_CONSTANTS.readiness_weights somme 1.0 (data 0.3 + conformity 0.4 + actions 0.3)', () => {
    expect(contextSrc).toMatch(/readiness_weights:\s*\{[\s\S]*data:\s*0\.3/);
    expect(contextSrc).toMatch(/readiness_weights:\s*\{[\s\S]*conformity:\s*0\.4/);
    expect(contextSrc).toMatch(/readiness_weights:\s*\{[\s\S]*actions:\s*0\.3/);
  });
});

describe('RegulatoryConstantsContext — merge backend (Phase L29.3)', () => {
  it('merge data.vnu en utilisant FALLBACK_CONSTANTS.vnu comme defaults', () => {
    // Pattern : merged.vnu = { ...FALLBACK_CONSTANTS.vnu, ...data.vnu }
    expect(contextSrc).toMatch(/merged\.vnu\s*=\s*\{\s*\.\.\.FALLBACK_CONSTANTS\.vnu/);
  });

  it('merge data.dt (Phase L29.3 nouveau merge)', () => {
    expect(contextSrc).toMatch(/merged\.dt\s*=\s*\{\s*\.\.\.FALLBACK_CONSTANTS\.dt/);
  });

  it('merge data.primary_energy (Phase L29.3 nouveau merge)', () => {
    expect(contextSrc).toMatch(
      /merged\.primary_energy\s*=\s*\{[\s\S]*FALLBACK_CONSTANTS\.primary_energy/
    );
  });

  it('merge data.readiness_weights (Phase L29.3 nouveau merge)', () => {
    expect(contextSrc).toMatch(
      /merged\.readiness_weights\s*=\s*\{[\s\S]*FALLBACK_CONSTANTS\.readiness_weights/
    );
  });

  it('ignore la clé doctrine du backend (présente uniquement comme métadata)', () => {
    expect(contextSrc).toContain('// Merge backend data sur les clés connues');
    // Pas de merge merged.doctrine = ...
    expect(contextSrc).not.toMatch(/merged\.doctrine\s*=/);
  });
});
