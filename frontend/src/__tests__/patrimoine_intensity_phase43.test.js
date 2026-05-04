/**
 * patrimoine_intensity_phase43.test.js — Sprint C-2 Phase 4.3
 *
 * Vérifie que Patrimoine.jsx consomme correctement le champ
 * `site.intensity_kwh_m2_total` exposé par le backend (Phase 4.2)
 * pour l'affichage kWh/m² ligne par site, en remplacement du
 * Math.round(annual_kwh / surface) inline (anti-pattern R7 audit Phase B).
 *
 * Convention repo : readFileSync + regex (cohérent patrimoine_v2.test.js).
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const SRC = fs.readFileSync(path.resolve(__dirname, '../pages/Patrimoine.jsx'), 'utf-8');

describe('Patrimoine.jsx — Phase 4.3 intensity_kwh_m2_total consumption', () => {
  test('site.intensity_kwh_m2_total est lu pour affichage par site', () => {
    expect(SRC).toMatch(/site\.intensity_kwh_m2_total/);
  });

  test('null-safety : intensity_kwh_m2_total != null avant utilisation', () => {
    // Pattern attendu : `site.intensity_kwh_m2_total != null ?`
    expect(SRC).toMatch(/site\.intensity_kwh_m2_total\s*!=\s*null/);
  });

  test('fallback "—" présent quand intensity null', () => {
    // Le pattern "—" (em dash) doit apparaître dans la branche fallback.
    // On vérifie une occurrence proche de intensity_kwh_m2_total.
    const m = SRC.match(/intensity_kwh_m2_total[\s\S]{0,300}—/);
    expect(m, 'fallback "—" attendu près du rendu intensity_kwh_m2_total').not.toBeNull();
  });

  test('aucun Math.round inline avec site.surface_m2 (anti-pattern R7 retiré)', () => {
    // Pattern interdit : Math.round(.../site.surface_m2)
    const FORBIDDEN = /Math\.round\([^)]*site\.surface_m2[^)]*\)/g;
    const matches = SRC.match(FORBIDDEN) || [];
    expect(matches).toEqual([]);
  });

  test('agrégat portfolio (KpiStripItem) référence dette tracée', () => {
    // L'agrégat portfolio Σ(annual_kwh)/Σ(surface) reste calcul FE pour MVP.
    // Doit référencer D-Phase4-3-Portfolio-Intensity-Backend-001 inline.
    expect(SRC).toMatch(/D-Phase4-3-Portfolio-Intensity-Backend-001/);
  });
});
