/**
 * PROMEOS — Tests for API client silent-request pattern.
 * Covers: isSilentUrl, SILENT_URLS contract.
 */
import { describe, it, expect } from 'vitest';
import { isSilentUrl } from '../api';

describe('isSilentUrl', () => {
  it('marks /demo/status-pack as silent', () => {
    expect(isSilentUrl('/demo/status-pack')).toBe(true);
  });

  it('marks full URL with status-pack as silent', () => {
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
});
