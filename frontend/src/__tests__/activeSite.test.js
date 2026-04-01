import { describe, test, expect, beforeEach, vi } from 'vitest';

// Mock localStorage for Node environment
const store = {};
const mockStorage = {
  getItem: vi.fn((key) => store[key] ?? null),
  setItem: vi.fn((key, val) => {
    store[key] = val;
  }),
  removeItem: vi.fn((key) => {
    delete store[key];
  }),
  clear: vi.fn(() => {
    for (const k in store) delete store[k];
  }),
};
vi.stubGlobal('localStorage', mockStorage);

import { getActiveSite, setActiveSite, clearActiveSite } from '../utils/activeSite';

beforeEach(() => {
  mockStorage.clear();
  vi.clearAllMocks();
});

describe('activeSite utils', () => {
  test('getActiveSite returns null when empty', () => {
    expect(getActiveSite()).toBeNull();
  });

  test('setActiveSite + getActiveSite round-trip', () => {
    setActiveSite({ id: 4, nom: 'Hotel HELIOS Nice', statut_conformite: 'a_risque' });
    const result = getActiveSite();
    expect(result.id).toBe(4);
    expect(result.nom).toBe('Hotel HELIOS Nice');
    expect(result.statut).toBe('a_risque');
  });

  test('clearActiveSite removes the entry', () => {
    setActiveSite({ id: 4, nom: 'Test' });
    clearActiveSite();
    expect(getActiveSite()).toBeNull();
  });

  test('setActiveSite ignores invalid input', () => {
    setActiveSite(null);
    expect(getActiveSite()).toBeNull();
    setActiveSite({ id: 4 }); // pas de nom
    expect(getActiveSite()).toBeNull();
  });

  test('getActiveSite handles corrupted localStorage', () => {
    localStorage.setItem('promeos.active_site', 'not-json');
    expect(getActiveSite()).toBeNull();
  });
});
