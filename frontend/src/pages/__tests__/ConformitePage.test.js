/**
 * PROMEOS — Tests for ConformitePage helpers
 * Covers: sitesToObligations, isOverdue, buildScopeParams, parseBundleError
 */
import { describe, it, expect } from 'vitest';
import { sitesToObligations, isOverdue, buildScopeParams, parseBundleError } from '../ConformitePage';

/* ---------- isOverdue ---------- */
describe('isOverdue', () => {
  it('returns false when echeance is null', () => {
    expect(isOverdue({ echeance: null, statut: 'non_conforme' })).toBe(false);
  });

  it('returns false when statut is conforme', () => {
    expect(isOverdue({ echeance: '2020-01-01', statut: 'conforme' })).toBe(false);
  });

  it('returns true for past deadline with non-conforme', () => {
    expect(isOverdue({ echeance: '2020-01-01', statut: 'non_conforme' })).toBe(true);
  });

  it('returns false for future deadline', () => {
    expect(isOverdue({ echeance: '2099-12-31', statut: 'non_conforme' })).toBe(false);
  });

  it('returns false when echeance is undefined', () => {
    expect(isOverdue({ statut: 'a_risque' })).toBe(false);
  });
});

/* ---------- sitesToObligations ---------- */
describe('sitesToObligations', () => {
  const makeSite = (id, nom, findings) => ({
    site_id: id, site_nom: nom, findings,
  });

  const makeFinding = (reg, status, severity = 'low', extra = {}) => ({
    regulation: reg, rule_id: `${reg}_SCOPE`, status, severity,
    evidence: 'test', ...extra,
  });

  it('returns empty array for null input', () => {
    expect(sitesToObligations(null)).toEqual([]);
    expect(sitesToObligations(undefined)).toEqual([]);
  });

  it('returns empty array for empty array', () => {
    expect(sitesToObligations([])).toEqual([]);
  });

  it('groups findings by regulation', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'NOK'), makeFinding('decret_tertiaire', 'OK')]),
      makeSite(2, 'B', [makeFinding('bacs', 'OK')]),
    ];
    const result = sitesToObligations(sites);
    const codes = result.map(o => o.code);
    expect(codes).toContain('bacs');
    expect(codes).toContain('decret_tertiaire');
    expect(result).toHaveLength(2);
  });

  it('tracks worst severity per regulation', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'NOK', 'medium')]),
      makeSite(2, 'B', [makeFinding('bacs', 'OK', 'critical')]),
    ];
    const result = sitesToObligations(sites);
    const bacs = result.find(o => o.code === 'bacs');
    expect(bacs.severity).toBe('critical');
  });

  it('counts sites_concernes correctly', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'NOK')]),
      makeSite(2, 'B', [makeFinding('bacs', 'OK')]),
      makeSite(3, 'C', [makeFinding('bacs', 'OK')]),
    ];
    const result = sitesToObligations(sites);
    const bacs = result.find(o => o.code === 'bacs');
    expect(bacs.sites_concernes).toBe(3);
    expect(bacs.sites_conformes).toBe(2);
  });

  it('sets statut non_conforme when any NOK', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'OK')]),
      makeSite(2, 'B', [makeFinding('bacs', 'NOK')]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].statut).toBe('non_conforme');
  });

  it('sets statut a_risque when UNKNOWN (no NOK)', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'OK')]),
      makeSite(2, 'B', [makeFinding('bacs', 'UNKNOWN')]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].statut).toBe('a_risque');
  });

  it('tracks closest deadline', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'NOK', 'high', { deadline: '2026-12-31' })]),
      makeSite(2, 'B', [makeFinding('bacs', 'NOK', 'high', { deadline: '2025-06-01' })]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].echeance).toBe('2025-06-01');
  });

  it('attaches site_nom and site_id to each finding', () => {
    const sites = [makeSite(7, 'SiteX', [makeFinding('bacs', 'OK')])];
    const result = sitesToObligations(sites);
    expect(result[0].findings[0].site_id).toBe(7);
    expect(result[0].findings[0].site_nom).toBe('SiteX');
  });
});

/* ---------- buildScopeParams ---------- */
describe('buildScopeParams', () => {
  it('always includes org_id', () => {
    const params = buildScopeParams({ orgId: 2 }, [{ id: 10 }, { id: 20 }, { id: 30 }]);
    expect(params.org_id).toBe(2);
    expect(params.site_id).toBeUndefined();
  });

  it('includes site_id when exactly 1 site', () => {
    const params = buildScopeParams({ orgId: 1 }, [{ id: 42 }]);
    expect(params.org_id).toBe(1);
    expect(params.site_id).toBe(42);
  });

  it('no site_id when 0 sites', () => {
    const params = buildScopeParams({ orgId: 1 }, []);
    expect(params.org_id).toBe(1);
    expect(params.site_id).toBeUndefined();
  });

  it('no site_id when many sites', () => {
    const params = buildScopeParams({ orgId: 3 }, [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]);
    expect(params.org_id).toBe(3);
    expect(params.site_id).toBeUndefined();
  });
});

/* ---------- parseBundleError ---------- */
describe('parseBundleError', () => {
  it('returns error for null bundle (network failure)', () => {
    const err = parseBundleError(null);
    expect(err).not.toBeNull();
    expect(err.message).toContain('indisponibles');
  });

  it('returns error with debug info for DB_SCHEMA_MISMATCH', () => {
    const bundle = {
      error_code: 'DB_SCHEMA_MISMATCH',
      empty_reason_message: 'Schema error',
      trace_id: 'abc123',
      hint: 'run_reset_db',
    };
    const err = parseBundleError(bundle);
    expect(err.error_code).toBe('DB_SCHEMA_MISMATCH');
    expect(err.trace_id).toBe('abc123');
    expect(err.hint).toBe('run_reset_db');
  });

  it('returns null for healthy bundle (no error_code)', () => {
    const bundle = {
      summary: { total_sites: 3 },
      sites: [],
      empty_reason_code: null,
    };
    expect(parseBundleError(bundle)).toBeNull();
  });
});

/* ---------- sitesToObligations with 3 regulations ---------- */
describe('sitesToObligations — 3 regulations', () => {
  const makeSite = (id, nom, findings) => ({
    site_id: id, site_nom: nom, findings,
  });
  const makeFinding = (reg, status, severity = 'medium', extra = {}) => ({
    regulation: reg, rule_id: `${reg}_RULE`, status, severity,
    evidence: 'test', ...extra,
  });

  it('groups 3 regulations into 3 obligations', () => {
    const sites = [
      makeSite(1, 'Hyper 1', [
        makeFinding('bacs', 'NOK', 'critical'),
        makeFinding('decret_tertiaire_operat', 'OK'),
        makeFinding('aper', 'UNKNOWN', 'high'),
      ]),
      makeSite(2, 'Hyper 2', [
        makeFinding('bacs', 'OK'),
        makeFinding('decret_tertiaire_operat', 'NOK', 'high'),
        makeFinding('aper', 'OK'),
      ]),
    ];
    const obligations = sitesToObligations(sites);
    const codes = obligations.map(o => o.code);
    expect(codes).toContain('bacs');
    expect(codes).toContain('decret_tertiaire_operat');
    expect(codes).toContain('aper');
    expect(obligations).toHaveLength(3);
  });

  it('shows dash score when no evaluated sites (empty bundle)', () => {
    const obligations = sitesToObligations([]);
    expect(obligations).toHaveLength(0);
  });
});
