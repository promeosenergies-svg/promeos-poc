/**
 * M2-5.2 — Tests des constantes UI (environnement node, logique pure).
 */
import { describe, expect, test } from 'vitest';

import {
  LIFECYCLE_BADGE_VARIANTS,
  LIFECYCLE_LABELS,
  LIFECYCLE_ORDER,
  KIND_LABELS,
  PRIORITY_LABELS,
  PRIORITY_BADGE_VARIANTS,
  PRIORITY_ORDER,
} from '../constants';

describe('M2-5.2 constants', () => {
  test('LIFECYCLE_LABELS has the 5 doctrinal states', () => {
    expect(Object.keys(LIFECYCLE_LABELS).sort()).toEqual([
      'closed',
      'in_progress',
      'new',
      'planned',
      'triaged',
    ]);
  });

  test('LIFECYCLE_ORDER respects the chronological order', () => {
    expect(LIFECYCLE_ORDER).toEqual(['new', 'triaged', 'planned', 'in_progress', 'closed']);
  });

  test('LIFECYCLE_BADGE_VARIANTS covers exactly all states', () => {
    expect(Object.keys(LIFECYCLE_BADGE_VARIANTS).sort()).toEqual(
      Object.keys(LIFECYCLE_LABELS).sort()
    );
  });

  test('closed maps to the "ok" Badge status', () => {
    expect(LIFECYCLE_BADGE_VARIANTS.closed).toBe('ok');
  });

  test('in_progress maps to the "warn" Badge status', () => {
    expect(LIFECYCLE_BADGE_VARIANTS.in_progress).toBe('warn');
  });
});

describe('M2-5.8.B constants', () => {
  test('KIND_LABELS covers the 7 backend kind values', () => {
    expect(Object.keys(KIND_LABELS).sort()).toEqual([
      'action',
      'anomaly',
      'deadline',
      'decision',
      'evidence_request',
      'recommendation',
      'signal',
    ]);
  });

  test('PRIORITY_LABELS covers the 4 brackets', () => {
    expect(Object.keys(PRIORITY_LABELS).sort()).toEqual(['P0', 'P1', 'P2', 'P3']);
  });

  test('PRIORITY_BADGE_VARIANTS is aligned with PRIORITY_LABELS', () => {
    expect(Object.keys(PRIORITY_BADGE_VARIANTS).sort()).toEqual(
      Object.keys(PRIORITY_LABELS).sort()
    );
  });

  test('PRIORITY_ORDER goes from most to least urgent', () => {
    expect(PRIORITY_ORDER).toEqual(['P0', 'P1', 'P2', 'P3']);
  });

  test('P0 maps to the "crit" Badge status', () => {
    expect(PRIORITY_BADGE_VARIANTS.P0).toBe('crit');
  });
});
