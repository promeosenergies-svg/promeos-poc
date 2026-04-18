/**
 * PROMEOS — nps.js helper tests (Sprint CX P1 residual)
 * Couvre le trigger J+30 et l'anti-resubmit 90j via localStorage.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  shouldShowNps,
  markNpsSubmitted,
  markNpsDismissed,
  NPS_LAST_SUBMIT_KEY,
  NPS_DISMISSED_KEY,
} from '../nps';

const store = {};
const localStorageMock = {
  getItem: vi.fn((key) => store[key] ?? null),
  setItem: vi.fn((key, val) => {
    store[key] = val;
  }),
  removeItem: vi.fn((key) => {
    delete store[key];
  }),
};
vi.stubGlobal('localStorage', localStorageMock);

beforeEach(() => {
  Object.keys(store).forEach((k) => delete store[k]);
  vi.clearAllMocks();
});

const DAY = 24 * 60 * 60 * 1000;

describe('shouldShowNps', () => {
  it('returns false when userCreatedAt is null', () => {
    expect(shouldShowNps(null)).toBe(false);
  });

  it('returns false when userCreatedAt is invalid', () => {
    expect(shouldShowNps('not-a-date')).toBe(false);
  });

  it('returns false when account age < 30 days', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 10 * DAY); // 10 days old
    expect(shouldShowNps(created, now)).toBe(false);
  });

  it('returns true when account age >= 30 days and no prior submission', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 35 * DAY);
    expect(shouldShowNps(created, now)).toBe(true);
  });

  it('returns false when last submission < 90 days ago', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 60 * DAY);
    store[NPS_LAST_SUBMIT_KEY] = new Date(now.getTime() - 10 * DAY).toISOString();
    expect(shouldShowNps(created, now)).toBe(false);
  });

  it('returns true when last submission > 90 days ago', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 180 * DAY);
    store[NPS_LAST_SUBMIT_KEY] = new Date(now.getTime() - 100 * DAY).toISOString();
    expect(shouldShowNps(created, now)).toBe(true);
  });

  it('returns false when dismissed is in the future', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 60 * DAY);
    store[NPS_DISMISSED_KEY] = new Date(now.getTime() + 10 * DAY).toISOString();
    expect(shouldShowNps(created, now)).toBe(false);
  });

  it('returns true when dismissed is in the past', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 60 * DAY);
    store[NPS_DISMISSED_KEY] = new Date(now.getTime() - 1 * DAY).toISOString();
    expect(shouldShowNps(created, now)).toBe(true);
  });

  it('accepts string date input', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    expect(shouldShowNps('2026-01-01T00:00:00Z', now)).toBe(true);
  });
});

describe('markNpsSubmitted', () => {
  it('writes ISO timestamp to localStorage', () => {
    const now = new Date('2026-04-17T12:00:00Z');
    markNpsSubmitted(now);
    expect(store[NPS_LAST_SUBMIT_KEY]).toBe(now.toISOString());
  });

  it('once marked, disables shouldShowNps within 90j', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    const created = new Date(now.getTime() - 120 * DAY);
    markNpsSubmitted(now);
    expect(shouldShowNps(created, now)).toBe(false);
  });
});

describe('markNpsDismissed', () => {
  it('writes a future ISO timestamp N days ahead', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    markNpsDismissed(15, now);
    const stored = new Date(store[NPS_DISMISSED_KEY]);
    const diff = (stored.getTime() - now.getTime()) / DAY;
    expect(diff).toBeCloseTo(15, 1);
  });

  it('defaults to 30 days', () => {
    const now = new Date('2026-04-17T00:00:00Z');
    markNpsDismissed(undefined, now);
    const stored = new Date(store[NPS_DISMISSED_KEY]);
    const diff = (stored.getTime() - now.getTime()) / DAY;
    expect(diff).toBeCloseTo(30, 1);
  });
});
