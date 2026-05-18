import Skeleton from '../../../ui/Skeleton';
import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';

import { useActionCenterV4Events } from '../../../hooks/v4';
import { DRAWER_COPY } from '../constants';
import { EventTimelineList } from './EventTimelineList';

const TIMELINE_LIMIT = 20;

/**
 * M2-5.3.A — Onglet Historique du drawer.
 *
 * Lazy : monté seulement quand l'onglet Timeline est actif. Consomme
 * useActionCenterV4Events (lecture seule), affiche les 20 derniers events
 * (tri occurred_at DESC côté backend).
 */
export function TimelineTab({ itemId }) {
  const { data, loading, error, refetch } = useActionCenterV4Events(itemId, {
    offset: 0,
    limit: TIMELINE_LIMIT,
  });

  if (loading) {
    return <Skeleton rows={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title={DRAWER_COPY.timelineErrorTitle}
        message={error.message || ''}
        onRetry={refetch}
      />
    );
  }

  const events = data?.items || [];

  if (events.length === 0) {
    return (
      <EmptyState
        variant="empty"
        title={DRAWER_COPY.timelineEmptyTitle}
        text={DRAWER_COPY.timelineEmptyText}
      />
    );
  }

  return <EventTimelineList events={events} />;
}
