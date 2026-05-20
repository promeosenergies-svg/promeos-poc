/**
 * M2-5.4 — Tests de la matrice lifecycle côté client (environnement node).
 */
import { describe, expect, test } from 'vitest';

import {
  USER_FACING_CLOSURE_REASONS,
  getAvailableTransitions,
  isTerminalState,
  transitionRequiresReason,
} from '../utils/lifecycleTransitions';

describe('getAvailableTransitions', () => {
  test('returns the 2 transitions available from new', () => {
    expect(
      getAvailableTransitions('new')
        .map((t) => t.to)
        .sort()
    ).toEqual(['closed', 'triaged']);
  });

  test('returns the single transition from in_progress', () => {
    expect(getAvailableTransitions('in_progress')).toEqual([
      { to: 'closed', requiresReason: true },
    ]);
  });

  test('returns nothing from closed (terminal state)', () => {
    expect(getAvailableTransitions('closed')).toEqual([]);
  });

  test('returns nothing for an unknown state', () => {
    expect(getAvailableTransitions('unknown')).toEqual([]);
  });
});

describe('transitionRequiresReason', () => {
  test('returns true for new → closed', () => {
    expect(transitionRequiresReason('new', 'closed')).toBe(true);
  });

  test('returns false for new → triaged', () => {
    expect(transitionRequiresReason('new', 'triaged')).toBe(false);
  });

  test('returns null for an invalid transition', () => {
    expect(transitionRequiresReason('new', 'in_progress')).toBeNull();
  });
});

describe('isTerminalState', () => {
  test('returns true for closed', () => {
    expect(isTerminalState('closed')).toBe(true);
  });

  test('returns false for every non-terminal state', () => {
    ['new', 'triaged', 'planned', 'in_progress'].forEach((s) =>
      expect(isTerminalState(s)).toBe(false)
    );
  });
});

test('USER_FACING_CLOSURE_REASONS holds the 3 doctrinal values', () => {
  expect([...USER_FACING_CLOSURE_REASONS].sort()).toEqual([
    'dismissed',
    'not_applicable',
    'resolved',
  ]);
});
