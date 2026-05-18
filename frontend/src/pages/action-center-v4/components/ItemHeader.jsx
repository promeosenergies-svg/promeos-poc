import { useCallback, useState } from 'react';

import Button from '../../../ui/Button';

import { DRAWER_COPY, TRANSITION_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { isTerminalState } from '../utils/lifecycleTransitions';
import { LifecycleBadge } from './LifecycleBadge';
import { LifecycleTransitionModal } from './LifecycleTransitionModal';

/**
 * M2-5.3.A / M2-5.4 — En-tête du drawer : titre + badge d'état + bouton
 * « Transitionner » + métadonnées.
 *
 * Le bouton ouvre la modal de transition lifecycle (M2-5.4) ; il reste
 * toujours visible mais est désactivé si l'item est dans un état terminal
 * (`closed`). Gère les états loading (skeleton) et error / item absent.
 */
export function ItemHeader({ item, loading, error, onTransitionSuccess }) {
  const [modalOpen, setModalOpen] = useState(false);
  const handleOpenModal = useCallback(() => setModalOpen(true), []);
  const handleCloseModal = useCallback(() => setModalOpen(false), []);

  if (loading) {
    return (
      <header>
        <div className="mb-2 h-7 w-2/3 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-gray-200" />
      </header>
    );
  }

  if (error || !item) {
    return (
      <header>
        <p className="text-sm text-red-700">{DRAWER_COPY.headerError}</p>
      </header>
    );
  }

  const isTerminal = isTerminalState(item.lifecycle_state);

  return (
    <header>
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xl font-semibold text-gray-900">{item.title}</h2>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <LifecycleBadge state={item.lifecycle_state} />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleOpenModal}
            disabled={isTerminal}
            title={isTerminal ? TRANSITION_COPY.buttonTerminal : undefined}
          >
            {TRANSITION_COPY.buttonTransition}
          </Button>
        </div>
      </div>

      {item.description && <p className="mt-2 text-sm text-gray-600">{item.description}</p>}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
        <dt>{DRAWER_COPY.domainLabel}</dt>
        <dd className="text-gray-700">{item.domain || '—'}</dd>

        <dt>{DRAWER_COPY.kindLabel}</dt>
        <dd className="text-gray-700">{item.kind || '—'}</dd>

        <dt>{DRAWER_COPY.createdAtLabel}</dt>
        <dd className="text-gray-700">{formatDateTimeFR(item.created_at)}</dd>

        <dt>{DRAWER_COPY.updatedAtLabel}</dt>
        <dd className="text-gray-700">{formatDateTimeFR(item.updated_at)}</dd>
      </dl>

      {modalOpen && (
        <LifecycleTransitionModal
          open
          onClose={handleCloseModal}
          itemId={item.id}
          currentState={item.lifecycle_state}
          onSuccess={onTransitionSuccess}
        />
      )}
    </header>
  );
}
