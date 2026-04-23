/**
 * PERMISSION_KEY_MAP — bridge entre clés NavRegistry V7 (module keys) et
 * clés backend permissions (capability keys).
 *
 * DETTE TECHNIQUE ASSUMÉE : résout le mismatch identifié dans
 * docs/audit/audit-navigation-main-2026-04-22.md §7 et confirmé par
 * docs/audit/audit-navigation-sol-fresh-2026-04-22.md §5.
 *
 * Exemples :
 *   resolveBackendPermissionKey('energie') → 'consommations'
 *   resolveBackendPermissionKey('achat')   → 'purchase'
 *   resolveBackendPermissionKey('cockpit') → 'cockpit' (identity)
 *
 * À terme (Lot 8+), aligner le backend `ROLE_PERMISSIONS` sur les module
 * keys NavRegistry. D'ici là cette table est la source de vérité frontend.
 */

export const PERMISSION_KEY_MAP = {
  cockpit: 'cockpit',
  conformite: 'conformite',
  energie: 'consommations',
  patrimoine: 'patrimoine',
  achat: 'purchase',
  admin: 'admin',
};

// Dev warning : signale les clés nav non mappées (sinon le fallback
// identity masque silencieusement un oubli). Fire-once par clé pour
// éviter le spam dans le useMemo sections (append à chaque render où
// les deps changent).
const _warnedKeys = new Set();

/**
 * Traduit une clé module NavRegistry en clé backend permission.
 * Identity fallback pour toute clé non-mappée (future-proof).
 */
export function resolveBackendPermissionKey(navKey) {
  if (navKey == null) return navKey;
  const mapped = PERMISSION_KEY_MAP[navKey];
  if (mapped === undefined) {
    if (import.meta.env?.DEV && !_warnedKeys.has(navKey)) {
      _warnedKeys.add(navKey);
      // eslint-disable-next-line no-console
      console.warn(
        `[permissionMap] nav key "${navKey}" not mapped to a backend capability ` +
          `— using identity fallback. Add it to PERMISSION_KEY_MAP.`
      );
    }
    return navKey;
  }
  return mapped;
}
