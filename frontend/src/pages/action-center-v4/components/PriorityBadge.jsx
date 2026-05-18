import Badge from '../../../ui/Badge';

import { PRIORITY_LABELS, PRIORITY_BADGE_VARIANTS } from '../constants';

/**
 * M2-5.8.B — Badge du `priority_bracket` d'un item V4 (P0-2 audit M2-5).
 *
 * Couleur mappée via les status Badge (crit/warn/info/neutral). Fallback :
 * la valeur brute du bracket si inconnue ; rien si bracket absent.
 */
export function PriorityBadge({ bracket }) {
  if (!bracket) return null;

  const variant = PRIORITY_BADGE_VARIANTS[bracket] || 'neutral';
  const label = PRIORITY_LABELS[bracket] || bracket;

  return <Badge status={variant}>{label}</Badge>;
}
