import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Blockers } from '../../../hooks/v4';
import { TAB_COPY } from '../constants';
import { BlockerItem } from './BlockerItem';

const LIMIT = 20;

/**
 * M2-5.3.B — Onglet Blocages du drawer (read-only, lazy).
 */
export function BlockersTab({ itemId }) {
  const { data, loading, error, refetch } = useActionCenterV4Blockers(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  if (loading) return <Skeleton rows={3} />;

  if (error) {
    return (
      <ErrorState
        title={TAB_COPY.blockersErrorTitle}
        message={error.message || ''}
        onRetry={refetch}
      />
    );
  }

  const blockers = data?.items || [];

  if (blockers.length === 0) {
    return (
      <EmptyState
        variant="empty"
        title={TAB_COPY.blockersEmptyTitle}
        text={TAB_COPY.blockersEmptyText}
      />
    );
  }

  return (
    <ol className="space-y-2">
      {blockers.map((blocker) => (
        <li key={blocker.id}>
          <BlockerItem blocker={blocker} />
        </li>
      ))}
    </ol>
  );
}
