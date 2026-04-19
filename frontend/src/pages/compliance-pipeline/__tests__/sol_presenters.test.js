/**
 * Unit tests — compliance-pipeline/sol_presenters.js
 *
 * Phase 5.1 Lot 6 · ≥ 15 cases couvrant null / undefined / {} / partial
 * / full (4 états dégradés). Pure functions, empty-state propre,
 * zéro throw.
 */
import { describe, it, expect } from 'vitest';
import {
  hasSummary,
  formatSitesReady,
  formatDeadlinesD30,
  formatUntrustedSites,
  interpretSitesReady,
  interpretDeadlinesD30,
  interpretUntrustedSites,
  buildKickerText,
  buildNarrative,
  buildSubNarrative,
  buildEmptyState,
  resolveTooltipExplain,
  pipelineRows,
  filterRows,
} from '../sol_presenters';

const SUMMARY_FULL = {
  org_id: 1,
  total_sites: 5,
  kpis: { data_blocked: 0, data_warning: 0, data_ready: 5 },
  top_blockers: [],
  deadlines: {
    d30: [{ type: 'finding', regulation: 'bacs', deadline: '2025-01-01', days_remaining: -473 }],
    d90: [{ type: 'finding', regulation: 'aper', deadline: '2026-07-01', days_remaining: 73 }],
    d180: [{ type: 'finding', regulation: 'dt', deadline: '2026-09-30', days_remaining: 164 }],
    beyond: [],
  },
  untrusted_sites: [
    { site_id: 1, site_nom: 'Siège HELIOS Paris', trust_score: 0, anomaly_count: 16, reasons: ['10 anomalies'] },
    { site_id: 3, site_nom: 'Entrepôt Toulouse', trust_score: 30, anomaly_count: 4, reasons: ['data gaps'] },
  ],
  sites: [
    {
      site_id: 1, site_nom: 'Siège HELIOS Paris',
      gate_status: 'OK', completeness_pct: 100, reg_risk: 10, compliance_score: 90,
      financial_opportunity_eur: 0,
      applicability: { tertiaire_operat: true, bacs: true, aper: true },
    },
    {
      site_id: 2, site_nom: 'Bureau Lyon',
      gate_status: 'WARNING', completeness_pct: 85, reg_risk: 35, compliance_score: 65,
      financial_opportunity_eur: 2500,
      applicability: { tertiaire_operat: true, bacs: false, aper: false },
    },
    {
      site_id: 3, site_nom: 'Entrepôt Toulouse',
      gate_status: 'BLOCKED', completeness_pct: 45, reg_risk: 70, compliance_score: 30,
      financial_opportunity_eur: 12000,
      applicability: { tertiaire_operat: true, bacs: true, aper: false },
    },
  ],
};

const SUMMARY_CLEAN = {
  org_id: 1,
  total_sites: 5,
  kpis: { data_blocked: 0, data_warning: 0, data_ready: 5 },
  top_blockers: [],
  deadlines: { d30: [], d90: [], d180: [], beyond: [] },
  untrusted_sites: [],
  sites: [],
};

const SUMMARY_EMPTY_PORTFOLIO = {
  org_id: 1,
  total_sites: 0,
  kpis: { data_blocked: 0, data_warning: 0, data_ready: 0 },
  top_blockers: [],
  deadlines: { d30: [], d90: [], d180: [], beyond: [] },
  untrusted_sites: [],
  sites: [],
};

describe('hasSummary', () => {
  it('false sur null / undefined / {}', () => {
    expect(hasSummary(null)).toBe(false);
    expect(hasSummary(undefined)).toBe(false);
    expect(hasSummary({})).toBe(false);
  });
  it('false sur total_sites absent ou null', () => {
    expect(hasSummary({ foo: 'bar' })).toBe(false);
    expect(hasSummary({ total_sites: null })).toBe(false);
  });
  it('true sur objet avec total_sites numérique (même 0)', () => {
    expect(hasSummary(SUMMARY_FULL)).toBe(true);
    expect(hasSummary(SUMMARY_EMPTY_PORTFOLIO)).toBe(true);
  });
});

describe('formatSitesReady', () => {
  it('null si summary absent (tous états dégradés)', () => {
    for (const s of [null, undefined, {}, { kpis: {} }]) {
      const k = formatSitesReady(s);
      expect(k.value).toBe(null);
      expect(k.tone).toBe('calme');
      expect(k.label).toBe('—');
    }
  });
  it('tone calme si portefeuille vide (0/0)', () => {
    const k = formatSitesReady(SUMMARY_EMPTY_PORTFOLIO);
    expect(k.tone).toBe('calme');
    expect(k.label).toBe('0 / 0');
  });
  it('tone succes si 100 % prêts', () => {
    const k = formatSitesReady(SUMMARY_CLEAN);
    expect(k.tone).toBe('succes');
    expect(k.value).toBe(5);
    expect(k.total).toBe(5);
  });
  it('tone attention si 50-99 % prêts', () => {
    const k = formatSitesReady({ total_sites: 5, kpis: { data_ready: 3 } });
    expect(k.tone).toBe('attention');
    expect(k.label).toBe('3 / 5');
  });
  it('tone refuse si < 50 % prêts', () => {
    const k = formatSitesReady({ total_sites: 5, kpis: { data_ready: 1 } });
    expect(k.tone).toBe('refuse');
  });
});

