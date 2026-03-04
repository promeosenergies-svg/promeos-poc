/**
 * PROMEOS — Tests for API client silent-request pattern.
 * Covers: isSilentUrl, normalizePathFromAxiosConfig, SILENT_URLS contract.
 */
import { describe, it, expect } from 'vitest';
import { isSilentUrl, normalizePathFromAxiosConfig } from '../api';

describe('normalizePathFromAxiosConfig', () => {
  it('joins baseURL + relative url', () => {
    expect(normalizePathFromAxiosConfig({ baseURL: '/api', url: '/demo/status-pack' })).toBe(
      '/api/demo/status-pack'
    );
  });

  it('handles missing leading slash on url', () => {
    expect(normalizePathFromAxiosConfig({ baseURL: '/api', url: 'demo/status-pack' })).toBe(
      '/api/demo/status-pack'
    );
  });

  it('strips protocol and host from absolute URL', () => {
    expect(
      normalizePathFromAxiosConfig({ url: 'http://localhost:8001/api/demo/status-pack' })
    ).toBe('/api/demo/status-pack');
  });

  it('strips querystring and hash', () => {
    expect(normalizePathFromAxiosConfig({ url: '/demo/status-pack?x=1#foo' })).toBe(
      '/demo/status-pack'
    );
  });

  it('strips querystring from absolute URL', () => {
    expect(
      normalizePathFromAxiosConfig({ url: 'http://localhost:8001/api/demo/status-pack?x=1' })
    ).toBe('/api/demo/status-pack');
  });

  it('handles null/undefined config', () => {
    expect(normalizePathFromAxiosConfig(null)).toBe('');
    expect(normalizePathFromAxiosConfig(undefined)).toBe('');
  });

  it('handles config with no url', () => {
    expect(normalizePathFromAxiosConfig({})).toBe('');
  });

  it('does not prepend baseURL to absolute url', () => {
    expect(
      normalizePathFromAxiosConfig({
        baseURL: '/api',
        url: 'http://localhost:8001/demo/status-pack',
      })
    ).toBe('/demo/status-pack');
  });
});

describe('isSilentUrl', () => {
  // String inputs (legacy)
  it('marks /demo/status-pack as silent (string)', () => {
    expect(isSilentUrl('/demo/status-pack')).toBe(true);
  });

  it('marks full URL with status-pack as silent (string)', () => {
    expect(isSilentUrl('/api/demo/status-pack')).toBe(true);
  });

  it('does NOT mark /demo/seed-pack as silent', () => {
    expect(isSilentUrl('/demo/seed-pack')).toBe(false);
  });

  it('does NOT mark /demo/reset-pack as silent', () => {
    expect(isSilentUrl('/demo/reset-pack')).toBe(false);
  });

  it('does NOT mark /sites as silent', () => {
    expect(isSilentUrl('/sites')).toBe(false);
  });

  it('handles null/undefined gracefully', () => {
    expect(isSilentUrl(null)).toBe(false);
    expect(isSilentUrl(undefined)).toBe(false);
  });

  // Config object inputs (V5.0 robust matching)
  it('matches config: relative url without baseURL', () => {
    expect(isSilentUrl({ url: '/demo/status-pack' })).toBe(true);
  });

  it('matches config: url without leading slash', () => {
    expect(isSilentUrl({ url: 'demo/status-pack' })).toBe(true);
  });

  it('matches config: baseURL /api + relative url', () => {
    expect(isSilentUrl({ baseURL: '/api', url: '/demo/status-pack' })).toBe(true);
  });

  it('matches config: absolute URL', () => {
    expect(isSilentUrl({ url: 'http://localhost:8001/api/demo/status-pack' })).toBe(true);
  });

  it('matches config: absolute URL with querystring', () => {
    expect(isSilentUrl({ url: 'http://localhost:8001/api/demo/status-pack?x=1' })).toBe(true);
  });

  it('does NOT match config: /demo/seed-pack', () => {
    expect(isSilentUrl({ baseURL: '/api', url: '/demo/seed-pack' })).toBe(false);
  });

  it('does NOT match config: /demo/reset-pack', () => {
    expect(isSilentUrl({ baseURL: '/api', url: '/demo/reset-pack' })).toBe(false);
  });
});
