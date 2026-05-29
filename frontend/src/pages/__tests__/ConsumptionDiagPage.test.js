/**
 * PROMEOS — Tests for ConsumptionDiagPage helpers
 * Covers: recalcLosses
 *
 * Sprint Énergie P0.S1b (2026-05-29) — tests `generateComparisonChart`
 * supprimés : la fonction a été retirée (générait des données
 * sinusoïdales synthétiques côté frontend, violation doctrine
 * « zéro calcul métier frontend »). Le chart Evidence est remplacé
 * par un placeholder. Migration vers endpoint
 * /api/diagnostic-conso/insights/{id}/profile_24h planifiée P1.S3.
 */
import { describe, it, expect } from 'vitest';
import { recalcLosses } from '../ConsumptionDiagPage';

describe('recalcLosses', () => {
  it('multiplies kWh by custom price', () => {
    expect(recalcLosses(1000, 0.2)).toBe(200);
  });

  it('uses default price when customPrice is null', () => {
    expect(recalcLosses(1000, null)).toBe(150);
  });

  it('returns 0 for null kWh', () => {
    expect(recalcLosses(null, 0.15)).toBe(0);
  });

  it('uses custom default price', () => {
    expect(recalcLosses(1000, null, 0.1)).toBe(100);
  });

  it('rounds to integer', () => {
    expect(recalcLosses(333, 0.157)).toBe(Math.round(333 * 0.157));
  });
});

describe('V9 CO2e: ConsumptionDiagPage includes CO2e features', () => {
  const { readFileSync } = require('fs');
  const { resolve } = require('path');
  const src = readFileSync(resolve(__dirname, '../ConsumptionDiagPage.jsx'), 'utf8');

  it('uses useElecCo2Factor hook (post-migration EmissionFactorsContext)', () => {
    expect(src).toContain('useElecCo2Factor');
    expect(src).toContain('EmissionFactorsContext');
    expect(src).not.toContain('CO2E_FACTOR_KG_PER_KWH');
  });

  it('uses kwhToCo2Kg helper (P0.S1b doctrine zéro calcul métier FE)', () => {
    expect(src).toContain('kwhToCo2Kg');
    expect(src).toContain("from '../utils/co2'");
  });

  it('has CO2e evitable summary card', () => {
    expect(src).toContain("'CO₂e évitable'");
  });

  it('has CO2e column in table header', () => {
    expect(src).toContain('CO₂e (kg)');
  });

  it('uses fmtCo2 for CO₂ formatting', () => {
    expect(src).toContain('fmtCo2');
  });

  it('does NOT contain Math.sin/cos baseline synthesis (P0.S1b)', () => {
    expect(src).not.toContain('Math.sin(');
    expect(src).not.toContain('export function generateComparisonChart');
  });

  it('renders evidence profile placeholder (post-suppression)', () => {
    expect(src).toContain('evidence-profile-placeholder');
  });
});
