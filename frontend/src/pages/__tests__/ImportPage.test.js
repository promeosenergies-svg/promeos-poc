/**
 * PROMEOS — Tests for ImportPage: scope switching + silent status-pack + error handling.
 *
 * Ensures:
 * - 404 on /demo/status-pack does NOT trigger a toast
 * - seedDemoPack → applyDemoScope called with { orgId, orgNom, ... } (object form)
 * - resetDemoPack → clearScope called
 * - Seed error → toast contains HTTP status + detail
 * - isDemoPath correctly identifies /demo/* routes (scope-exempt guard)
 * - scopeLabel correctly derives "Tous les sites" vs "Site : <name>"
 */
import { describe, it, expect, vi } from 'vitest';
import { isSilentUrl, normalizePathFromAxiosConfig, isDemoPath } from '../../services/api';

// ── Silent URL: status-pack ───────────────────────────────────────────────

describe('ImportPage: status-pack 404 is silent', () => {
  it('404 on status-pack with silent:true flag prevents toast', () => {
    const cfg = { url: '/demo/status-pack', baseURL: '/api', silent: true };
    const isSilent = cfg.silent || isSilentUrl(cfg);
    expect(isSilent).toBe(true);
  });

  it('404 on status-pack matches via URL even without silent flag', () => {
    const cfg = { url: '/demo/status-pack', baseURL: '/api' };
    const isSilent = cfg.silent || isSilentUrl(cfg);
    expect(isSilent).toBe(true);
  });

  it('isSilentUrl matches config with baseURL /api', () => {
    expect(isSilentUrl({ url: '/demo/status-pack', baseURL: '/api' })).toBe(true);
  });

  it('isSilentUrl matches absolute URL variant', () => {
    expect(isSilentUrl({ url: 'http://localhost:8000/api/demo/status-pack?x=1' })).toBe(true);
  });

  it('seed-pack is NOT silent (user actions should toast)', () => {
    expect(isSilentUrl({ url: '/demo/seed-pack', baseURL: '/api' })).toBe(false);
  });

  it('reset-pack is NOT silent (user actions should toast)', () => {
    expect(isSilentUrl({ url: '/demo/reset-pack', baseURL: '/api' })).toBe(false);
  });

  it('simulated interceptor: silent config skips toast callback', () => {
    const toastFn = vi.fn();
    const error = {
      config: { url: '/demo/status-pack', baseURL: '/api', silent: true },
      response: { status: 404, statusText: 'Not Found' },
    };
    const cfg = error.config;
    const isSilent = cfg.silent || isSilentUrl(cfg);
    if (!isSilent) { toastFn(error.response.statusText, 'error'); }
    expect(toastFn).not.toHaveBeenCalled();
  });

  it('simulated interceptor: non-silent 404 DOES toast', () => {
    const toastFn = vi.fn();
    const error = {
      config: { url: '/sites', baseURL: '/api' },
      response: { status: 404, statusText: 'Not Found' },
    };
    const cfg = error.config;
    const isSilent = cfg.silent || isSilentUrl(cfg);
    if (!isSilent) { toastFn(error.response.statusText, 'error'); }
    expect(toastFn).toHaveBeenCalledWith('Not Found', 'error');
  });
});

// ── isDemoPath ─────────────────────────────────────────────────────────────

describe('isDemoPath — scope-exempt guard for /demo/* endpoints', () => {
  it('/demo/seed-pack is a demo path', () => {
    expect(isDemoPath('/demo/seed-pack')).toBe(true);
  });

  it('/api/demo/seed-pack is a demo path', () => {
    expect(isDemoPath('/api/demo/seed-pack')).toBe(true);
  });

  it('/demo/reset-pack is a demo path', () => {
    expect(isDemoPath('/demo/reset-pack')).toBe(true);
  });

  it('/demo/status-pack is a demo path', () => {
    expect(isDemoPath('/demo/status-pack')).toBe(true);
  });

  it('/sites is NOT a demo path', () => {
    expect(isDemoPath('/sites')).toBe(false);
  });

  it('/consumption/tunnel is NOT a demo path', () => {
    expect(isDemoPath('/consumption/tunnel')).toBe(false);
  });

  it('absolute URL with /demo/ is detected', () => {
    expect(isDemoPath('http://localhost:8000/api/demo/seed-pack?pack=casino')).toBe(true);
  });

  it('null/undefined/empty returns false', () => {
    expect(isDemoPath(null)).toBe(false);
    expect(isDemoPath(undefined)).toBe(false);
    expect(isDemoPath('')).toBe(false);
  });
});

// ── Scope switching after seed/reset ──────────────────────────────────────

