import { useCallback, useMemo, useState } from 'react';

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
import { Masthead } from './components/Masthead';
import { NarrativeBar } from './components/NarrativeBar';
import { PilotageTabs } from './components/PilotageTabs';

/**
 * M2-5.2 → M2-5.10.A.bis — Page liste du Centre d'Action V4 (`/action-center-v4`).
 *
 * Liste paginée (20/page), filtres lifecycle + kind client-side, états
 * loading/vide/erreur. Clic sur une ligne → drawer détail (read-only puis
 * write M2-5.4-.6).
 *
 * M2-5.10.A : restyle pixel-perfect Sol (maquette §8.3, `centre_action_v4_
 * referentiel.html`).
 * M2-5.10.A.bis : hotfix fidélité — masthead remonté via
 * `editorialHeader` (court-circuite le H1 Tailwind du PageShell, anti-pattern
 * doctrine §6.1) + sous-titre enrichi du total backend.
 *
 * Auth : la route est derrière `RequireAuth` (cf. M2-5.8.A.bis). Sans
 * session, `RequireAuth` redirige vers `/login` où le bouton « Connexion
 * démo HELIOS » est surfacé — la page n'a donc pas à gérer l'absence de
 * token elle-même.
 */
export function ActionCenterV4ListPage() {
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState(null);
  const [kindFilter, setKindFilter] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);

  const { data, loading, error, refetch } = useActionCenterV4Items({
    offset: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  // `data?.items || []` retournerait un tableau littéral à chaque rendu →
  // dépendance instable pour le useMemo qui suit. On le stabilise.
  const items = useMemo(() => data?.items || [], [data]);
  const total = data?.total ?? 0;

  // Filtrage client-side sur la page courante (cf. `filterScopeNote`). Les
  // deux filtres sont composés (AND). Le calcul n'est pas du « calcul
  // métier » (règle d'or PROMEOS) : c'est de la sélection visuelle pure.
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (stateFilter && item.lifecycle_state !== stateFilter) return false;
      if (kindFilter && item.kind !== kindFilter) return false;
      return true;
    });
  }, [items, stateFilter, kindFilter]);

  // M2-5.10.A.bis — counts par kind sur la page courante (sélection visuelle
  // pour les `chip-count` MONO maquette ligne 745-752). Limité à la page
  // (cohérent avec `filterScopeNote`). Dette M3+ : count org-wide backend.
  const kindCounts = useMemo(() => {
    const counts = {};
    for (const item of items) {
      counts[item.kind] = (counts[item.kind] || 0) + 1;
    }
    return counts;
  }, [items]);

  const ready = !loading && !error;

  // selectedItemId (pas l'objet item) → le drawer fetch les données fraîches
  // via useActionCenterV4Item, évitant toute dérive avec la liste.
  const handleOpenItem = useCallback((item) => {
    setSelectedItemId(item.id);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedItemId(null);
  }, []);

  // M2-5.9.bis — changer un filtre repart en page 1 : filtrer depuis une
  // page profonde laisserait une page vide trompeuse (EmptyState alors que
  // d'autres pages contiennent des items du filtre).
  const handleStateFilterChange = useCallback((value) => {
    setStateFilter(value);
    setPage(1);
  }, []);

  const handleKindFilterChange = useCallback((value) => {
    setKindFilter(value);
    setPage(1);
  }, []);

  const handleReset = useCallback(() => {
    setStateFilter(null);
    setKindFilter(null);
    setPage(1);
  }, []);

  return (
    <PageShell editorialHeader={<Masthead total={total} />}>
      {/* M2-5.10.D — Tabs Pilotage / Référentiel posés en tête de body. */}
      <PilotageTabs />

      {/* M2-5.11.C — Synthèse 5 compteurs CFO (P0/P1/sans pilote/à risque/sécurisés). */}
      <NarrativeBar />

      <ListFilterBar
        stateFilter={stateFilter}
        onStateFilterChange={handleStateFilterChange}
        kindFilter={kindFilter}
        onKindFilterChange={handleKindFilterChange}
        kindCounts={kindCounts}
        onReset={handleReset}
      />

      {loading && <SkeletonTable rows={5} cols={5} />}

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
