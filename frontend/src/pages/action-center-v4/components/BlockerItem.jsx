import Badge from '../../../ui/Badge';

import {
  BLOCKER_STATUS_BADGE_VARIANTS,
  BLOCKER_STATUS_LABELS,
  BLOCKER_TYPE_LABELS,
  TAB_COPY,
} from '../constants';
import { formatDateTimeFR } from '../utils/date';

/**
 * M2-5.3.B — Affichage d'un blocker (read-only).
 *
 * Status dérivé de resolved_at : actif tant qu'il n'est pas résolu.
 */
export function BlockerItem({ blocker }) {
  const status = blocker.resolved_at ? 'resolved' : 'active';
  const label = BLOCKER_STATUS_LABELS[status];
  const variant = BLOCKER_STATUS_BADGE_VARIANTS[status];
  const typeLabel = BLOCKER_TYPE_LABELS[blocker.blocker_type] || blocker.blocker_type;

  return (
    <article className="rounded border border-gray-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-gray-900">{typeLabel}</div>
          {blocker.justification && (
            <div className="mt-1 text-sm text-gray-700">{blocker.justification}</div>
          )}
        </div>
        <Badge status={variant}>{label}</Badge>
      </div>

      <div className="mt-2 space-y-0.5 text-xs text-gray-500">
        {blocker.added_at && (
          <div>
            {TAB_COPY.reportedAtLabel} {formatDateTimeFR(blocker.added_at)}
          </div>
        )}
        {blocker.resolved_at && (
          <div>
            {TAB_COPY.resolvedAtLabel} {formatDateTimeFR(blocker.resolved_at)}
          </div>
        )}
      </div>
    </article>
  );
}
