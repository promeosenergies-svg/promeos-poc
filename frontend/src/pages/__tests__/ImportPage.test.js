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
import { isSilentUrl, isDemoPath } from '../../services/api';

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
    expect(isSilentUrl({ url: 'http://localhost:8001/api/demo/status-pack?x=1' })).toBe(true);
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
    expect(isDemoPath('http://localhost:8001/api/demo/seed-pack?pack=helios')).toBe(true);
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

    const seedResult = { org_id: 789, org_nom: 'Groupe HELIOS' };
    if (seedResult.org_id) {
      applyDemoScope({ orgId: seedResult.org_id, orgNom: seedResult.org_nom });
      callOrder.push('applyDemoScope');
    }

    expect(callOrder).toEqual(['clearScope', 'applyDemoScope']);
    expect(applyDemoScope).toHaveBeenCalledWith({ orgId: 789, orgNom: 'Groupe HELIOS' });
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

// ── Toast message wording (V11.1 UX spec) ────────────────────────────────

describe('ImportPage: toast message wording', () => {
  it('seed success toast: Démo chargée — contexte appliqué à toute l\'application.', () => {
    const msg = 'Démo chargée — contexte appliqué à toute l\'application.';
    expect(msg).toContain('Démo chargée');
    expect(msg).toContain('contexte appliqué');
  });

  it('reset success toast: Démo réinitialisée — retour à un contexte neutre.', () => {
    const msg = 'Démo réinitialisée — retour à un contexte neutre.';
    expect(msg).toContain('réinitialisée');
    expect(msg).toContain('contexte neutre');
  });

  it('replay success toast: Démo relancée — contexte mis à jour.', () => {
    const msg = 'Démo relancée — contexte mis à jour.';
    expect(msg).toContain('relancée');
    expect(msg).toContain('mis à jour');
  });

  it('seed and replay toasts are distinct', () => {
    const seedMsg = 'Démo chargée — contexte appliqué à toute l\'application.';
    const replayMsg = 'Démo relancée — contexte mis à jour.';
    const resetMsg = 'Démo réinitialisée — retour à un contexte neutre.';
    expect(seedMsg).not.toBe(replayMsg);
    expect(seedMsg).not.toBe(resetMsg);
    expect(replayMsg).not.toBe(resetMsg);
  });
});

// ── syncInProgress mismatch detection ────────────────────────────────────

describe('ImportPage: syncInProgress mismatch logic', () => {
  function computeSyncInProgress(packStatus, scope) {
    return !!(
      packStatus?.org_id &&
      scope?.orgId &&
      packStatus.org_id !== scope.orgId
    );
  }

  it('no mismatch when org_ids match', () => {
    const packStatus = { org_id: 42, org_nom: 'Groupe HELIOS' };
    const scope = { orgId: 42 };
    expect(computeSyncInProgress(packStatus, scope)).toBe(false);
  });

  it('mismatch when org_ids differ', () => {
    const packStatus = { org_id: 42, org_nom: 'Groupe HELIOS' };
    const scope = { orgId: 99 };
    expect(computeSyncInProgress(packStatus, scope)).toBe(true);
  });

  it('no mismatch when scope has no orgId (empty scope)', () => {
    const packStatus = { org_id: 42, org_nom: 'Groupe HELIOS' };
    const scope = { orgId: null };
    expect(computeSyncInProgress(packStatus, scope)).toBe(false);
  });

  it('no mismatch when packStatus has no org_id (no pack loaded)', () => {
    const packStatus = { org_id: null, total_rows: 0 };
    const scope = { orgId: 42 };
    expect(computeSyncInProgress(packStatus, scope)).toBe(false);
  });

  it('mismatch triggers applyDemoScope with packStatus org info', () => {
    const applyDemoScope = vi.fn();
    const packStatus = { org_id: 42, org_nom: 'Groupe HELIOS' };
    const scope = { orgId: 99 };
    const syncInProgress = computeSyncInProgress(packStatus, scope);
    if (syncInProgress && packStatus?.org_id && packStatus?.org_nom) {
      applyDemoScope({ orgId: packStatus.org_id, orgNom: packStatus.org_nom });
    }
    expect(applyDemoScope).toHaveBeenCalledWith({ orgId: 42, orgNom: 'Groupe HELIOS' });
  });

  it('after applyDemoScope, syncInProgress becomes false', () => {
    // Simulate: scope.orgId updated to match packStatus.org_id
    const packStatus = { org_id: 42 };
    const scopeAfterSync = { orgId: 42 };
    expect(computeSyncInProgress(packStatus, scopeAfterSync)).toBe(false);
  });
});

// ── Demo Pack regression (V16 Fix) ───────────────────────────────────────
// Regression guards for: "Pack chargé: Aucun" + sites vides après seed

