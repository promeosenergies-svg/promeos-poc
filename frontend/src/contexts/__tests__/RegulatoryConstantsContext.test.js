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

  it('FALLBACK_CONSTANTS.aper deadline_iso aligné SoT doctrine APER_DEADLINE_SMALL=2028-07-01 (Phase L30.1 fix drift)', () => {
    // Phase L30.1 audit fix P1 — anti-régression : la deadline FE ne doit jamais
    // diverger de doctrine.constants.APER_DEADLINE_SMALL_PARKING_DATE (2028-07-01).
    expect(contextSrc).toContain("deadline_iso: '2028-07-01'");
    // deadline_large_iso pour parkings >10000 m² (IMMINENT — APER_DEADLINE_LARGE)
    expect(contextSrc).toContain("deadline_large_iso: '2026-07-01'");
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

describe('RegulatoryConstantsContext — merge backend (Phase L29.3 → L33.4 generic)', () => {
  it('merge générique Object.fromEntries itère sur FALLBACK_CONSTANTS (Phase L33.4)', () => {
    // Phase L33.4 — refactor 8 if/merge → boucle générique. Anti-régression
    // ouverture future : ajouter une nouvelle clé dans FALLBACK_CONSTANTS
    // suffit, pas besoin d'ajouter un if dédié.
    expect(contextSrc).toContain('Object.fromEntries');
    expect(contextSrc).toContain('Object.entries(FALLBACK_CONSTANTS)');
  });

  it('merge utilise FALLBACK_CONSTANTS comme defaults pour chaque clé', () => {
    // Pattern : data?.[key] ? { ...fallback, ...data[key] } : fallback
    expect(contextSrc).toMatch(/data\?\.\[key\]/);
    expect(contextSrc).toMatch(/\{\s*\.\.\.fallback,\s*\.\.\.data\[key\]\s*\}/);
  });

  it('ignore la clé doctrine du backend (non présente dans FALLBACK_CONSTANTS donc filtrée)', () => {
    // Phase L33.4 — refactor merge générique Object.fromEntries itère sur
    // FALLBACK_CONSTANTS donc la clé "doctrine" du backend (string narrative)
    // est automatiquement ignorée car non listée dans FALLBACK_CONSTANTS.
    expect(contextSrc).not.toMatch(/merged\.doctrine\s*=/);
    expect(contextSrc).not.toMatch(/FALLBACK_CONSTANTS\.doctrine/);
  });
});
