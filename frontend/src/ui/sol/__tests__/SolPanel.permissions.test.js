/**
 * SolPanel — permission filtering (Sprint 1 Vague A phase A2)
 *
 * Source-guard : vérifie que SolPanel appelle hasPermission via le
 * bridge PERMISSION_KEY_MAP. Tests comportementaux d'intégration full
 * RTL déportés en Phase A3 (après badge cadenas) pour éviter les
 * double-tests sur la même logique.
 *
 * Convention projet : source-guard style (readFileSync + regex).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');

describe('SolPanel — permission filtering wiring', () => {
  it('imports useAuth from AuthContext', () => {
    expect(src).toMatch(
      /import\s*\{[^}]*useAuth[^}]*\}\s*from\s*['"]\.\.\/\.\.\/contexts\/AuthContext['"]/
    );
  });

  it('imports resolveBackendPermissionKey from permissionMap', () => {
    expect(src).toMatch(
      /import\s*\{[^}]*resolveBackendPermissionKey[^}]*\}\s*from\s*['"]\.\.\/\.\.\/layout\/permissionMap['"]/
    );
  });

  it('imports ROUTE_MODULE_MAP from NavRegistry', () => {
    expect(src).toMatch(/ROUTE_MODULE_MAP/);
  });

  it('destructures hasPermission + isAuthenticated from useAuth()', () => {
    expect(src).toMatch(/\{\s*isAuthenticated,\s*hasPermission\s*\}\s*=\s*useAuth\(\)/);
  });

  it('calls hasPermission("view", …) for item filtering', () => {
    expect(src).toMatch(/hasPermission\(\s*['"]view['"]/);
  });

  it('calls hasPermission("admin") for requireAdmin items (parity with NavPanel)', () => {
    expect(src).toMatch(/requireAdmin/);
    expect(src).toMatch(/hasPermission\(\s*['"]admin['"]/);
  });

  it('uses resolveBackendPermissionKey to bridge NavRegistry key → backend key', () => {
    expect(src).toMatch(/resolveBackendPermissionKey\(\s*navModule\s*\)/);
  });

  it('resolves module from ROUTE_MODULE_MAP[item.to]', () => {
    expect(src).toMatch(/ROUTE_MODULE_MAP\[basePath\]/);
  });

  it('drops empty sections after filtering (length > 0 filter)', () => {
    expect(src).toMatch(/section\.items\.length\s*>\s*0/);
  });

  it('memoizes filtered sections (useMemo with proper deps)', () => {
    expect(src).toMatch(/React\.useMemo\(/);
    expect(src).toMatch(/\[rawSections,\s*isAuthenticated,\s*hasPermission\]/);
  });

  it('bypasses filter when not authenticated (all items remain visible)', () => {
    // A3 : au lieu d'un simple `return rawSections`, on map items avec
    // locked: false pour garder le shape cohérent. Test vérifie la branche
    // !isAuthenticated.
    expect(src).toMatch(/if\s*\(!\s*isAuthenticated\)\s*\{?/);
    expect(src).toMatch(/locked:\s*false/);
  });
});
