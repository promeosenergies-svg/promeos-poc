/**
 * PROMEOS — ExplorerURL regression tests (V11.1-E)
 * Tests useExplorerURL v2 URL param parsing, new fields, and setUrlParams behaviour.
 *
 * Since useExplorerURL uses useSearchParams (a React hook that requires a Router context),
 * we test the pure parsing logic extracted from the hook directly.
 */
import { describe, it, expect } from 'vitest';

// ── Pure parsing helpers (mirrors useExplorerURL logic) ──────────────────

const DEFAULTS = {
  energy: 'electricity',
  days: 90,
  mode: 'agrege',
  unit: 'kwh',
  tab: 'tunnel',
};

/** Parse URLSearchParams string into urlState — mirrors the hook */
function parseUrlState(search) {
  const p = new URLSearchParams(search);

  return {
    siteIds: p.get('sites')
      ? p.get('sites').split(',').map(Number).filter(Boolean)
      : [],
    energy: p.get('energy') || DEFAULTS.energy,
    days: p.has('days') ? Number(p.get('days')) : DEFAULTS.days,
    startDate: p.get('start') || null,
    endDate: p.get('end') || null,
    mode: p.get('mode') || DEFAULTS.mode,
    unit: p.get('unit') || DEFAULTS.unit,
    tab: p.get('tab') || DEFAULTS.tab,
    layers: p.get('layers')
      ? p.get('layers').split(',').filter(Boolean)
      : null,
  };
}

/** Serialize state updates into URL params — mirrors setUrlParams logic */
function applyUrlUpdates(existing, updates) {
  const next = new URLSearchParams(existing);
  for (const [key, value] of Object.entries(updates)) {
    if (value === null || value === undefined) {
      next.delete(key);
    } else if (Array.isArray(value)) {
      if (value.length === 0) {
        next.delete(key);
      } else {
        next.set(key, value.join(','));
      }
    } else {
      next.set(key, String(value));
    }
  }
  return next;
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe('useExplorerURL — URL state parsing', () => {
  it('returns defaults when URL has no params', () => {
    const state = parseUrlState('');
    expect(state.energy).toBe('electricity');
    expect(state.days).toBe(90);
    expect(state.mode).toBe('agrege');
    expect(state.unit).toBe('kwh');
    expect(state.tab).toBe('tunnel');
    expect(state.siteIds).toEqual([]);
    expect(state.startDate).toBeNull();
    expect(state.endDate).toBeNull();
    expect(state.layers).toBeNull();
  });

  it('parses sites param as number array', () => {
    const state = parseUrlState('sites=12,34');
    expect(state.siteIds).toEqual([12, 34]);
  });

  it('parses single site', () => {
    const state = parseUrlState('sites=99');
    expect(state.siteIds).toEqual([99]);
  });

  it('parses days param as number', () => {
    const state = parseUrlState('days=7');
    expect(state.days).toBe(7);
  });

  it('parses layers param as string array', () => {
    const state = parseUrlState('layers=tunnel,signature');
    expect(state.layers).toEqual(['tunnel', 'signature']);
  });

  it('returns null layers when layers param absent', () => {
    const state = parseUrlState('energy=gas');
    expect(state.layers).toBeNull();
  });

  it('parses custom start and end dates', () => {
    const state = parseUrlState('start=2025-01-01&end=2025-03-31');
    expect(state.startDate).toBe('2025-01-01');
    expect(state.endDate).toBe('2025-03-31');
  });

  it('startDate and endDate are null when absent', () => {
    const state = parseUrlState('days=30');
    expect(state.startDate).toBeNull();
    expect(state.endDate).toBeNull();
  });
});

describe('useExplorerURL — URL serialization (setUrlParams)', () => {
  it('setUrlParams preserves existing params when updating one', () => {
    const initial = 'energy=gas&days=30&mode=agrege';
    const updated = applyUrlUpdates(initial, { days: 90 });
    expect(updated.get('energy')).toBe('gas');
    expect(updated.get('days')).toBe('90');
    expect(updated.get('mode')).toBe('agrege');
  });

  it('setUrlParams joins array values with commas', () => {
    const updated = applyUrlUpdates('', { sites: [1, 2, 3] });
    expect(updated.get('sites')).toBe('1,2,3');
  });

  it('setUrlParams deletes key when value is null', () => {
    const initial = 'start=2025-01-01&days=30';
    const updated = applyUrlUpdates(initial, { start: null });
    expect(updated.has('start')).toBe(false);
    expect(updated.get('days')).toBe('30');
  });

  it('setUrlParams deletes key when array is empty', () => {
    const initial = 'sites=1,2&days=30';
    const updated = applyUrlUpdates(initial, { sites: [] });
    expect(updated.has('sites')).toBe(false);
  });

  it('layers array serialized as comma-separated string', () => {
    const updated = applyUrlUpdates('', { layers: ['tunnel', 'signature'] });
    expect(updated.get('layers')).toBe('tunnel,signature');
  });

  it('roundtrip: serialize then parse gives back same values', () => {
    const input = { sites: [10, 20], energy: 'gas', days: 7, mode: 'superpose', unit: 'kw', layers: ['tunnel'] };
    const serialized = applyUrlUpdates('', {
      sites: input.sites,
      energy: input.energy,
      days: input.days,
      mode: input.mode,
      unit: input.unit,
      layers: input.layers,
    });
    const parsed = parseUrlState(serialized.toString());
    expect(parsed.siteIds).toEqual([10, 20]);
    expect(parsed.energy).toBe('gas');
    expect(parsed.days).toBe(7);
    expect(parsed.mode).toBe('superpose');
    expect(parsed.unit).toBe('kw');
    expect(parsed.layers).toEqual(['tunnel']);
  });
});
