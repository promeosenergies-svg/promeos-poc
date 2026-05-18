import { useCallback, useState } from 'react';

import Badge from '../../../ui/Badge';
import Button from '../../../ui/Button';

import {
  BLOCKER_RESOLVE_COPY,
  BLOCKER_STATUS_BADGE_VARIANTS,
  BLOCKER_STATUS_LABELS,
  BLOCKER_TYPE_LABELS,
  TAB_COPY,
} from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { BlockerResolveModal } from './BlockerResolveModal';

/**
 * M2-5.3.B / M2-5.6 — Affichage d'un blocker.
 *
 * Status dérivé de resolved_at : actif tant qu'il n'est pas résolu.
 * M2-5.6 : bouton « Résoudre » affiché uniquement si le blocage est actif
 * (`resolved_at === null`) → modal de résolution.
 */
export function BlockerItem({ blocker, onResolveSuccess }) {
  const [modalOpen, setModalOpen] = useState(false);
  const handleOpenModal = useCallback(() => setModalOpen(true), []);
  const handleCloseModal = useCallback(() => setModalOpen(false), []);

  const status = blocker.resolved_at ? 'resolved' : 'active';
  const label = BLOCKER_STATUS_LABELS[status];
  const variant = BLOCKER_STATUS_BADGE_VARIANTS[status];
  const typeLabel = BLOCKER_TYPE_LABELS[blocker.blocker_type] || blocker.blocker_type;
  const isActive = !blocker.resolved_at;

  return (
    <article className="rounded border border-gray-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-gray-900">{typeLabel}</div>
          {blocker.justification && (
            <div className="mt-1 text-sm text-gray-700">{blocker.justification}</div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge status={variant}>{label}</Badge>
          {isActive && (
            <Button variant="ghost" size="sm" onClick={handleOpenModal}>
              {BLOCKER_RESOLVE_COPY.buttonResolve}
            </Button>
          )}
        </div>
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

      {modalOpen && (
        <BlockerResolveModal
          open
          onClose={handleCloseModal}
          blockerId={blocker.id}
          onSuccess={onResolveSuccess}
        />
      )}
    </article>
  );
}