describe('formatDeadlinesD30', () => {
  it('null si summary absent', () => {
    expect(formatDeadlinesD30(null).value).toBe(null);
    expect(formatDeadlinesD30(undefined).tone).toBe('calme');
    expect(formatDeadlinesD30({}).value).toBe(null);
  });
  it('tone refuse si d30 > 0', () => {
    const k = formatDeadlinesD30(SUMMARY_FULL);
    expect(k.value).toBe(1);
    expect(k.tone).toBe('refuse');
  });
  it('tone attention si d30 = 0 mais d90 > 0', () => {
    const k = formatDeadlinesD30({
      total_sites: 1,
      deadlines: { d30: [], d90: [{}, {}], d180: [], beyond: [] },
    });
    expect(k.value).toBe(0);
    expect(k.d90).toBe(2);
    expect(k.tone).toBe('attention');
  });
  it('tone calme si d30 = 0 et d90 = 0', () => {
    expect(formatDeadlinesD30(SUMMARY_CLEAN).tone).toBe('calme');
  });
  it('deadlines absent → 0/calme (partial object safe)', () => {
    expect(formatDeadlinesD30({ total_sites: 2 }).tone).toBe('calme');
  });
});

describe('formatUntrustedSites', () => {
  it('null si summary absent', () => {
    expect(formatUntrustedSites(null).value).toBe(null);
    expect(formatUntrustedSites({}).value).toBe(null);
  });
  it('tone succes si 0 untrusted', () => {
    expect(formatUntrustedSites(SUMMARY_CLEAN).tone).toBe('succes');
  });
  it('tone attention si 0 < ratio < 50 %', () => {
    const k = formatUntrustedSites(SUMMARY_FULL); // 2 / 5 = 40 %
    expect(k.tone).toBe('attention');
    expect(k.value).toBe(2);
    expect(k.total).toBe(5);
  });
  it('tone refuse si ratio ≥ 50 %', () => {
    const k = formatUntrustedSites({ total_sites: 4, untrusted_sites: [1, 2, 3] });
    expect(k.tone).toBe('refuse');
  });
  it('tone calme si portefeuille vide (0/0)', () => {
    expect(formatUntrustedSites(SUMMARY_EMPTY_PORTFOLIO).tone).toBe('calme');
  });
});

describe('interpret*', () => {
  it('chaque interpret gère null sans throw', () => {
    expect(() => interpretSitesReady(null)).not.toThrow();
    expect(() => interpretDeadlinesD30(null)).not.toThrow();
    expect(() => interpretUntrustedSites(null)).not.toThrow();
    expect(interpretSitesReady(null)).toMatch(/indisponible/i);
  });
  it('interpretSitesReady adapte au ratio', () => {
    expect(interpretSitesReady(SUMMARY_CLEAN)).toMatch(/prêts|OK/i);
    expect(interpretSitesReady({ total_sites: 5, kpis: { data_ready: 1 } })).toMatch(/priorité|débloquer/i);
  });
  it('interpretDeadlinesD30 différencie bucket', () => {
    expect(interpretDeadlinesD30(SUMMARY_FULL)).toMatch(/imminente|sous 30/i);
    expect(interpretDeadlinesD30(SUMMARY_CLEAN)).toMatch(/confortable|Aucune/i);
  });
  it('interpretUntrustedSites adapte au ratio', () => {
    expect(interpretUntrustedSites(SUMMARY_FULL)).toMatch(/fiabiliser|anomalies/i);
    expect(interpretUntrustedSites(SUMMARY_CLEAN)).toMatch(/fiables|OK/i);
  });
});

describe('buildKickerText', () => {
  it('fallback si summary absent', () => {
    expect(buildKickerText(null)).toBe('CONFORMITÉ · PIPELINE PORTEFEUILLE');
  });
  it('inclut count sites + pluriel', () => {
    const k = buildKickerText(SUMMARY_FULL);
    expect(k).toContain('5');
    expect(k).toContain('SITES');
  });
  it('singulier si 1 site', () => {
    const k = buildKickerText({ total_sites: 1 });
    expect(k).toContain('1');
    expect(k).toContain('SITE');
    expect(k).not.toContain('SITES');
  });
});

