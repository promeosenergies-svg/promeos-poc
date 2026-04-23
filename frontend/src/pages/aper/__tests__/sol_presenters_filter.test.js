/**
 * PROMEOS — AperSol deep-link filter presenters (Sprint 1 Vague A, Phase A1)
 *
 * Valide le contrat de filter Vague 1 `?filter=parking|toiture` dans AperSol :
 *   - normalizeAperFilter : accepte uniquement 'parking' ou 'toiture', sinon null
 *   - applyAperFilter : propage le filtre au dashboard (KPIs, week-cards, bar
 *     chart, narratives héritent automatiquement)
 */
import { describe, it, expect } from 'vitest';
import { normalizeAperFilter, applyAperFilter } from '../sol_presenters';

describe('normalizeAperFilter', () => {
  it("accepte 'parking'", () => {
    expect(normalizeAperFilter('parking')).toBe('parking');
  });

  it("accepte 'toiture'", () => {
    expect(normalizeAperFilter('toiture')).toBe('toiture');
  });

  it('rejette les valeurs inconnues → null', () => {
    expect(normalizeAperFilter('foo')).toBeNull();
    expect(normalizeAperFilter('')).toBeNull();
    expect(normalizeAperFilter('Parking')).toBeNull();
    expect(normalizeAperFilter(undefined)).toBeNull();
    expect(normalizeAperFilter(null)).toBeNull();
  });
});

describe('applyAperFilter', () => {
  const baseDashboard = {
    total_eligible_sites: 5,
    parking: { eligible_count: 3, total_surface_m2: 5000, sites: [{ id: 1 }, { id: 2 }, { id: 3 }] },
    roof: { eligible_count: 2, total_surface_m2: 800, sites: [{ id: 4 }, { id: 5 }] },
  };

  it('filter null → dashboard inchangé', () => {
    const result = applyAperFilter(baseDashboard, null);
    expect(result).toBe(baseDashboard);
    expect(result.total_eligible_sites).toBe(5);
  });

  it("filter 'parking' → ne garde que les parkings, roof vidé", () => {
    const result = applyAperFilter(baseDashboard, 'parking');
    expect(result.parking.sites).toHaveLength(3);
    expect(result.roof.sites).toHaveLength(0);
    expect(result.total_eligible_sites).toBe(3);
  });

  it("filter 'toiture' → ne garde que les toitures, parking vidé", () => {
    const result = applyAperFilter(baseDashboard, 'toiture');
    expect(result.parking.sites).toHaveLength(0);
    expect(result.roof.sites).toHaveLength(2);
    expect(result.total_eligible_sites).toBe(2);
  });

  it("dashboard null → retourne null (safe fallback)", () => {
    expect(applyAperFilter(null, 'parking')).toBeNull();
    expect(applyAperFilter(undefined, 'toiture')).toBeUndefined();
  });

  it("dashboard sans parking/roof → catégories vides retournées", () => {
    const minimal = { total_eligible_sites: 0 };
    const result = applyAperFilter(minimal, 'parking');
    expect(result.parking.sites).toEqual([]);
    expect(result.total_eligible_sites).toBe(0);
  });
});
