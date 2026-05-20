import { useCallback, useState } from 'react';

import PageShell from '../../ui/PageShell';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';

import { usePilotageFilePrioritaire, useActionCenterV4Items } from '../../hooks/v4';
import { PILOTAGE_COPY } from './constants';
import { ItemDetailDrawer } from './components/ItemDetailDrawer';
import { Masthead } from './components/Masthead';
import { PilotageTabs } from './components/PilotageTabs';
import { PilotageViewToggle } from './components/PilotageViewToggle';
import { PriorityQueueCard } from './components/PriorityQueueCard';

/**
 * M2-5.10.D — Page Pilotage (`/action-center-v4/pilotage`) — vue Resp.
 * Énergie « ce matin » avec la file prioritaire (5 items P0/P1 actifs).
 *
 * Maquette source : `docs/maquettes/centre_action_v4/centre_action_v4_pilotage_
 * decisions_v031.html` §8.1. Scope MV3 réduit : masthead Sol + tabs internes
 * + section « File prioritaire » uniquement. Hors scope (BACKLOG_M3) :
 * narrative bar agrégée, escalation banner, quick filters, sections Jalons /
 * À surveiller / Clôturé récemment, view toggle Décisions/Journal (= .E),
 * SLA dates, vues Audit/Dense.
 *
 * Clic sur une card → ouvre le drawer détail (réutilise `ItemDetailDrawer`).
 * On consomme `useActionCenterV4Items` à zéro coût juste pour pouvoir
 * passer `refetch` à `onRefreshList` (parité avec la page Référentiel) —
 * sinon une transition lifecycle depuis le drawer ne rafraîchirait pas la
 * file (les hooks Pilotage et Items sont indépendants côté state).
 */
export function ActionCenterV4PilotagePage() {
  const [selectedItemId, setSelectedItemId] = useState(null);

  const { data, loading, error, refetch } = usePilotageFilePrioritaire({ limit: 5 });
  // Liste référentiel utilisée comme `onRefreshList` du drawer pour rester
  // cohérent avec la page liste (un succès transition refresh aussi la
  // liste globale même si l'utilisateur n'est pas dessus).
  const { refetch: refetchAll } = useActionCenterV4Items({ offset: 0, limit: 20 });

  const items = data?.items || [];
  const ready = !loading && !error;

  const handleOpenItem = useCallback((item) => {
    setSelectedItemId(item.id);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedItemId(null);
  }, []);

  // Succès transition / mutation → refetch file + référentiel (le drawer
  // gère son propre refetch item via useActionCenterV4Item).
  const handleRefreshFromDrawer = useCallback(() => {
    refetch();
    refetchAll();
  }, [refetch, refetchAll]);

  return (
    <PageShell editorialHeader={<Masthead total={items.length} />}>
      <PilotageTabs />
      <PilotageViewToggle />

      {/* Header section File prioritaire — maquette §8.1 lignes 870-876. */}
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <div>
          <h2
            className="text-[15px] font-semibold leading-tight"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-900)',
            }}
          >
            {PILOTAGE_COPY.fileSectionTitle}
            {items.length > 0 && (
              <span
                className="ml-2 font-mono text-[10px] font-normal"
                style={{ color: 'var(--sol-ink-500)' }}
              >
                {items.length}
              </span>
            )}
          </h2>
          <p
            className="mt-0.5 text-[12px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {PILOTAGE_COPY.fileSectionSub}
          </p>
        </div>
      </div>

      {loading && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-[110px] animate-pulse rounded-[8px] border"
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
              }}
            />
          ))}
        </div>
      )}

      {!loading && error && (
        <ErrorState
          title={PILOTAGE_COPY.errorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {ready && items.length === 0 && (
        <EmptyState
          variant="empty"
          title={PILOTAGE_COPY.emptyTitle}
          text={PILOTAGE_COPY.emptyText}
        />
      )}

      {ready && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <PriorityQueueCard key={item.id} item={item} onOpenItem={handleOpenItem} />
          ))}
        </div>
      )}

      <ItemDetailDrawer
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onClose={handleCloseDrawer}
        onRefreshList={handleRefreshFromDrawer}
      />
    </PageShell>
  );
}
