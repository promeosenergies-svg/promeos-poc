import { describe, it, expect } from 'vitest';
import {
  buildKbRecoActionKey,
  buildKbRecoActionPayload,
  buildKbRecoActionDeepLink,
} from '../kbRecoActionModel';

const mockReco = {
  id: 42,
  recommendation_code: 'RECO-ECLAIRAGE-LED',
  title: 'Passage LED integral',
  estimated_savings_kwh_year: 15000,
  estimated_savings_eur_year: 2400,
  ice_score: 7.5,
  status: 'pending',
};

describe('kbRecoActionModel', () => {
  it('buildKbRecoActionKey returns correct format', () => {
    const key = buildKbRecoActionKey(1, 'RECO-ECLAIRAGE-LED');
    expect(key).toBe('kb-reco:1:RECO-ECLAIRAGE-LED');
    expect(key.length).toBeLessThan(64);
  });

  it('buildKbRecoActionPayload has required fields', () => {
    const payload = buildKbRecoActionPayload({
      orgId: 1,
      siteId: 5,
      siteName: 'Paris Bureaux',
      reco: mockReco,
      topSeverity: 'high',
    });

    expect(payload.source_type).toBe('insight');
    expect(payload.idempotency_key).toBe('kb-reco:5:RECO-ECLAIRAGE-LED');
    expect(payload.org_id).toBe(1);
    expect(payload.site_id).toBe(5);
    expect(payload.category).toBe('energie');
    expect(payload.title).toContain('Paris Bureaux');
    expect(payload.priority).toBe(2); // high → priority 2
    expect(payload.estimated_gain_eur).toBe(2400);
  });

  // Fix P0 QA Guardian 2026-04-15 : le front ne calcule plus co2e,
  // il envoie estimated_savings_kwh_year et le backend calcule via emission_factors.py.
  // Objectif : empêcher la dérive DB si ADEME met à jour le facteur CO2.
  it('sends estimated_savings_kwh_year (backend computes co2e)', () => {
    const payload = buildKbRecoActionPayload({
      orgId: 1,
      siteId: 1,
      siteName: 'Test',
      reco: mockReco,
    });
    expect(payload.estimated_savings_kwh_year).toBe(15000);
    // Le front ne doit PLUS envoyer co2e_savings_est_kg — source guard DB.
    expect(payload.co2e_savings_est_kg).toBeUndefined();
  });

  it('handles recos without savings', () => {
    const recoNoSavings = {
      ...mockReco,
      estimated_savings_kwh_year: null,
      estimated_savings_eur_year: null,
    };
    const payload = buildKbRecoActionPayload({
      orgId: 1,
      siteId: 1,
      siteName: 'Test',
      reco: recoNoSavings,
    });
    expect(payload.estimated_gain_eur).toBeNull();
    expect(payload.estimated_savings_kwh_year).toBeNull();
    expect(payload.co2e_savings_est_kg).toBeUndefined();
  });

  it('buildKbRecoActionDeepLink points to /actions', () => {
    const link = buildKbRecoActionDeepLink(5);
    expect(link).toContain('/actions');
    expect(link).toContain('site_id=5');
  });

  it('idempotency_key is stable', () => {
    const key1 = buildKbRecoActionKey(5, 'RECO-BACS-CLASSE-B');
    const key2 = buildKbRecoActionKey(5, 'RECO-BACS-CLASSE-B');
    expect(key1).toBe(key2);
  });
});
