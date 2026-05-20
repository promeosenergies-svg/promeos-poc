import { useCallback, useState } from 'react';
import { Slash } from 'lucide-react';

import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Blockers } from '../../../hooks/v4';
import { BLOCKER_ADD_COPY, EMPTY_STATE_CTA_COPY, TAB_COPY } from '../constants';
import { BlockerAddModal } from './BlockerAddModal';
import { BlockerItem } from './BlockerItem';

const LIMIT = 20;

/**
 * M2-5.3.B / M2-5.6 — Onglet Blocages du drawer.
 *
 * Lecture lazy + actions write M2-5.6 : « Ajouter un blocage » (modal) et
 * « Résoudre » par blocker (modal dans BlockerItem). Au succès d'une mutation :
 * refetch local + `onBlockerMutated` pour rafraîchir la Timeline.
 *
 * M2-5.9.bis — `itemClosed` masque « Ajouter un blocage » sur un item clôturé.
 * La résolution d'un blocage déjà présent reste possible (état propre du blocker).
 */
export function BlockersTab({ itemId, itemClosed = false, onBlockerMutated }) {
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
      {!itemClosed && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => setAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-[4px] border px-3 py-1.5 font-sans text-[11.5px] font-semibold cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-afaire-fg)',
              borderColor: 'var(--sol-afaire-line)',
            }}
          >
            <Slash size={12} aria-hidden="true" />
            {BLOCKER_ADD_COPY.buttonAddBlocker}
          </button>
        </div>
      )}

      {loading && <Skeleton rows={3} />}

      {!loading && error && (
        <ErrorState
          title={TAB_COPY.blockersErrorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {!loading && !error && blockers.length === 0 && (
        <div>
          <EmptyState
            variant="empty"
            title={TAB_COPY.blockersEmptyTitle}
            text={TAB_COPY.blockersEmptyText}
          />
          {/* CTA inline — audit CS P1-3. */}
          {!itemClosed && (
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={() => setAddModalOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-[4px] border px-3 py-1.5 font-sans text-[11.5px] font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
                style={{
                  background: 'var(--sol-bg-paper)',
                  color: 'var(--sol-afaire-fg)',
                  borderColor: 'var(--sol-afaire-line)',
                }}
              >
                <Slash size={12} aria-hidden="true" />
                {EMPTY_STATE_CTA_COPY.addBlocker}
              </button>
            </div>
          )}
        </div>
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
