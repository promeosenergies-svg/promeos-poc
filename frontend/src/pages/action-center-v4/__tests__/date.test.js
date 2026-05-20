/**
 * M2-5.3.A / M2-5.10.B.bis — Tests des utilitaires date FR (logique pure).
 */
import { describe, expect, test } from 'vitest';

import { daysSince, formatDateTimeFR, formatRelativeDate } from '../utils/date';

describe('formatRelativeDate', () => {
  test('returns « — » for null/undefined/invalid', () => {
    expect(formatRelativeDate(null)).toBe('—');
    expect(formatRelativeDate(undefined)).toBe('—');
    expect(formatRelativeDate('not-a-date')).toBe('—');
  });

  // ── M2-5.10.bis clôture — `now` injectable (cohérent daysSince) ─
  test("returns « aujourd'hui » for same-day with injected now", () => {
    const now = new Date('2026-05-20T10:00:00Z');
    expect(formatRelativeDate('2026-05-20T09:00:00Z', now)).toBe("aujourd'hui");
  });

  test('returns « hier » for D-1 with injected now', () => {
    const now = new Date('2026-05-20T10:00:00Z');
    expect(formatRelativeDate('2026-05-19T10:00:00Z', now)).toBe('hier');
  });

  test('returns « il y a N jours » for 2-6 days with injected now', () => {
    const now = new Date('2026-05-20T10:00:00Z');
    expect(formatRelativeDate('2026-05-17T10:00:00Z', now)).toBe('il y a 3 jours');
  });

  test('returns « DD/MM » beyond 7 days with injected now', () => {
    const now = new Date('2026-05-20T10:00:00Z');
    expect(formatRelativeDate('2026-05-10T10:00:00Z', now)).toMatch(/^\d{2}\/\d{2}$/);
  });
});

describe('formatDateTimeFR', () => {
  test('returns « — » for null/undefined/invalid', () => {
    expect(formatDateTimeFR(null)).toBe('—');
    expect(formatDateTimeFR(undefined)).toBe('—');
    expect(formatDateTimeFR('not-a-date')).toBe('—');
  });

  test('renders day/month/year + hour:minute for a valid ISO', () => {
    // Date fixée pour test déterministe (timezone navigateur indifférent — on
    // vérifie juste qu'on a 4 chiffres pour l'année).
    const out = formatDateTimeFR('2026-05-19T10:30:00Z');
    expect(out).toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
});

describe('daysSince (M2-5.10.B.bis)', () => {
  test('returns null for null/undefined/invalid', () => {
    expect(daysSince(null)).toBeNull();
    expect(daysSince(undefined)).toBeNull();
    expect(daysSince('not-a-date')).toBeNull();
  });

  test('returns 0 for the current moment (injectable now)', () => {
    const now = new Date('2026-05-19T10:00:00Z');
    expect(daysSince('2026-05-19T09:00:00Z', now)).toBe(0);
  });

  test('returns the exact number of days for past dates', () => {
    const now = new Date('2026-05-19T10:00:00Z');
    expect(daysSince('2026-05-18T10:00:00Z', now)).toBe(1);
    expect(daysSince('2026-05-12T10:00:00Z', now)).toBe(7);
    expect(daysSince('2026-04-19T10:00:00Z', now)).toBe(30);
  });

  test('clamps to 0 for future dates (defensive — clock skew)', () => {
    const now = new Date('2026-05-19T10:00:00Z');
    expect(daysSince('2026-05-20T10:00:00Z', now)).toBe(0);
  });

  test('uses the current time as default if `now` is omitted', () => {
    // Test indirect : un ISO d'il y a 1 jour doit retourner 1.
    const yesterday = new Date(Date.now() - 86400000).toISOString();
    expect(daysSince(yesterday)).toBe(1);
  });
});
