import { useCallback, useMemo, useState } from 'react';
import { ClipboardList } from 'lucide-react';

import PageShell from '../../ui/PageShell';
import { SkeletonTable } from '../../ui/Skeleton';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import Pagination from '../../ui/Pagination';

import { useActionCenterV4Items } from '../../hooks/v4';
import { COPY, MASTHEAD_COPY, PAGE_SIZE } from './constants';
import { ItemsTable } from './components/ItemsTable';
import { ItemDetailDrawer } from './components/ItemDetailDrawer';
import { ListFilterBar } from './components/ListFilterBar';

/**
 * M2-5.2 → M2-5.10.A — Page liste du Centre d'Action V4 (`/action-center-v4`).
 *
 * Liste paginée (20/page), filtres lifecycle + kind client-side, états
 * loading/vide/erreur. Clic sur une ligne → drawer détail (read-only puis
 * write M2-5.4-.6).
 *
 * M2-5.10.A : masthead italique Sol au-dessus des filtres + refonte
 * pixel-perfect (cf. maquette §8.3, `centre_action_v4_referentiel.html`).
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

  // M2-5.10.A — symétrique pour le filtre kind.
  const handleKindFilterChange = useCallback((value) => {
    setKindFilter(value);
    setPage(1);
  }, []);

  const handleReset = useCallback(() => {
    setStateFilter(null);
    setKindFilter(null);
    setPage(1);
  }, []);

  // Date « MAJ live » — dérivée à l'affichage, format FR court (jour DD MM).
  // Pas de calcul backend : c'est la date courante, repère utilisateur.
  const liveDate = useMemo(() => {
    const d = new Date();
    return d.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }, []);

  return (
    <PageShell icon={ClipboardList} title={COPY.pageTitle} subtitle={COPY.pageSubtitle}>
      {/* Masthead Sol — bandeau italique au-dessus des filtres (maquette
          §8.3 lignes 703-707). Bordure inférieure ink-900 = signature
          éditoriale Fraunces. */}
      <div
        className="mb-4 flex items-baseline justify-between gap-4 pb-2.5"
        style={{ borderBottom: '1px solid var(--sol-ink-900)' }}
      >
        <div
          className="text-[13px] italic"
          style={{
            fontFamily: 'var(--sol-font-display)',
            color: 'var(--sol-ink-900)',
            letterSpacing: '0.02em',
          }}
        >
          <span className="font-semibold not-italic">{MASTHEAD_COPY.title}</span> ·{' '}
          {MASTHEAD_COPY.subtitle}
        </div>
        <div
          className="font-mono text-[10.5px] uppercase tracking-[0.16em]"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {liveDate} · {MASTHEAD_COPY.dateLive}
        </div>
      </div>

      <ListFilterBar
        stateFilter={stateFilter}
        onStateFilterChange={handleStateFilterChange}
        kindFilter={kindFilter}
        onKindFilterChange={handleKindFilterChange}
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
