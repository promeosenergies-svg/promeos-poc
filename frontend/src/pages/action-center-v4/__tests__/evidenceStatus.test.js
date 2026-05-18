/**
 * M2-5.3.B — Tests du helper deriveEvidenceStatus (environnement node, pur).
 */
import { describe, expect, test } from 'vitest';

import { deriveEvidenceStatus } from '../utils/evidenceStatus';

describe('deriveEvidenceStatus', () => {
  test('returns pending when verified_at is null', () => {
    expect(deriveEvidenceStatus({ verified_at: null })).toBe('pending');
  });

  test('returns pending when verified_at is undefined', () => {
    expect(deriveEvidenceStatus({})).toBe('pending');
  });

  test('returns pending when evidence is null', () => {
    expect(deriveEvidenceStatus(null)).toBe('pending');
  });

  test('returns verified when verified_at is set and there is no expiry', () => {
    expect(
      deriveEvidenceStatus({
        verified_at: '2026-05-01T00:00:00Z',
        expires_at: null,
      })
    ).toBe('verified');
  });

  test('returns verified when verified_at is set and expiry is in the future', () => {
    const future = new Date(Date.now() + 86400000).toISOString();
    expect(
      deriveEvidenceStatus({
        verified_at: '2026-05-01T00:00:00Z',
        expires_at: future,
      })
    ).toBe('verified');
  });

  test('returns expired when verified_at is set and expiry is in the past', () => {
    const now = new Date('2026-05-18T00:00:00Z');
    expect(
      deriveEvidenceStatus(
        { verified_at: '2026-04-01T00:00:00Z', expires_at: '2026-05-01T00:00:00Z' },
        now
      )
    ).toBe('expired');
  });
});
