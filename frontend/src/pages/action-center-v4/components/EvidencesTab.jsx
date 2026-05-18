import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Evidences } from '../../../hooks/v4';
import { TAB_COPY } from '../constants';
import { EvidenceItem } from './EvidenceItem';

const LIMIT = 20;

/**
 * M2-5.3.B — Onglet Preuves du drawer (read-only, lazy).
 */
export function EvidencesTab({ itemId }) {
  const { data, loading, error, refetch } = useActionCenterV4Evidences(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  if (loading) return <Skeleton rows={3} />;

  if (error) {
    return (
      <ErrorState
        title={TAB_COPY.evidencesErrorTitle}
        message={error.message || ''}
        onRetry={refetch}
      />
    );
  }

  const evidences = data?.items || [];

  if (evidences.length === 0) {
    return (
      <EmptyState
        variant="empty"
        title={TAB_COPY.evidencesEmptyTitle}
        text={TAB_COPY.evidencesEmptyText}
      />
    );
  }

  return (
    <ol className="space-y-2">
      {evidences.map((evidence) => (
        <li key={evidence.id}>
          <EvidenceItem evidence={evidence} />
        </li>
      ))}
    </ol>
  );
}
