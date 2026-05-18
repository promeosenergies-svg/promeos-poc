import { useCallback, useEffect, useState } from 'react';
import { ClipboardList } from 'lucide-react';

import PageShell from '../../ui/PageShell';
import { SkeletonTable } from '../../ui/Skeleton';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import Pagination from '../../ui/Pagination';

import { useActionCenterV4Items } from '../../hooks/v4';
import { hasValidToken } from '../../services/api/v4Auth';
import { COPY, PAGE_SIZE } from './constants';
import { ItemsTable } from './components/ItemsTable';
import { ItemDetailDrawer } from './components/ItemDetailDrawer';
import { ListFilterBar } from './components/ListFilterBar';
import { DemoLoginPrompt } from './components/DemoLoginPrompt';

/**
 * M2-5.2 / M2-5.3.A / M2-5.8.A — Page liste du Centre d'Action V4
 * (`/action-center-v4`).
 *
 * Liste paginée (20/page), filtre lifecycle client-side, états loading / vide
 * / erreur ; un clic sur une ligne ouvre le drawer détail (read-only).
 *
 * M2-5.8.A — garde d'authentification : les endpoints V4 exigent un JWT
 * portant `org_id` (sinon 401 `NO_ORG_CONTEXT`). Sans token, on affiche un
 * prompt de connexion démo INLINE (pas de redirection) — résout le P0-1.
 */
export function ActionCenterV4ListPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => hasValidToken());
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);

  const { data, loading, error, refetch } = useActionCenterV4Items({
    offset: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  // Après demo-login : marquer authentifié ET refetch — le hook ne se
  // redéclenche pas seul (ses deps sont offset/limit, pas le token).
  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
    refetch();
  }, [refetch]);

  // Synchronise l'état si le token est purgé/posé ailleurs (autre onglet, ou
  // purge 401 par l'intercepteur apiClientV4). L'event `storage` ne couvre que
  // le cross-onglet ; la purge same-window est rattrapée au prochain mount.
  useEffect(() => {
    const sync = () => setIsAuthenticated(hasValidToken());
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

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

  // Pas de token → prompt de connexion démo inline (pas de redirection).
  if (!isAuthenticated) {
    return (
      <PageShell icon={ClipboardList} title={COPY.pageTitle} subtitle={COPY.pageSubtitle}>
        <DemoLoginPrompt onLoginSuccess={handleLoginSuccess} />
      </PageShell>
    );
  }

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
