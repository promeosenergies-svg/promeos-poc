/**
 * PROMEOS — Tests for ConformitePage helpers
 * Covers: sitesToObligations, isOverdue, buildScopeParams, parseBundleError
 */
import { describe, it, expect } from 'vitest';
import { sitesToObligations, isOverdue, buildScopeParams, parseBundleError, resolveScopeLabel, computeBacsV2Summary, computeScopeLabel } from '../ConformitePage';

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

  it('sets statut a_qualifier when UNKNOWN (no NOK)', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'OK')]),
      makeSite(2, 'B', [makeFinding('bacs', 'UNKNOWN')]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].statut).toBe('a_qualifier');
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

  it('sets statut hors_perimetre when OUT_OF_SCOPE', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'OUT_OF_SCOPE')]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].statut).toBe('hors_perimetre');
  });

  it('NOK overrides a_qualifier', () => {
    const sites = [
      makeSite(1, 'A', [makeFinding('bacs', 'UNKNOWN')]),
      makeSite(2, 'B', [makeFinding('bacs', 'NOK', 'critical')]),
    ];
    const result = sitesToObligations(sites);
    expect(result[0].statut).toBe('non_conforme');
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

  it('includes portefeuille_id when portefeuille scope with many sites', () => {
    const params = buildScopeParams({ orgId: 1, portefeuilleId: 3 }, [{ id: 10 }, { id: 20 }]);
    expect(params.org_id).toBe(1);
    expect(params.portefeuille_id).toBe(3);
    expect(params.site_id).toBeUndefined();
  });

  it('site_id takes priority over portefeuille_id when 1 site', () => {
    const params = buildScopeParams({ orgId: 1, portefeuilleId: 3 }, [{ id: 42 }]);
    expect(params.org_id).toBe(1);
    expect(params.site_id).toBe(42);
    expect(params.portefeuille_id).toBeUndefined();
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

/* ---------- resolveScopeLabel (DevScopeBadge logic) ---------- */
describe('resolveScopeLabel', () => {
  it('returns org scope by default', () => {
    const result = resolveScopeLabel({ orgId: 1, portefeuilleId: null, siteId: null });
    expect(result.scopeType).toBe('org');
    expect(result.scopeId).toBe(1);
    expect(result.label).toBe('org/1');
  });

  it('returns portefeuille scope when set', () => {
    const result = resolveScopeLabel({ orgId: 1, portefeuilleId: 3, siteId: null });
    expect(result.scopeType).toBe('portefeuille');
    expect(result.scopeId).toBe(3);
    expect(result.label).toBe('portefeuille/3');
  });

  it('returns site scope when site selected', () => {
    const result = resolveScopeLabel({ orgId: 1, portefeuilleId: 2, siteId: 42 });
    expect(result.scopeType).toBe('site');
    expect(result.scopeId).toBe(42);
    expect(result.label).toBe('site/42');
  });
});

/* ---------- API badge logic (Connected / Offline) ---------- */
describe('API badge logic', () => {
  it('API offline: parseBundleError(null) returns error with indisponibles message', () => {
    const err = parseBundleError(null);
    expect(err).not.toBeNull();
    expect(err.message).toContain('indisponibles');
  });

  it('API connected: parseBundleError with healthy bundle returns null', () => {
    const bundle = { summary: { total_sites: 36 }, sites: [], empty_reason_code: null };
    expect(parseBundleError(bundle)).toBeNull();
  });
});

/* ---------- computeBacsV2Summary ---------- */
describe('computeBacsV2Summary', () => {
  it('returns null when no bacs_v2 data', () => {
    expect(computeBacsV2Summary(null)).toBeNull();
    expect(computeBacsV2Summary(undefined)).toBeNull();
    expect(computeBacsV2Summary({})).toBeNull();
  });

  it('aggregates applicable from bundle entries', () => {
    const data = {
      1: { applicable: true, deadline: '2025-01-01', threshold_kw: 290, putile_kw: 350, tri_exemption: false },
      2: { applicable: false, deadline: null, threshold_kw: 0, putile_kw: 50, tri_exemption: false },
    };
    const result = computeBacsV2Summary(data);
    expect(result.applicable).toBe(true);
    expect(result.threshold_kw).toBe(290);
    expect(result.tier).toBe('TIER1');
  });

  it('picks closest deadline', () => {
    const data = {
      1: { applicable: true, deadline: '2030-01-01', threshold_kw: 70, putile_kw: 150, tri_exemption: false },
      2: { applicable: true, deadline: '2025-01-01', threshold_kw: 290, putile_kw: 350, tri_exemption: true },
    };
    const result = computeBacsV2Summary(data);
    expect(result.deadline).toBe('2025-01-01');
    expect(result.tri_exemption).toBe(true);
  });

  it('returns TIER2 when max threshold < 290', () => {
    const data = {
      1: { applicable: true, deadline: '2030-01-01', threshold_kw: 70, putile_kw: 150, tri_exemption: false },
    };
    const result = computeBacsV2Summary(data);
    expect(result.tier).toBe('TIER2');
    expect(result.putile_kw).toBe(150);
  });
});

/* ---------- computeScopeLabel ---------- */
describe('computeScopeLabel', () => {
  const org = { nom: 'Nexity' };

  it('returns org scope by default', () => {
    const result = computeScopeLabel(org, { siteId: null, portefeuilleId: null }, [{}, {}, {}], []);
    expect(result).toBe('Nexity \u00b7 Organisation (3 sites)');
  });

  it('shows portefeuille name when selected', () => {
    const pfs = [{ id: 3, nom: 'PF Alpha' }];
    const result = computeScopeLabel(org, { siteId: null, portefeuilleId: 3 }, [{}, {}], pfs);
    expect(result).toContain('Portefeuille: PF Alpha');
    expect(result).toContain('2 sites');
  });

  it('shows site name when site selected', () => {
    const sites = [{ id: 42, nom: 'Hyper Lyon' }];
    const result = computeScopeLabel(org, { siteId: 42, portefeuilleId: 1 }, sites, []);
    expect(result).toContain('Site: Hyper Lyon');
  });

  it('falls back to site ID when site has no nom', () => {
    const sites = [{ id: 42 }];
    const result = computeScopeLabel(org, { siteId: 42, portefeuilleId: null }, sites, []);
    expect(result).toContain('42');
  });
});

/* ---------- Demo-ready: forbidden strings regression ---------- */
describe('FR demo-ready — forbidden strings in key pages', () => {
  const fs = require('fs');
  const path = require('path');

  const readPage = (name) => fs.readFileSync(path.resolve(__dirname, '..', name), 'utf8');

  it('CreateActionModal uses "À planifier" not "Backlog"', () => {
    const src = fs.readFileSync(path.resolve(__dirname, '../../components/CreateActionModal.jsx'), 'utf8');
    // "Backlog" should not appear as a user-facing label
    expect(src).not.toMatch(/label:\s*['"]Backlog['"]/);
    expect(src).toMatch(/À planifier/);
  });

  it('CompliancePage uses "Réévaluer" not "Re-evaluer"', () => {
    const src = readPage('CompliancePage.jsx');
    expect(src).not.toMatch(/Re-evaluer/);
  });

  it('ConformitePage uses "Recommandations" not "Actions à mener"', () => {
    const src = readPage('ConformitePage.jsx');
    expect(src).not.toMatch(/Actions à mener/);
    expect(src).toMatch(/Recommandations/);
  });

  it('ConformitePage rule_id fallback never shows raw code to non-expert', () => {
    const src = readPage('ConformitePage.jsx');
    // The fallback in findings list should NOT be f.rule_id alone
    expect(src).not.toMatch(/\?\.\s*title_fr\s*\|\|\s*f\.rule_id\s*\}/);
  });
});

/* ---------- Sprint Conformité: centralized FR labels ---------- */
describe('FR labels — no English in user-facing constants', () => {
  it('STATUT_LABELS has only FR text', () => {
    const { STATUT_LABELS } = require('../../domain/compliance/complianceLabels.fr');
    const values = Object.values(STATUT_LABELS);
    values.forEach(v => {
      expect(v).not.toMatch(/^(Compliant|Non compliant|At risk|Unknown|Out of scope)$/i);
    });
    expect(STATUT_LABELS.a_qualifier).toBe('À qualifier');
    expect(STATUT_LABELS.hors_perimetre).toBe('Hors périmètre');
  });

  it('BACKEND_STATUS_MAP maps UNKNOWN to a_qualifier', () => {
    const { BACKEND_STATUS_MAP } = require('../../domain/compliance/complianceLabels.fr');
    expect(BACKEND_STATUS_MAP.UNKNOWN).toBe('a_qualifier');
    expect(BACKEND_STATUS_MAP.OUT_OF_SCOPE).toBe('hors_perimetre');
    expect(BACKEND_STATUS_MAP.OK).toBe('conforme');
    expect(BACKEND_STATUS_MAP.NOK).toBe('non_conforme');
  });

  it('RULE_LABELS has title_fr and why_fr for all rules', () => {
    const { RULE_LABELS } = require('../../domain/compliance/complianceLabels.fr');
    const rules = Object.values(RULE_LABELS);
    expect(rules.length).toBeGreaterThanOrEqual(13);
    rules.forEach(r => {
      expect(r).toHaveProperty('title_fr');
      expect(r).toHaveProperty('why_fr');
      expect(r.title_fr.length).toBeGreaterThan(3);
    });
  });

  it('ACTION_STATUS_LABELS uses proper accents', () => {
    const { ACTION_STATUS_LABELS } = require('../../domain/compliance/complianceLabels.fr');
    expect(ACTION_STATUS_LABELS.backlog).toBe('À planifier');
    expect(ACTION_STATUS_LABELS.planned).toBe('Planifiée');
    expect(ACTION_STATUS_LABELS.done).toBe('Terminée');
  });

  it('SEVERITY_LABELS are in FR', () => {
    const { SEVERITY_LABELS } = require('../../domain/compliance/complianceLabels.fr');
    expect(SEVERITY_LABELS.critical).toBe('Critique');
    expect(SEVERITY_LABELS.high).toBe('Élevée');
    expect(SEVERITY_LABELS.medium).toBe('Moyenne');
    expect(SEVERITY_LABELS.low).toBe('Faible');
  });
});

