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
 *
 * F4 P2-8 : en dev, `console.warn` si une clé non-mappée est demandée
 * pour détecter silencieusement les nouveaux modules NavRegistry qui
 * n'ont pas été ajoutés à PERMISSION_KEY_MAP (sinon fallback identity
 * masquerait le bug).
 */
export function resolveBackendPermissionKey(navKey) {
  if (navKey == null) return navKey;
  const mapped = PERMISSION_KEY_MAP[navKey];
  if (mapped === undefined) {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV) {
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
