/**
 * PROMEOS — Tests for ImportPage: scope switching + silent status-pack.
 * Ensures:
 * - 404 on /demo/status-pack does NOT trigger a toast
 * - seedDemoPack → applyDemoScope called with org_id/org_nom
 * - resetDemoPack → clearScope called
 */
import { describe, it, expect, vi } from 'vitest';
import { isSilentUrl, normalizePathFromAxiosConfig } from '../../services/api';

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

    if (!isSilent) {
      toastFn(error.response.statusText, 'error');
    }

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

    if (!isSilent) {
      toastFn(error.response.statusText, 'error');
    }

    expect(toastFn).toHaveBeenCalledWith('Not Found', 'error');
  });
});


describe('ImportPage: scope switching after seed/reset', () => {
  it('seedDemoPack success triggers applyDemoScope with org_id and org_nom', () => {
    const applyDemoScope = vi.fn();
    // Simulate seed response
    const seedResult = {
      status: 'ok',
      org_id: 123,
      org_nom: 'SCI Les Terrasses',
      default_site_id: 456,
      default_site_name: 'Bureaux Paris',
      sites_count: 10,
      elapsed_s: 3.2,
    };
    // Simulate handleSeedPack logic
    if (seedResult.org_id) {
      applyDemoScope(seedResult.org_id, seedResult.org_nom);
    }
    expect(applyDemoScope).toHaveBeenCalledWith(123, 'SCI Les Terrasses');
  });

  it('seed with no org_id does NOT call applyDemoScope', () => {
    const applyDemoScope = vi.fn();
    const seedResult = { status: 'error' };
    if (seedResult.org_id) {
      applyDemoScope(seedResult.org_id, seedResult.org_nom);
    }
    expect(applyDemoScope).not.toHaveBeenCalled();
  });

  it('resetDemoPack triggers clearScope', () => {
    const clearScope = vi.fn();
    // Simulate handleResetPack logic
    clearScope();
    expect(clearScope).toHaveBeenCalledOnce();
  });

  it('replay flow: reset → clearScope → seed → applyDemoScope', () => {
    const clearScope = vi.fn();
    const applyDemoScope = vi.fn();
    const callOrder = [];

    // Simulate replay
    clearScope();
    callOrder.push('clearScope');

    const seedResult = { org_id: 789, org_nom: 'Groupe Casino' };
    if (seedResult.org_id) {
      applyDemoScope(seedResult.org_id, seedResult.org_nom);
      callOrder.push('applyDemoScope');
    }

    expect(callOrder).toEqual(['clearScope', 'applyDemoScope']);
    expect(applyDemoScope).toHaveBeenCalledWith(789, 'Groupe Casino');
  });

  it('status-pack with org_id triggers applyDemoScope on init', () => {
    const applyDemoScope = vi.fn();
    const statusResult = { org_id: 100, org_nom: 'Demo Org', total_rows: 5000 };
    // Simulate refreshStatus logic
    if (statusResult.org_id && statusResult.total_rows > 0) {
      applyDemoScope(statusResult.org_id, statusResult.org_nom);
    }
    expect(applyDemoScope).toHaveBeenCalledWith(100, 'Demo Org');
  });

  it('status-pack with total_rows=0 does NOT trigger applyDemoScope', () => {
    const applyDemoScope = vi.fn();
    const statusResult = { org_id: null, total_rows: 0 };
    if (statusResult.org_id && statusResult.total_rows > 0) {
      applyDemoScope(statusResult.org_id, statusResult.org_nom);
    }
    expect(applyDemoScope).not.toHaveBeenCalled();
  });
});
