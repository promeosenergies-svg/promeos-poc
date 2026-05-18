import { useState } from 'react';
import { ClipboardList } from 'lucide-react';

import PageShell from '../../ui/PageShell';
import { SkeletonTable } from '../../ui/Skeleton';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import Pagination from '../../ui/Pagination';

import { useActionCenterV4Items } from '../../hooks/v4';
import { COPY, PAGE_SIZE } from './constants';
import { ItemsTable } from './components/ItemsTable';
import { ListFilterBar } from './components/ListFilterBar';

/**
 * M2-5.2 — Page liste du Centre d'Action V4 (`/action-center-v4`).
 *
 * Premier écran utilisateur V4 : liste paginée (20/page) des items, filtre
 * lifecycle client-side, états loading / vide / erreur. Le clic ligne (drawer
 * détail) est branché en M2-5.3 — les lignes sont volontairement inertes ici.
 */
export function ActionCenterV4ListPage() {
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState(null);

  const { data, loading, error, refetch } = useActionCenterV4Items({
    offset: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  const items = data?.items || [];
  const total = data?.total ?? 0;
  const filteredItems = stateFilter
    ? items.filter((item) => item.lifecycle_state === stateFilter)
    : items;

  const ready = !loading && !error;

  return (
    <PageShell icon={ClipboardList} title={COPY.pageTitle} subtitle={COPY.pageSubtitle}>
      <ListFilterBar stateFilter={stateFilter} onStateFilterChange={setStateFilter} />

      {loading && <SkeletonTable rows={5} cols={4} />}

      {!loading && error && (
        <ErrorState title={COPY.errorTitle} message={error.message || ''} onRetry={refetch} />
      )}

      {ready && items.length === 0 && (
        <EmptyState variant="empty" title={COPY.emptyTitle} text={COPY.emptyText} />
      )}

      {ready && items.length > 0 && filteredItems.length === 0 && (
        <EmptyState variant="empty" title={COPY.emptyFilteredTitle} text={COPY.emptyFilteredText} />
      )}

      {ready && filteredItems.length > 0 && <ItemsTable items={filteredItems} />}

      {ready && total > 0 && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
      )}
    </PageShell>
  );
}
