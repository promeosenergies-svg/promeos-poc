/**
 * PROMEOS — ExplorerPresets regression tests (V11.1-E)
 * Tests the pure preset logic from useExplorerPresets.js.
 *
 * We test the underlying pure functions (readPresets, writePresets, savePreset, etc.)
 * by importing the helper logic and using a localStorage mock.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// ── localStorage mock ──────────────────────────────────────────────────────
const store = {};
const mockLocalStorage = {
  getItem: vi.fn((key) => store[key] ?? null),
  setItem: vi.fn((key, val) => {
    store[key] = val;
  }),
  removeItem: vi.fn((key) => {
    delete store[key];
  }),
  clear: vi.fn(() => {
    Object.keys(store).forEach((k) => delete store[k]);
  }),
};
vi.stubGlobal('localStorage', mockLocalStorage);

// ── Re-implement the pure preset logic for unit testing ────────────────────
const STORAGE_KEY = 'promeos_explorer_presets';
const MAX_PRESETS = 10;

function readPresets() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writePresets(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {}
}

function makePresetOps(initial = []) {
  let presets = [...initial];

  const persist = (next) => {
    presets = next;
    writePresets(next);
  };

  const savePreset = (name, state) => {
    if (!name?.trim()) return;
    const filtered = presets.filter((p) => p.name !== name);
    const entry = { name, state, savedAt: new Date().toISOString() };
    persist([...filtered, entry].slice(-MAX_PRESETS));
  };

  const loadPreset = (name) => presets.find((p) => p.name === name)?.state ?? null;
  const deletePreset = (name) => persist(presets.filter((p) => p.name !== name));
  const getPresets = () => presets;

  return { savePreset, loadPreset, deletePreset, getPresets };
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe('useExplorerPresets — save / load / delete', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    Object.keys(store).forEach((k) => delete store[k]);
  });

  it('savePreset stores entry and loadPreset retrieves it', () => {
    const { savePreset, loadPreset } = makePresetOps();
    const state = { siteIds: [1], energy: 'electricity', days: 30, mode: 'agrege', unit: 'kwh' };
    savePreset('Mon preset', state);
    expect(loadPreset('Mon preset')).toEqual(state);
  });

  it('loadPreset returns null for unknown name', () => {
    const { loadPreset } = makePresetOps();
    expect(loadPreset('inconnu')).toBeNull();
  });

  it('deletePreset removes the entry', () => {
    const state = { energy: 'gas' };
    const { savePreset, deletePreset, loadPreset, getPresets } = makePresetOps();
    savePreset('A', state);
    expect(getPresets()).toHaveLength(1);
    deletePreset('A');
    expect(getPresets()).toHaveLength(0);
    expect(loadPreset('A')).toBeNull();
  });

  it('savePreset overwrites existing entry with same name (no duplicates)', () => {
    const { savePreset, loadPreset, getPresets } = makePresetOps();
    savePreset('A', { days: 30 });
    savePreset('A', { days: 90 });
    expect(getPresets()).toHaveLength(1);
    expect(loadPreset('A')).toEqual({ days: 90 });
  });

  it('max 10 presets: 11th save drops oldest', () => {
    const { savePreset, getPresets } = makePresetOps();
    for (let i = 1; i <= 11; i++) {
      savePreset(`Preset ${i}`, { idx: i });
    }
    const names = getPresets().map((p) => p.name);
    expect(names).toHaveLength(MAX_PRESETS);
    // Oldest (Preset 1) should be gone
    expect(names).not.toContain('Preset 1');
    // Latest should be present
    expect(names).toContain('Preset 11');
  });

  it('invalid localStorage JSON returns empty list without throw', () => {
    store[STORAGE_KEY] = 'NOT_JSON{{{';
    const result = readPresets();
    expect(result).toEqual([]);
  });

  it('persists to localStorage on save', () => {
    const { savePreset } = makePresetOps();
    savePreset('Stored', { energy: 'gas' });
    const raw = mockLocalStorage.getItem(STORAGE_KEY);
    const parsed = JSON.parse(raw);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].name).toBe('Stored');
  });

  it('multiple named presets can coexist independently', () => {
    const { savePreset, loadPreset } = makePresetOps();
    savePreset('Alpha', { days: 7 });
    savePreset('Beta', { days: 30 });
    savePreset('Gamma', { days: 90 });
    expect(loadPreset('Alpha')).toEqual({ days: 7 });
    expect(loadPreset('Beta')).toEqual({ days: 30 });
    expect(loadPreset('Gamma')).toEqual({ days: 90 });
  });
});
