import { describe, it, expect, vi, beforeEach } from 'vitest';

// vi.mock is hoisted — use vi.hoisted for shared mock refs
const { mockGet } = vi.hoisted(() => {
  const mockGet = vi.fn();
  return { mockGet };
});

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    }),
  },
}));

import { getSiteIntelligence } from '../../services/api';

describe('getSiteIntelligence API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls GET /sites/{id}/intelligence', async () => {
    mockGet.mockResolvedValue({
      data: {
        site_id: 1,
        archetype: { code: 'BUREAU_STANDARD', match_score: 0.85, title: 'Bureau standard' },
        anomalies: [],
        recommendations: [],
        summary: { total_anomalies: 0, total_recommendations: 0 },
        status: 'analyzed',
      },
    });

    const result = await getSiteIntelligence(1);
    expect(mockGet).toHaveBeenCalledWith('/sites/1/intelligence');
    expect(result.site_id).toBe(1);
    expect(result.archetype.code).toBe('BUREAU_STANDARD');
  });

  it('returns correct shape with anomalies and recommendations', async () => {
    mockGet.mockResolvedValue({
      data: {
        site_id: 2,
        archetype: { code: 'HOTEL_STANDARD', match_score: 0.92, title: 'Hotel' },
        anomalies: [
          {
            id: 1,
            anomaly_code: 'RULE-BASE-NUIT-001',
            title: 'Talon nocturne',
            severity: 'high',
            confidence: 0.9,
          },
        ],
        recommendations: [
          {
            id: 1,
            recommendation_code: 'RECO-LED',
            title: 'LED',
            ice_score: 0.5,
            status: 'PENDING',
          },
        ],
        summary: { total_anomalies: 1, total_recommendations: 1, potential_savings_eur_year: 5000 },
        status: 'analyzed',
      },
    });

    const result = await getSiteIntelligence(2);
    expect(result.anomalies).toHaveLength(1);
    expect(result.recommendations).toHaveLength(1);
    expect(result.summary.potential_savings_eur_year).toBe(5000);
  });
});
