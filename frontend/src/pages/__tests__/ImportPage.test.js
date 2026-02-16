/**
 * PROMEOS — Tests for ImportPage silent status-pack behavior.
 * Ensures 404 on /demo/status-pack does NOT trigger a toast.
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
