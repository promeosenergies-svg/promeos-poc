/**
 * PERMISSION_KEY_MAP — tests unitaires du bridge module NavRegistry ↔
 * capability backend (Sprint 1 Vague A phase A2).
 */
import { describe, it, expect } from 'vitest';
import { PERMISSION_KEY_MAP, resolveBackendPermissionKey } from '../permissionMap';

describe('PERMISSION_KEY_MAP', () => {
  it('maps NavRegistry keys to backend capability keys', () => {
    expect(resolveBackendPermissionKey('energie')).toBe('consommations');
    expect(resolveBackendPermissionKey('achat')).toBe('purchase');
  });

  it('identity for keys already aligned backend↔frontend', () => {
    expect(resolveBackendPermissionKey('cockpit')).toBe('cockpit');
    expect(resolveBackendPermissionKey('conformite')).toBe('conformite');
    expect(resolveBackendPermissionKey('patrimoine')).toBe('patrimoine');
    expect(resolveBackendPermissionKey('admin')).toBe('admin');
  });

  it('identity fallback for unmapped keys (future-proof)', () => {
    expect(resolveBackendPermissionKey('unknown_module')).toBe('unknown_module');
    expect(resolveBackendPermissionKey('')).toBe('');
  });

  it('all 6 NavRegistry module keys are present in the map', () => {
    const navKeys = ['cockpit', 'conformite', 'energie', 'patrimoine', 'achat', 'admin'];
    navKeys.forEach((key) => {
      expect(PERMISSION_KEY_MAP[key]).toBeDefined();
      expect(typeof PERMISSION_KEY_MAP[key]).toBe('string');
    });
  });

  it('undefined and null are handled (identity fallback)', () => {
    expect(resolveBackendPermissionKey(undefined)).toBeUndefined();
    expect(resolveBackendPermissionKey(null)).toBe(null);
  });
});
