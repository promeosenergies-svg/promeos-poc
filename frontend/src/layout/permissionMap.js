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

/**
 * Traduit une clé module NavRegistry en clé backend permission.
 * Identity fallback pour toute clé non-mappée (future-proof).
 */
export function resolveBackendPermissionKey(navKey) {
  return PERMISSION_KEY_MAP[navKey] ?? navKey;
}
