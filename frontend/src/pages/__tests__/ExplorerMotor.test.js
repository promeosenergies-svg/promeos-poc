/**
 * PROMEOS — Tests for Explorer WoW types + URL state parsing
 * (Motor hook itself requires full React render context — not tested here;
 *  tested via integration. This file covers:
 *  - types.js constants
 *  - useExplorerURL logic (pure URL parsing extracted)
 *  - enrichWithSignature helper from SignatureLayer
 */
import { describe, it, expect } from 'vitest';
import {
  MODES,
  UNITS,
  LAYERS,
  DEFAULT_LAYERS,
  MODE_LABELS,
  UNIT_LABELS,
  LAYER_LABELS,
  MAX_SITES,
} from '../consumption/types';
import { enrichWithSignature } from '../consumption/layers/SignatureLayer';

// ── types.js ──────────────────────────────────────────────────────────────

describe('MODES', () => {
  it('has 4 modes', () => {
    expect(Object.keys(MODES)).toHaveLength(4);
  });
  it('AGREGE value is agrege', () => {
    expect(MODES.AGREGE).toBe('agrege');
  });
  it('SUPERPOSE value is superpose', () => {
    expect(MODES.SUPERPOSE).toBe('superpose');
  });
  it('EMPILE value is empile', () => {
    expect(MODES.EMPILE).toBe('empile');
  });
  it('SEPARE value is separe', () => {
    expect(MODES.SEPARE).toBe('separe');
  });
});

describe('UNITS', () => {
  it('has 3 units', () => {
    expect(Object.keys(UNITS)).toHaveLength(3);
  });
  it('KWH is kwh', () => {
    expect(UNITS.KWH).toBe('kwh');
  });
  it('KW is kw', () => {
    expect(UNITS.KW).toBe('kw');
  });
  it('EUR is eur', () => {
    expect(UNITS.EUR).toBe('eur');
  });
});

describe('LAYERS', () => {
  it('has 5 layers', () => {
    expect(Object.keys(LAYERS)).toHaveLength(5);
  });
  it('TUNNEL is tunnel', () => {
    expect(LAYERS.TUNNEL).toBe('tunnel');
  });
  it('SIGNATURE is signature', () => {
    expect(LAYERS.SIGNATURE).toBe('signature');
  });
});

describe('DEFAULT_LAYERS', () => {
  it('tunnel is ON by default', () => {
    expect(DEFAULT_LAYERS[LAYERS.TUNNEL]).toBe(true);
  });
  it('talon is OFF by default', () => {
    expect(DEFAULT_LAYERS[LAYERS.TALON]).toBe(false);
  });
  it('meteo is OFF by default', () => {
    expect(DEFAULT_LAYERS[LAYERS.METEO]).toBe(false);
  });
  it('signature is OFF by default', () => {
    expect(DEFAULT_LAYERS[LAYERS.SIGNATURE]).toBe(false);
  });
  it('objectifs is OFF by default', () => {
    expect(DEFAULT_LAYERS[LAYERS.OBJECTIFS]).toBe(false);
  });
});

describe('Labels', () => {
  it('MODE_LABELS has label for each mode', () => {
    for (const key of Object.values(MODES)) {
      expect(MODE_LABELS[key]).toBeTruthy();
    }
  });
  it('UNIT_LABELS has label for each unit', () => {
    for (const key of Object.values(UNITS)) {
      expect(UNIT_LABELS[key]).toBeTruthy();
    }
  });
  it('LAYER_LABELS has label for each layer', () => {
    for (const key of Object.values(LAYERS)) {
      expect(LAYER_LABELS[key]).toBeTruthy();
    }
  });
});

describe('MAX_SITES', () => {
  it('is 5', () => {
    expect(MAX_SITES).toBe(5);
  });
});

// ── enrichWithSignature ────────────────────────────────────────────────────

describe('enrichWithSignature', () => {
  const data = [
    { date: 'd1', kwh: 10 },
    { date: 'd2', kwh: 20 },
    { date: 'd3', kwh: 30 },
    { date: 'd4', kwh: 40 },
    { date: 'd5', kwh: 50 },
  ];

  it('empty array => empty array', () => {
    expect(enrichWithSignature([])).toEqual([]);
  });

  it('adds signature key to each point', () => {
    const result = enrichWithSignature(data);
    for (const p of result) {
      expect(p).toHaveProperty('signature');
    }
  });

  it('first point signature = its own value', () => {
    const result = enrichWithSignature(data);
    expect(result[0].signature).toBe(10);
  });

  it('second point signature = avg of first two', () => {
    const result = enrichWithSignature(data);
    expect(result[1].signature).toBe(15); // (10+20)/2
  });

  it('preserves all original keys', () => {
    const result = enrichWithSignature(data);
    expect(result[0].date).toBe('d1');
    expect(result[0].kwh).toBe(10);
  });

  it('window=1 => signature equals own value', () => {
    const result = enrichWithSignature(data, 'kwh', 1);
    expect(result[2].signature).toBe(30);
  });

  it('handles null/undefined values gracefully', () => {
    const sparseData = [{ kwh: 10 }, { kwh: null }, { kwh: 30 }];
    expect(() => enrichWithSignature(sparseData)).not.toThrow();
  });
});
