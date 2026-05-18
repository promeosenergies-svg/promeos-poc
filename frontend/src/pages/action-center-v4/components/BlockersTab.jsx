import { useCallback, useState } from 'react';

import Button from '../../../ui/Button';
import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Blockers } from '../../../hooks/v4';
import { BLOCKER_ADD_COPY, TAB_COPY } from '../constants';
import { BlockerAddModal } from './BlockerAddModal';
import { BlockerItem } from './BlockerItem';

const LIMIT = 20;

/**
 * M2-5.3.B / M2-5.6 — Onglet Blocages du drawer.
 *
 * Lecture lazy + actions write M2-5.6 : « Ajouter un blocage » (modal) et
 * « Résoudre » par blocker (modal dans BlockerItem). Au succès d'une mutation :
 * refetch local + `onBlockerMutated` pour rafraîchir la Timeline.
 */
export function BlockersTab({ itemId, onBlockerMutated }) {
  const [addModalOpen, setAddModalOpen] = useState(false);

  const { data, loading, error, refetch } = useActionCenterV4Blockers(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  const handleSuccess = useCallback(() => {
    refetch();
    onBlockerMutated?.();
  }, [refetch, onBlockerMutated]);

  const blockers = data?.items || [];

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button onClick={() => setAddModalOpen(true)}>{BLOCKER_ADD_COPY.buttonAddBlocker}</Button>
      </div>

      {loading && <Skeleton rows={3} />}

      {!loading && error && (
        <ErrorState
          title={TAB_COPY.blockersErrorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {!loading && !error && blockers.length === 0 && (
        <EmptyState
          variant="empty"
          title={TAB_COPY.blockersEmptyTitle}
          text={TAB_COPY.blockersEmptyText}
        />
      )}

      {!loading && !error && blockers.length > 0 && (
        <ol className="space-y-2">
          {blockers.map((blocker) => (
            <li key={blocker.id}>
              <BlockerItem blocker={blocker} onResolveSuccess={handleSuccess} />
            </li>
          ))}
        </ol>
      )}

      {addModalOpen && (
        <BlockerAddModal
          open
          onClose={() => setAddModalOpen(false)}
          itemId={itemId}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
