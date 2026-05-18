import { useCallback, useState } from 'react';
import { ClipboardList } from 'lucide-react';

import PageShell from '../../ui/PageShell';
import { SkeletonTable } from '../../ui/Skeleton';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import Pagination from '../../ui/Pagination';

import { useActionCenterV4Items } from '../../hooks/v4';
import { COPY, PAGE_SIZE } from './constants';
import { ItemsTable } from './components/ItemsTable';
import { ItemDetailDrawer } from './components/ItemDetailDrawer';
import { ListFilterBar } from './components/ListFilterBar';

/**
 * M2-5.2 / M2-5.3.A — Page liste du Centre d'Action V4 (`/action-center-v4`).
 *
 * Liste paginée (20/page), filtre lifecycle client-side, états loading / vide
 * / erreur. M2-5.3.A : un clic sur une ligne ouvre le drawer détail (read-only).
 *
 * Auth : la route est derrière `RequireAuth` (cf. M2-5.8.A.bis). Sans session,
 * `RequireAuth` redirige vers `/login` où le bouton « Connexion démo HELIOS »
 * est surfacé — la page n'a donc pas à gérer l'absence de token elle-même.
 */
export function ActionCenterV4ListPage() {
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);

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

  // selectedItemId (pas l'objet item) → le drawer fetch les données fraîches
  // via useActionCenterV4Item, évitant toute dérive avec la liste.
  const handleOpenItem = useCallback((item) => {
    setSelectedItemId(item.id);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedItemId(null);
  }, []);

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

      {ready && filteredItems.length > 0 && (
        <ItemsTable items={filteredItems} onOpenItem={handleOpenItem} />
      )}

      {ready && total > 0 && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
      )}

      <ItemDetailDrawer
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onClose={handleCloseDrawer}
        onRefreshList={refetch}
      />
    </PageShell>
  );
}
