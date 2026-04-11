/**
 * PROMEOS — useCommandCenterData — Source Guards + Structure Tests
 * Vérifie display-only, structure du hook, et enrichissement CommandCenter.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const hookPath = join(__dirname, '..', 'hooks', 'useCommandCenterData.js');
const hookSrc = readFileSync(hookPath, 'utf-8');
const ccPath = join(__dirname, '..', 'pages', 'CommandCenter.jsx');
const ccSrc = readFileSync(ccPath, 'utf-8');

// ── Hook Source Guards ───────────────────────────────────────────────

describe('useCommandCenterData — source guard (no-calc)', () => {
  it('ne contient pas de formule CO2 (* 0.0569)', () => {
    expect(hookSrc).not.toMatch(/\*\s*0\.0569/);
  });

  it('ne contient pas de formule risque (* 7500)', () => {
    expect(hookSrc).not.toMatch(/\*\s*7500/);
  });

  it('ne contient pas de conformiteScore', () => {
    expect(hookSrc).not.toMatch(/conformiteScore/);
  });
});

describe('useCommandCenterData — structure', () => {
  it('exporte useCommandCenterData', () => {
    expect(hookSrc).toMatch(/export function useCommandCenterData/);
  });

  it('importe getEmsTimeseries', () => {
    expect(hookSrc).toMatch(/getEmsTimeseries/);
  });

  it('importe useScope', () => {
    expect(hookSrc).toMatch(/useScope/);
  });

  it('expose weekSeries et hourlyProfile', () => {
    expect(hookSrc).toMatch(/weekSeries/);
    expect(hookSrc).toMatch(/hourlyProfile/);
  });

  it('expose kpisJ1 avec consoHierKwh et picKw', () => {
    expect(hookSrc).toMatch(/consoHierKwh/);
    expect(hookSrc).toMatch(/picKw/);
  });

  it('co2ResKgKwh reste null (pas de calcul)', () => {
    expect(hookSrc).toMatch(/co2ResKgKwh:\s*null/);
  });

  it('utilise Promise.all pour appels paralleles', () => {
    expect(hookSrc).toMatch(/Promise\.all/);
  });

  it('contient mountedRef guard', () => {
    expect(hookSrc).toMatch(/mountedRef/);
  });
});

// ── CommandCenter enrichissement ─────────────────────────────────────

describe('CommandCenter — enrichissement Step 5', () => {
  it('importe useCommandCenterData', () => {
    expect(ccSrc).toMatch(/useCommandCenterData/);
  });

  it('importe useCockpitData pour la trajectoire', () => {
    expect(ccSrc).toMatch(/useCockpitData/);
  });

  it('contient data-testid kpis-j1', () => {
    expect(ccSrc).toContain('data-testid="kpis-j1"');
  });

  it('contient data-testid charts-conso', () => {
    expect(ccSrc).toContain('data-testid="charts-conso"');
  });

  it('contient data-testid trajectoire-mensuelle', () => {
    expect(ccSrc).toContain('data-testid="trajectoire-mensuelle"');
  });

  it('conserve BriefingHeroCard (pas supprime)', () => {
    expect(ccSrc).toMatch(/BriefingHeroCard/);
  });

  it('conserve TodayActionsCard (pas supprime)', () => {
    expect(ccSrc).toMatch(/TodayActionsCard/);
  });

  it('conserve ModuleLaunchers (pas supprime)', () => {
    expect(ccSrc).toMatch(/ModuleLaunchers/);
  });

  it('utilise Recharts (ComposedChart)', () => {
    expect(ccSrc).toMatch(/ComposedChart/);
  });

  it('utilise fmtKwh pour les valeurs', () => {
    expect(ccSrc).toMatch(/fmtKwh/);
  });

  it('normalizeDashboardModel est toujours exporte', () => {
    expect(ccSrc).toMatch(/export function normalizeDashboardModel/);
  });
});
