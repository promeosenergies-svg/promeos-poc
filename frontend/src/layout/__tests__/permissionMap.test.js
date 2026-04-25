/**
 * PERMISSION_KEY_MAP — tests unitaires du bridge module NavRegistry ↔
 * capability backend (Sprint 1 Vague A phase A2).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { PERMISSION_KEY_MAP, resolveBackendPermissionKey } from '../permissionMap';
import { NAV_MODULES } from '../NavRegistry';

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

  it('F3 fix P1-11 : every NAV_MODULES key is present in PERMISSION_KEY_MAP (dynamic)', () => {
    // Dérivé dynamiquement de NAV_MODULES — si un jour un 7ème module
    // est ajouté (ex. flexibilite), il doit être ajouté à PERMISSION_KEY_MAP
    // simultanément sinon le test échoue.
    const navKeys = NAV_MODULES.map((m) => m.key);
    expect(navKeys.length).toBeGreaterThanOrEqual(6);
    const missing = navKeys.filter((k) => PERMISSION_KEY_MAP[k] === undefined);
    expect(missing, `Modules missing from PERMISSION_KEY_MAP: ${missing.join(', ')}`).toEqual([]);
    navKeys.forEach((key) => {
      expect(typeof PERMISSION_KEY_MAP[key]).toBe('string');
    });
  });

  it('undefined and null are handled (identity fallback)', () => {
    expect(resolveBackendPermissionKey(undefined)).toBeUndefined();
    expect(resolveBackendPermissionKey(null)).toBe(null);
  });
});

describe('permissionMap source guards (F4 P2-8)', () => {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const src = readFileSync(join(__dirname, '..', 'permissionMap.js'), 'utf-8');

  it('warns in dev when a key is not mapped (anti silent typo)', () => {
    expect(src).toMatch(/console\.warn/);
    expect(src).toMatch(/not mapped to a backend capability/);
  });
});