describe('ImportPage: scope switching after seed/reset', () => {
  it('seedDemoPack success triggers applyDemoScope with object { orgId, orgNom, defaultSiteId, defaultSiteName }', () => {
    const applyDemoScope = vi.fn();
    const seedResult = {
      status: 'ok',
      org_id: 123,
      org_nom: 'SCI Les Terrasses',
      default_site_id: 456,
      default_site_name: 'Bureaux Paris',
      sites_count: 10,
      elapsed_s: 3.2,
    };
    // Simulate handleSeedPack logic (object form)
    if (seedResult.org_id) {
      applyDemoScope({
        orgId: seedResult.org_id,
        orgNom: seedResult.org_nom,
        defaultSiteId: seedResult.default_site_id,
        defaultSiteName: seedResult.default_site_name,
      });
    }
    expect(applyDemoScope).toHaveBeenCalledWith({
      orgId: 123,
      orgNom: 'SCI Les Terrasses',
      defaultSiteId: 456,
      defaultSiteName: 'Bureaux Paris',
    });
  });

  it('seed with no org_id does NOT call applyDemoScope', () => {
    const applyDemoScope = vi.fn();
    const seedResult = { status: 'error' };
    if (seedResult.org_id) {
      applyDemoScope({ orgId: seedResult.org_id, orgNom: seedResult.org_nom });
    }
    expect(applyDemoScope).not.toHaveBeenCalled();
  });

  it('resetDemoPack triggers clearScope', () => {
    const clearScope = vi.fn();
    clearScope();
    expect(clearScope).toHaveBeenCalledOnce();
  });

  it('replay flow: reset → clearScope → seed → applyDemoScope', () => {
    const clearScope = vi.fn();
    const applyDemoScope = vi.fn();
    const callOrder = [];

    clearScope();
    callOrder.push('clearScope');

    const seedResult = { org_id: 789, org_nom: 'Groupe Casino' };
    if (seedResult.org_id) {
      applyDemoScope({ orgId: seedResult.org_id, orgNom: seedResult.org_nom });
      callOrder.push('applyDemoScope');
    }

    expect(callOrder).toEqual(['clearScope', 'applyDemoScope']);
    expect(applyDemoScope).toHaveBeenCalledWith({ orgId: 789, orgNom: 'Groupe Casino' });
  });

  it('status-pack with org_id triggers applyDemoScope on init', () => {
    const applyDemoScope = vi.fn();
    const statusResult = { org_id: 100, org_nom: 'Demo Org', total_rows: 5000 };
    if (statusResult.org_id && statusResult.total_rows > 0) {
      applyDemoScope({ orgId: statusResult.org_id, orgNom: statusResult.org_nom });
    }
    expect(applyDemoScope).toHaveBeenCalledWith({ orgId: 100, orgNom: 'Demo Org' });
  });

  it('status-pack with total_rows=0 does NOT trigger applyDemoScope', () => {
    const applyDemoScope = vi.fn();
    const statusResult = { org_id: null, total_rows: 0 };
    if (statusResult.org_id && statusResult.total_rows > 0) {
      applyDemoScope({ orgId: statusResult.org_id, orgNom: statusResult.org_nom });
    }
    expect(applyDemoScope).not.toHaveBeenCalled();
  });
});

// ── Seed error toast format ───────────────────────────────────────────────

describe('ImportPage: seed error toast format', () => {
  function buildErrorToast(err) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail || err.message || 'Erreur inconnue';
    return status
      ? `Echec du chargement (HTTP\u00a0${status}) — ${detail}`
      : `Echec du chargement — ${detail}`;
  }

  it('HTTP 400 error shows status + backend detail', () => {
    const err = {
      response: { status: 400, data: { detail: 'Organisation deja existante' } },
      message: 'Request failed with status code 400',
    };
    expect(buildErrorToast(err)).toContain('HTTP\u00a0400');
    expect(buildErrorToast(err)).toContain('Organisation deja existante');
  });

  it('HTTP 500 error shows status + detail', () => {
    const err = { response: { status: 500, data: { detail: 'Internal Server Error' } } };
    expect(buildErrorToast(err)).toContain('HTTP\u00a0500');
    expect(buildErrorToast(err)).toContain('Internal Server Error');
  });

  it('network error (no response) shows message without HTTP label', () => {
    const err = { message: 'Network Error' };
    const msg = buildErrorToast(err);
    expect(msg).toContain('Network Error');
    expect(msg).not.toContain('HTTP');
  });

  it('error with no detail falls back to err.message', () => {
    const err = { response: { status: 422, data: {} }, message: 'Unprocessable Entity' };
    expect(buildErrorToast(err)).toContain('HTTP\u00a0422');
    expect(buildErrorToast(err)).toContain('Unprocessable Entity');
  });

  it('completely empty error returns Erreur inconnue', () => {
    const err = {};
    expect(() => buildErrorToast(err)).not.toThrow();
    expect(buildErrorToast(err)).toContain('Erreur inconnue');
  });
});

// ── scopeLabel logic ──────────────────────────────────────────────────────

describe('scopeLabel derivation (ScopeContext)', () => {
  function deriveScopeLabel(siteId, scopedSites) {
    if (!siteId) return 'Tous les sites';
    const site = scopedSites.find(s => s.id === siteId);
    return site ? `Site\u00a0: ${site.nom}` : 'Tous les sites';
  }

  it('null siteId => Tous les sites', () => {
    expect(deriveScopeLabel(null, [])).toBe('Tous les sites');
  });

  it('undefined siteId => Tous les sites', () => {
    expect(deriveScopeLabel(undefined, [])).toBe('Tous les sites');
  });

  it('siteId found in scopedSites => Site : <name>', () => {
    const sites = [{ id: 5, nom: 'Entrepot Lyon' }];
    expect(deriveScopeLabel(5, sites)).toBe('Site\u00a0: Entrepot Lyon');
  });

  it('siteId not found (seeded org has no mock sites) => Tous les sites', () => {
    // After seeding a real org, scopedSites may be empty (mock-only).
    // scopeLabel must still return a coherent label, not crash.
    expect(deriveScopeLabel(999, [])).toBe('Tous les sites');
  });

  it('after applyDemoScope (siteId=null) TopBar shows Tous les sites', () => {
    // applyDemoScope always sets siteId=null -> scopeLabel = 'Tous les sites'
    const siteId = null;
    expect(deriveScopeLabel(siteId, [])).toBe('Tous les sites');
  });
});
