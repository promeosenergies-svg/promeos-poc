import EmptyState from '../../../../ui/EmptyState';
import ErrorState from '../../../../ui/ErrorState';
import Skeleton from '../../../../ui/Skeleton';

import { useActionCenterV4Links } from '../../../../hooks/v4';
import { TAB_COPY } from '../../constants';
import { LinkItem } from './LinkItem';

const LIMIT = 20;

/**
 * M2-5.3.B — Onglet Liens du drawer (read-only, lazy).
 */
export function LinksTab({ itemId }) {
  const { data, loading, error, refetch } = useActionCenterV4Links(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  if (loading) return <Skeleton rows={3} />;

  if (error) {
    return (
      <ErrorState
        title={TAB_COPY.linksErrorTitle}
        message={error.message || ''}
        onRetry={refetch}
      />
    );
  }

  const links = data?.items || [];

  if (links.length === 0) {
    return (
      <EmptyState variant="empty" title={TAB_COPY.linksEmptyTitle} text={TAB_COPY.linksEmptyText} />
    );
  }

  return (
    <ol className="space-y-2">
      {links.map((link) => (
        <li key={link.id}>
          <LinkItem link={link} />
        </li>
      ))}
    </ol>
  );
}
