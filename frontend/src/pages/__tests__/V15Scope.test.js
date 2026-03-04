/**
 * PROMEOS — Sprint V15 Scope Tests
 * Pure logic tests (no DOM) covering:
 *   - filteredInsights: selectedSiteId filtering
 *   - hasMismatch: scope mismatch detection
 *   - computeSummaryFromInsights: totals + by_type
 *   - GRAN_LABELS mapping
 *   - DataCoverageBadge parts generation logic
 */
import { describe, it, expect } from 'vitest';
import { computeSummaryFromInsights } from '../ConsumptionDiagPage';

// ── filteredInsights ───────────────────────────────────────────────────────────

describe('filteredInsights: site scope filtering', () => {
  const insights = [
    { id: 1, site_id: 1, type: 'base_load', estimated_loss_kwh: 100, estimated_loss_eur: 15 },
    { id: 2, site_id: 2, type: 'pointe', estimated_loss_kwh: 200, estimated_loss_eur: 30 },
    { id: 3, site_id: 3, type: 'derive', estimated_loss_kwh: 50, estimated_loss_eur: 7.5 },
    { id: 4, site_id: 1, type: 'hors_horaires', estimated_loss_kwh: 80, estimated_loss_eur: 12 },
  ];

  function filterInsights(allInsights, selectedSiteId) {
    if (!allInsights.length) return [];
    if (selectedSiteId) return allInsights.filter((i) => i.site_id === selectedSiteId);
    return allInsights;
  }

  it('selectedSiteId=null → all insights returned', () => {
    const result = filterInsights(insights, null);
    expect(result).toHaveLength(4);
  });

  it('selectedSiteId=1 → only site 1 insights (2 items)', () => {
    const result = filterInsights(insights, 1);
    expect(result).toHaveLength(2);
    expect(result.every((i) => i.site_id === 1)).toBe(true);
  });

  it('selectedSiteId=3 → only site 3 insights (1 item)', () => {
    const result = filterInsights(insights, 3);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(3);
  });

  it('selectedSiteId=99 → empty array (no data for that site)', () => {
    const result = filterInsights(insights, 99);
    expect(result).toHaveLength(0);
  });
});

// ── hasMismatch ────────────────────────────────────────────────────────────────

describe('hasMismatch: scope mismatch detection', () => {
  const insights = [{ site_id: 1 }, { site_id: 2 }, { site_id: 3 }];

  function computeHasMismatch(selectedSiteId, allInsights) {
    const isSiteScoped = Boolean(selectedSiteId);
    return isSiteScoped && new Set(allInsights.map((i) => i.site_id)).size > 1;
  }

  it('hasMismatch: true when siteId set + insights from 3 different sites', () => {
    expect(computeHasMismatch(1, insights)).toBe(true);
  });

  it('hasMismatch: false when selectedSiteId=null', () => {
    expect(computeHasMismatch(null, insights)).toBe(false);
  });

  it('hasMismatch: false when all insights belong to selectedSiteId (1 unique site)', () => {
    const singleSiteInsights = [{ site_id: 5 }, { site_id: 5 }];
    expect(computeHasMismatch(5, singleSiteInsights)).toBe(false);
  });

  it('hasMismatch: false when insights array is empty', () => {
    expect(computeHasMismatch(1, [])).toBe(false);
  });
});

// ── computeSummaryFromInsights ─────────────────────────────────────────────────

describe('computeSummaryFromInsights: totals and by_type', () => {
  const insights = [
    { id: 1, site_id: 1, type: 'base_load', estimated_loss_kwh: 100, estimated_loss_eur: 15 },
    { id: 2, site_id: 2, type: 'pointe', estimated_loss_kwh: 200, estimated_loss_eur: 30 },
    { id: 3, site_id: 1, type: 'base_load', estimated_loss_kwh: 50, estimated_loss_eur: 7.5 },
    { id: 4, site_id: 3, type: 'hors_horaires', estimated_loss_kwh: 80, estimated_loss_eur: 12 },
  ];

  it('computes correct totals for 4 insights', () => {
    const result = computeSummaryFromInsights(insights);
    expect(result.total_insights).toBe(4);
    expect(result.total_loss_kwh).toBeCloseTo(430);
    expect(result.total_loss_eur).toBeCloseTo(64.5);
  });

  it('counts unique sites correctly (sites_with_insights)', () => {
    const result = computeSummaryFromInsights(insights);
    expect(result.sites_with_insights).toBe(3); // sites 1, 2, 3
  });

  it('groups by_type correctly', () => {
    const result = computeSummaryFromInsights(insights);
    expect(result.by_type.base_load).toBe(2);
    expect(result.by_type.pointe).toBe(1);
    expect(result.by_type.hors_horaires).toBe(1);
  });

  it('empty array → returns zero values', () => {
    const result = computeSummaryFromInsights([]);
    expect(result.total_insights).toBe(0);
    expect(result.sites_with_insights).toBe(0);
    expect(result.total_loss_kwh).toBe(0);
    expect(result.total_loss_eur).toBe(0);
    expect(result.by_type).toEqual({});
  });

  it('null input → returns zero values', () => {
    const result = computeSummaryFromInsights(null);
    expect(result.total_insights).toBe(0);
    expect(result.total_loss_kwh).toBe(0);
  });

  it('insights with null site_id → not counted in sites_with_insights', () => {
    const mixed = [
      { id: 1, site_id: null, type: 'base_load', estimated_loss_kwh: 10, estimated_loss_eur: 1.5 },
      { id: 2, site_id: 5, type: 'pointe', estimated_loss_kwh: 20, estimated_loss_eur: 3 },
    ];
    const result = computeSummaryFromInsights(mixed);
    expect(result.sites_with_insights).toBe(1); // only site_id=5 counts
  });
});

