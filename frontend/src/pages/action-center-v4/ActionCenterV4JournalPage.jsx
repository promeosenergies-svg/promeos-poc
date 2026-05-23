import { useCallback, useMemo, useState } from 'react';

import PageShell from '../../ui/PageShell';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';

import { useActionCenterV4Items, usePilotageJournal } from '../../hooks/v4';
import { JOURNAL_COPY } from './constants';
import { groupEventsByDay } from './utils/groupByDay';
import { ItemDetailDrawer } from './components/drawer/ItemDetailDrawer';
import { JournalEventRow } from './components/narrative/JournalEventRow';
import { Masthead } from './components/narrative/Masthead';
import { PilotageTabs } from './components/narrative/PilotageTabs';
import { PilotageViewToggle } from './components/narrative/PilotageViewToggle';

/**
 * M2-5.10.E — Page Pilotage / Journal (`/action-center-v4/pilotage/journal`).
 *
 * Timeline org-wide cross-items des 7 derniers jours, groupée par jour
 * (Aujourd'hui / Hier / dates). Clic sur le titre d'un item dans une ligne
 * d'event → ouvre le drawer détail (réutilise `ItemDetailDrawer`).
 *
 * Maquette source `centre_action_v4_pilotage_journal.html` §8.2 — scope MV3
 * réduit : pas de filtres event_type serveur, pas de narrative bar agrégée,
 * pas d'export PDF (BACKLOG_M3).
 */
export function ActionCenterV4JournalPage() {
  const [selectedItemId, setSelectedItemId] = useState(null);

  const { data, loading, error, refetch } = usePilotageJournal({ sinceDays: 7, limit: 100 });
  const { refetch: refetchAll } = useActionCenterV4Items({ offset: 0, limit: 20 });

  // `data?.items || []` retournerait un tableau littéral à chaque rendu →
  // dépendance instable pour le useMemo qui suit. On le stabilise.
  const events = useMemo(() => data?.items || [], [data]);
  const total = data?.total ?? 0;
  const ready = !loading && !error;

  const groups = useMemo(() => groupEventsByDay(events), [events]);

  const handleOpenItem = useCallback((itemId) => {
    setSelectedItemId(itemId);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedItemId(null);
  }, []);

  const handleRefreshFromDrawer = useCallback(() => {
    refetch();
    refetchAll();
  }, [refetch, refetchAll]);

  return (
    <PageShell
      editorialHeader={
        <Masthead
          subtitle="Journal · flux d'activité"
          countLabel={total > 0 ? JOURNAL_COPY.countSuffix(total) : null}
        />
      }
    >
      <PilotageTabs />
      <PilotageViewToggle />

      {/* Header section Journal — équivalent de fileSection sur la page
          Décisions, mais centré sur les events org-wide. */}
      <div className="mb-3">
        <h2
          className="text-[15px] font-semibold leading-tight"
          style={{
            fontFamily: 'var(--sol-font-display)',
            color: 'var(--sol-ink-900)',
          }}
        >
          {JOURNAL_COPY.sectionTitle}
          {total > 0 && (
            <span
              className="ml-2 font-mono text-[10px] font-normal"
              style={{ color: 'var(--sol-ink-500)' }}
            >
              {total}
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
          {JOURNAL_COPY.sectionSub}
        </p>
      </div>

      {loading && (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[120px] animate-pulse rounded-[6px] border"
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
          title={JOURNAL_COPY.errorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {ready && groups.length === 0 && (
        <EmptyState variant="empty" title={JOURNAL_COPY.emptyTitle} text={JOURNAL_COPY.emptyText} />
      )}

      {ready && groups.length > 0 && (
        <div className="space-y-6">
          {groups.map((group, gi) => (
            <section key={group.dayKey} aria-label={`Événements ${group.label}`}>
              {/* Day header — maquette §8.2 lignes 633-637. */}
              <div
                className="mb-2 flex items-baseline gap-3 pb-1.5"
                style={{ borderBottom: '1px solid var(--sol-rule)' }}
              >
                <span
                  className="text-[13px] font-medium"
                  style={{
                    fontFamily: 'var(--sol-font-display)',
                    color: 'var(--sol-ink-900)',
                  }}
                >
                  {group.label}
                </span>
                <span
                  className="font-mono text-[10px] uppercase tracking-[0.08em]"
                  style={{ color: 'var(--sol-ink-500)' }}
                >
                  {group.events.length} {group.events.length === 1 ? 'événement' : 'événements'}
                </span>
              </div>

              <ol className="relative flex flex-col pl-3.5">
                {/* Ligne verticale Sol commune à la timeline. */}
                <span
                  aria-hidden="true"
                  className="absolute top-1 bottom-1 w-px"
                  style={{ left: '0px', background: 'var(--sol-rule)' }}
                />
                {group.events.map((event, ei) => (
                  <li key={event.id}>
                    <JournalEventRow
                      event={event}
                      isFirst={gi === 0 && ei === 0}
                      onOpenItem={handleOpenItem}
                    />
                  </li>
                ))}
              </ol>
            </section>
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
