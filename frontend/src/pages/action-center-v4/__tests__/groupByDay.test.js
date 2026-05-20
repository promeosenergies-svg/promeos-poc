/**
 * M2-5.10.E — Tests de `groupEventsByDay` (logique pure, env node).
 */
import { describe, expect, test } from 'vitest';

import { groupEventsByDay } from '../utils/groupByDay';

const fixedNow = new Date('2026-05-20T10:00:00Z');

function ev(occurred_at) {
  return { id: occurred_at, occurred_at };
}

describe('groupEventsByDay', () => {
  test('returns empty array for empty/null/undefined input', () => {
    expect(groupEventsByDay([])).toEqual([]);
    expect(groupEventsByDay(null)).toEqual([]);
    expect(groupEventsByDay(undefined)).toEqual([]);
  });

  test('groups events of the same day together', () => {
    const groups = groupEventsByDay(
      [ev('2026-05-20T09:00:00Z'), ev('2026-05-20T03:00:00Z'), ev('2026-05-19T15:00:00Z')],
      { now: fixedNow }
    );
    expect(groups.length).toBe(2);
    expect(groups[0].events.length).toBe(2);
    expect(groups[1].events.length).toBe(1);
  });

  test("labels today as « Aujourd'hui »", () => {
    const groups = groupEventsByDay([ev('2026-05-20T09:00:00Z')], { now: fixedNow });
    expect(groups[0].label).toBe("Aujourd'hui");
  });

  test('labels yesterday as « Hier »', () => {
    const groups = groupEventsByDay([ev('2026-05-19T09:00:00Z')], { now: fixedNow });
    expect(groups[0].label).toBe('Hier');
  });

  test('labels older days as long FR weekday + date', () => {
    const groups = groupEventsByDay([ev('2026-05-15T09:00:00Z')], { now: fixedNow });
    // « vendredi 15 mai 2026 » (toLocaleDateString FR).
    expect(groups[0].label).toMatch(/vendredi/i);
    expect(groups[0].label).toMatch(/15 mai/);
  });

  test('preserves backend DESC order across groups', () => {
    const groups = groupEventsByDay(
      [
        ev('2026-05-20T10:00:00Z'),
        ev('2026-05-19T18:00:00Z'),
        ev('2026-05-19T08:00:00Z'),
        ev('2026-05-18T12:00:00Z'),
      ],
      { now: fixedNow }
    );
    expect(groups.map((g) => g.label)).toEqual(["Aujourd'hui", 'Hier', expect.any(String)]);
  });

  test('skips events with missing or invalid occurred_at', () => {
    const groups = groupEventsByDay(
      [ev('2026-05-20T10:00:00Z'), { id: 'bad' }, { id: 'bad2', occurred_at: 'not-a-date' }],
      { now: fixedNow }
    );
    expect(groups.length).toBe(1);
    expect(groups[0].events.length).toBe(1);
  });

  test('each group exposes a dayKey ISO-shaped (YYYY-MM-DD)', () => {
    const groups = groupEventsByDay([ev('2026-05-20T10:00:00Z')], { now: fixedNow });
    expect(groups[0].dayKey).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