// ── GRAN_LABELS mapping ────────────────────────────────────────────────────────

describe('GRAN_LABELS: granularity label mapping', () => {
  const GRAN_LABELS = {
    daily: 'Journalière',
    monthly: 'Mensuelle',
    hourly: 'Horaire',
    '15min': '15 min',
    '30min': '30 min',
  };

  it('daily → Journalière', () => {
    expect(GRAN_LABELS.daily).toBe('Journalière');
  });

  it('monthly → Mensuelle', () => {
    expect(GRAN_LABELS.monthly).toBe('Mensuelle');
  });

  it('hourly → Horaire', () => {
    expect(GRAN_LABELS.hourly).toBe('Horaire');
  });

  it('15min → 15 min', () => {
    expect(GRAN_LABELS['15min']).toBe('15 min');
  });

  it('30min → 30 min', () => {
    expect(GRAN_LABELS['30min']).toBe('30 min');
  });

  it('unknown granularity → falls back to raw value (undefined in map)', () => {
    expect(GRAN_LABELS['weekly']).toBeUndefined();
    // In the component: GRAN_LABELS[gran] || gran → falls back to 'weekly'
    const gran = 'weekly';
    expect(GRAN_LABELS[gran] || gran).toBe('weekly');
  });
});

// ── DataCoverageBadge parts generation ────────────────────────────────────────

describe('DataCoverageBadge: parts generation logic', () => {
  const GRAN_LABELS = {
    daily: 'Journalière',
    monthly: 'Mensuelle',
    hourly: 'Horaire',
    '15min': '15 min',
    '30min': '30 min',
  };

  function buildParts(meta, siteCount, qualityPct) {
    return [
      siteCount > 1 ? `${siteCount} sites` : null,
      meta?.n_meters ? `${meta.n_meters}\u00a0compteur${meta.n_meters > 1 ? 's' : ''}` : null,
      meta?.n_points ? `${meta.n_points.toLocaleString('fr-FR')}\u00a0points` : null,
      meta?.granularity
        ? `Granularité\u00a0: ${GRAN_LABELS[meta.granularity] || meta.granularity}`
        : null,
      qualityPct != null ? `Qualité\u00a0: ${qualityPct}\u00a0%` : null,
      'Source\u00a0: EMS',
    ].filter(Boolean);
  }

  it('single site: no "N sites" part', () => {
    const parts = buildParts({ n_meters: 1, n_points: 31, granularity: 'daily' }, 1, null);
    expect(parts.some((p) => p.includes('sites'))).toBe(false);
  });

  it('2 sites: includes "2 sites" part', () => {
    const parts = buildParts({ n_meters: 2, n_points: 62, granularity: 'daily' }, 2, null);
    expect(parts[0]).toBe('2 sites');
  });

  it('always includes "Source : EMS"', () => {
    const parts = buildParts(null, 1, null);
    expect(parts[parts.length - 1]).toBe('Source\u00a0: EMS');
  });

  it('n_meters=1 → singular "compteur"', () => {
    const parts = buildParts({ n_meters: 1, n_points: 10, granularity: 'daily' }, 1, null);
    expect(parts.some((p) => p.includes('compteur') && !p.includes('compteurs'))).toBe(true);
  });

  it('n_meters=3 → plural "compteurs"', () => {
    const parts = buildParts({ n_meters: 3, n_points: 93, granularity: 'monthly' }, 1, null);
    expect(parts.some((p) => p.includes('compteurs'))).toBe(true);
  });

  it('qualityPct included when provided', () => {
    const parts = buildParts({ n_meters: 1, n_points: 30, granularity: 'daily' }, 1, 87);
    expect(parts.some((p) => p.includes('87'))).toBe(true);
  });
});
