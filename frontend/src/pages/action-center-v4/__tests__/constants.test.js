/**
 * M2-5.2 — Tests des constantes UI (environnement node, logique pure).
 */
import { describe, expect, test } from 'vitest';

import { LIFECYCLE_BADGE_VARIANTS, LIFECYCLE_LABELS, LIFECYCLE_ORDER } from '../constants';

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
