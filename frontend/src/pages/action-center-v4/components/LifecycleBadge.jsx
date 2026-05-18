import Badge from '../../../ui/Badge';

import { LIFECYCLE_BADGE_VARIANTS, LIFECYCLE_LABELS } from '../constants';

/**
 * M2-5.2 — Badge d'état lifecycle d'un item V4.
 *
 * Couleur mappée via le prop `status` du Badge (zéro couleur hardcodée).
 * Texte FR. Fallback sur la valeur brute si l'état est inconnu.
 */
export function LifecycleBadge({ state }) {
  const status = LIFECYCLE_BADGE_VARIANTS[state] || 'neutral';
  const label = LIFECYCLE_LABELS[state] || state;

  return <Badge status={status}>{label}</Badge>;
}
