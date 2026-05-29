/**
 * PROMEOS — Tests kwhToCo2Kg + kwhToCo2Tonnes.
 *
 * Sprint Énergie P0.S1b (2026-05-29).
 * Cible : frontend/src/utils/co2.js
 *
 * Doctrine : ces helpers sont l'unique point autorisé du frontend pour
 * la conversion kWh → kgCO₂eq. Facteur ADEME V23.6 (0,052 kgCO₂eq/kWh
 * électricité France métropole) fourni par backend.
 */
import { describe, it, expect } from 'vitest';
import { kwhToCo2Kg, kwhToCo2Tonnes } from '../utils/co2';

describe('kwhToCo2Kg', () => {
  it('convertit 1000 kWh × 0,052 (ADEME V23.6 élec FR) → 52 kg', () => {
    expect(kwhToCo2Kg(1000, 0.052)).toBe(52);
  });

  it('arrondit à l’entier (52,3 → 52, 52,6 → 53)', () => {
    expect(kwhToCo2Kg(1005.77, 0.052)).toBe(52);
    expect(kwhToCo2Kg(1011.54, 0.052)).toBe(53);
  });

  it('retourne 0 pour kwh=0 (cas légitime, pas null)', () => {
    expect(kwhToCo2Kg(0, 0.052)).toBe(0);
  });

  it('retourne null si kwh manquant (ne masque pas l’absence de donnée)', () => {
    expect(kwhToCo2Kg(null, 0.052)).toBeNull();
    expect(kwhToCo2Kg(undefined, 0.052)).toBeNull();
  });

  it('retourne null si facteur manquant', () => {
    expect(kwhToCo2Kg(1000, null)).toBeNull();
    expect(kwhToCo2Kg(1000, undefined)).toBeNull();
  });

  it('retourne null pour entrées non-numériques', () => {
    expect(kwhToCo2Kg('abc', 0.052)).toBeNull();
    expect(kwhToCo2Kg(NaN, 0.052)).toBeNull();
    expect(kwhToCo2Kg(Infinity, 0.052)).toBeNull();
    expect(kwhToCo2Kg(1000, NaN)).toBeNull();
  });

  it('accepte les strings castables (cas payload backend JSON)', () => {
    expect(kwhToCo2Kg('1000', '0.052')).toBe(52);
  });

  it('supporte gaz naturel ADEME V23.6 (0,227 kgCO₂eq/kWh PCI)', () => {
    // Cf. skill emission_factors — gaz = 0.227
    expect(kwhToCo2Kg(1000, 0.227)).toBe(227);
  });
});

describe('kwhToCo2Tonnes', () => {
  it('convertit 100 000 kWh × 0,052 → 5,20 tonnes', () => {
    expect(kwhToCo2Tonnes(100000, 0.052)).toBe(5.2);
  });

  it('arrondit à 2 décimales', () => {
    expect(kwhToCo2Tonnes(12345, 0.052)).toBe(0.64); // 641,94 kg → 0,64 t
  });

  it('retourne null si entrées invalides (propage kwhToCo2Kg)', () => {
    expect(kwhToCo2Tonnes(null, 0.052)).toBeNull();
    expect(kwhToCo2Tonnes(1000, null)).toBeNull();
  });

  it('retourne 0 pour kwh=0', () => {
    expect(kwhToCo2Tonnes(0, 0.052)).toBe(0);
  });
});