describe('buildNarrative + buildSubNarrative', () => {
  it('narrative fallback honnête si summary null', () => {
    expect(buildNarrative(null)).toMatch(/indisponible|Pipeline/i);
  });
  it('narrative empty state si 0 sites', () => {
    expect(buildNarrative(SUMMARY_EMPTY_PORTFOLIO)).toMatch(/Aucun site|premier site/i);
  });
  it('narrative compact (≤ 130 car) avec prêts + échéances + untrusted', () => {
    const n = buildNarrative(SUMMARY_FULL);
    expect(n).toContain('5');            // total
    expect(n).toMatch(/prêts|prêt/i);
    expect(n.length).toBeLessThanOrEqual(130);
  });
  it('subNarrative sans mention endpoints / RegOps / /api', () => {
    const s = buildSubNarrative(SUMMARY_FULL);
    expect(s).not.toMatch(/\/api\/|RegOps|endpoint/i);
  });
  it('subNarrative prioritise blocked puis warning puis stable', () => {
    expect(buildSubNarrative({ total_sites: 5, kpis: { data_blocked: 2, data_warning: 0, data_ready: 3 } })).toMatch(/bloqué/i);
    expect(buildSubNarrative({ total_sites: 5, kpis: { data_blocked: 0, data_warning: 2, data_ready: 3 } })).toMatch(/warning|compléter/i);
    expect(buildSubNarrative(SUMMARY_CLEAN)).toMatch(/stable|trajectoire/i);
  });
});

describe('buildEmptyState', () => {
  it('null si summary présent', () => {
    expect(buildEmptyState({ summary: SUMMARY_FULL })).toBe(null);
  });
  it('fallback businessError si summary absent', () => {
    const es = buildEmptyState({ summary: null });
    expect(es).not.toBe(null);
    expect(es.title).toBeTruthy();
    expect(es.message).toBeTruthy();
  });
  it('fallback safe si appelé sans argument', () => {
    expect(() => buildEmptyState()).not.toThrow();
  });
});

describe('resolveTooltipExplain', () => {
  it('route vers bon interpret par code KPI', () => {
    expect(resolveTooltipExplain('pipeline_sites_ready', SUMMARY_FULL)).toMatch(/sites|prêts|portefeuille/i);
    expect(resolveTooltipExplain('pipeline_deadlines_d30', SUMMARY_FULL)).toMatch(/imminente|échéance/i);
    expect(resolveTooltipExplain('pipeline_untrusted_sites', SUMMARY_FULL)).toMatch(/fiabiliser|anomalies/i);
  });
  it('string vide si code inconnu', () => {
    expect(resolveTooltipExplain('unknown_kpi', SUMMARY_FULL)).toBe('');
  });
});

describe('pipelineRows', () => {
  it('array vide si summary absent', () => {
    expect(pipelineRows(null)).toEqual([]);
    expect(pipelineRows({})).toEqual([]);
    expect(pipelineRows({ total_sites: 5 })).toEqual([]);
  });
  it('mappe sites[] en rows avec applicability booléen', () => {
    const rows = pipelineRows(SUMMARY_FULL);
    expect(rows).toHaveLength(3);
    expect(rows[0].applicable_dt).toBe(true);
    expect(rows[0].applicable_bacs).toBe(true);
    expect(rows[1].applicable_bacs).toBe(false);
    expect(rows[2].gate_status).toBe('BLOCKED');
  });
  it('fallbacks safe si sites[].applicability absent', () => {
    const rows = pipelineRows({ total_sites: 1, sites: [{ site_id: 9, site_nom: 'X' }] });
    expect(rows[0].applicable_dt).toBe(false);
    expect(rows[0].completeness_pct).toBe(0);
    expect(rows[0].gate_status).toBe('UNKNOWN');
  });
});

describe('filterRows', () => {
  const rows = pipelineRows(SUMMARY_FULL);

  it('retourne tous les rows si pas de filtre', () => {
    expect(filterRows(rows)).toHaveLength(3);
  });
  it('filtre par search case-insensitive sur site_nom', () => {
    expect(filterRows(rows, { search: 'LYON' })).toHaveLength(1);
    expect(filterRows(rows, { search: 'siège' })).toHaveLength(1);
  });
  it('filtre par gate_status', () => {
    expect(filterRows(rows, { gate_status: 'BLOCKED' })).toHaveLength(1);
    expect(filterRows(rows, { gate_status: 'OK' })).toHaveLength(1);
  });
  it('filtre par framework applicability', () => {
    expect(filterRows(rows, { framework: 'bacs' })).toHaveLength(2);  // HELIOS + Toulouse
    expect(filterRows(rows, { framework: 'aper' })).toHaveLength(1);  // HELIOS
  });
  it('filtre untrustedOnly via Set d\'IDs', () => {
    const untrustedIds = new Set([1, 3]);
    expect(filterRows(rows, { untrustedOnly: true, untrustedIds })).toHaveLength(2);
  });
  it('retourne [] si rows non-array', () => {
    expect(filterRows(null)).toEqual([]);
    expect(filterRows(undefined)).toEqual([]);
  });
});