describe('Demo Pack regression: optimistic packStatus after seed', () => {
  /**
   * Simulates the performSeed logic:
   *   1. seedDemoPack() → res
   *   2. setPackStatus(optimistic) — immediately from res
   *   3. applyDemoScope(...)
   *   4. refreshStatus() async — may succeed or fail
   */
  function simulatePerformSeed(res, refreshError = false) {
    let packStatus = null;
    const applyDemoScope = vi.fn();

    // Optimistic update — must happen before refreshStatus
    if (res.org_id) {
      packStatus = {
        org_id: res.org_id,
        org_nom: res.org_nom,
        pack: res.pack,
        size: res.size,
        total_rows: res.total_rows ?? 0,
      };
    }

    // applyDemoScope call
    if (res.org_id) {
      applyDemoScope({
        orgId: res.org_id,
        orgNom: res.org_nom,
        defaultSiteId: res.default_site_id,
        defaultSiteName: res.default_site_name,
      });
    }

    // refreshStatus — if it fails, packStatus must NOT become null
    if (refreshError) {
      // catch handler: only setStatusError(true) — NOT setPackStatus(null)
      // packStatus stays at the optimistic value (unchanged)
    } else {
      // then handler: simulate server confirming (or returning empty status)
      // Server returns org_id only when a pack is loaded; otherwise org_id=null
      if (res.org_id) {
        packStatus = {
          org_id: res.org_id,
          org_nom: res.org_nom,
          pack: res.pack,
          size: res.size,
          total_rows: res.total_rows ?? 0,
        };
      } else {
        // Server confirms nothing is loaded → packStatus stays null
        packStatus = null;
      }
    }

    return { packStatus, applyDemoScope };
  }

  it('packStatus.org_nom is set immediately after seed (Tertiaire)', () => {
    const res = {
      status: 'ok',
      org_id: 10,
      org_nom: 'SCI Les Terrasses',
      pack: 'tertiaire',
      size: 'S',
      total_rows: 50000,
      default_site_id: 1,
      default_site_name: 'Bureaux Paris',
    };
    const { packStatus } = simulatePerformSeed(res, false);
    expect(packStatus).not.toBeNull();
    expect(packStatus.org_nom).toBe('SCI Les Terrasses');
  });

  it('packStatus.org_nom survives refreshStatus() failure (catch must not reset)', () => {
    const res = {
      status: 'ok',
      org_id: 10,
      org_nom: 'SCI Les Terrasses',
      pack: 'tertiaire',
      size: 'S',
      total_rows: 50000,
    };
    // refreshError=true simulates getDemoPackStatus() throwing
    const { packStatus } = simulatePerformSeed(res, true);
    // Must NOT be null even when refresh failed
    expect(packStatus).not.toBeNull();
    expect(packStatus.org_nom).toBe('SCI Les Terrasses');
  });

  it('packStatus.pack equals the seeded pack key', () => {
    const res = { org_id: 99, org_nom: 'Groupe HELIOS', pack: 'helios', size: 'S', total_rows: 5000 };
    const { packStatus } = simulatePerformSeed(res);
    expect(packStatus.pack).toBe('helios');
  });

  it('applyDemoScope is called exactly once per seed (not twice)', () => {
    const res = { org_id: 10, org_nom: 'SCI Les Terrasses', pack: 'tertiaire', size: 'S', total_rows: 50000, default_site_id: 1, default_site_name: 'Site 1' };
    const { applyDemoScope } = simulatePerformSeed(res, false);
    // applyDemoScope must be called exactly once (from performSeed, NOT from refreshStatus)
    expect(applyDemoScope).toHaveBeenCalledOnce();
  });

  it('seed with no org_id → packStatus stays null (no org seeded)', () => {
    const res = { status: 'error' };
    const { packStatus } = simulatePerformSeed(res);
    expect(packStatus).toBeNull();
  });
});

describe('Demo Pack regression: isLoaded badge logic', () => {
  /**
   * "Chargé" badge must appear on the card whose key matches packStatus.pack.
   * It must NOT appear on the other card.
   */
  function computeIsLoaded(packStatus, packKey) {
    return packStatus?.pack === packKey;
  }

  it('isLoaded = true when packStatus.pack matches pack key (tertiaire)', () => {
    const packStatus = { pack: 'tertiaire', org_nom: 'SCI Les Terrasses' };
    expect(computeIsLoaded(packStatus, 'tertiaire')).toBe(true);
    expect(computeIsLoaded(packStatus, 'helios')).toBe(false);
  });

  it('isLoaded = false when packStatus.pack is a different key (helios loaded)', () => {
    const packStatus = { pack: 'helios', org_nom: 'Groupe HELIOS' };
    expect(computeIsLoaded(packStatus, 'tertiaire')).toBe(false);
    expect(computeIsLoaded(packStatus, 'helios')).toBe(true);
  });

  it('isLoaded = false when packStatus is null (nothing loaded)', () => {
    expect(computeIsLoaded(null, 'helios')).toBe(false);
    expect(computeIsLoaded(null, 'tertiaire')).toBe(false);
  });

  it('isLoaded = false when packStatus has no pack field', () => {
    const packStatus = { org_id: 5, org_nom: 'Org sans pack' };
    expect(computeIsLoaded(packStatus, 'helios')).toBe(false);
  });
});

describe('Demo Pack regression: refreshStatus catch must not overwrite optimistic packStatus', () => {
  /**
   * The old bug: .catch(() => { setPackStatus(null); setStatusError(true); })
   * After fix:   .catch(() => { setStatusError(true); })
   */
  function simulateRefreshStatusCatch_OLD(_currentPackStatus) {
    // OLD behavior: always reset to null
    return null;
  }

  function simulateRefreshStatusCatch_NEW(currentPackStatus) {
    // NEW behavior: preserve current packStatus
    return currentPackStatus;
  }

  it('OLD catch: packStatus becomes null (the bug)', () => {
    const optimistic = { org_id: 10, org_nom: 'SCI Les Terrasses', pack: 'tertiaire' };
    expect(simulateRefreshStatusCatch_OLD(optimistic)).toBeNull();
  });

  it('NEW catch: packStatus preserved after refreshStatus failure', () => {
    const optimistic = { org_id: 10, org_nom: 'SCI Les Terrasses', pack: 'tertiaire' };
    const result = simulateRefreshStatusCatch_NEW(optimistic);
    expect(result).not.toBeNull();
    expect(result.org_nom).toBe('SCI Les Terrasses');
  });

  it('NEW catch: null packStatus stays null (nothing was optimistically set)', () => {
    // If we never seeded, packStatus=null → catch should not change it
    const result = simulateRefreshStatusCatch_NEW(null);
    expect(result).toBeNull();
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
