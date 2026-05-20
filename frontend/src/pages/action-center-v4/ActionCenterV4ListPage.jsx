import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import PageShell from '../../ui/PageShell';
import { SkeletonTable } from '../../ui/Skeleton';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import Pagination from '../../ui/Pagination';

import { useActionCenterV4Items } from '../../hooks/v4';
import { COPY, LIFECYCLE_ORDER, PAGE_SIZE } from './constants';
import { KIND_LABELS } from './constants';
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
/**
 * M2-5.11.K — Validation stricte des params URL (CX +0.3 backlog).
 *
 * Évite qu'un deep link malicieux/copié injecte un état UI imprévu :
 * - `state=xxx` doit être ∈ LIFECYCLE_ORDER, sinon ignoré.
 * - `kind=xxx` doit être ∈ KIND_LABELS, sinon ignoré.
 * - `page` doit être un entier ≥ 1, sinon page=1.
 *
 * Pas de calcul métier — juste un sanity check de l'input external.
 */
const VALID_KINDS = new Set(Object.keys(KIND_LABELS));
const VALID_STATES = new Set(LIFECYCLE_ORDER);

function parseFilterParams(searchParams) {
  const rawState = searchParams.get('state');
  const rawKind = searchParams.get('kind');
  const rawPage = parseInt(searchParams.get('page') ?? '', 10);
  return {
    stateFilter: rawState && VALID_STATES.has(rawState) ? rawState : null,
    kindFilter: rawKind && VALID_KINDS.has(rawKind) ? rawKind : null,
    page: Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1,
  };
}

export function ActionCenterV4ListPage() {
  // M2-5.11.K — état filtres + page persisté en query params (audit CX backlog
  // « Filter state loss on cross-page navigation »). Le drawer + cross-page
  // → retour conserve désormais les filtres ; un share-link reflète la vue.
  const [searchParams, setSearchParams] = useSearchParams();
  const { stateFilter, kindFilter, page } = parseFilterParams(searchParams);

  // Le drawer reste en state local : pas besoin de persister l'item ouvert
  // dans l'URL (UX bizarre au refresh — réouverture systématique non désirée).
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

  // M2-5.11.K — helper centralisé pour synchro URL ↔ state filtres. Tout
  // changement remet page=1 (M2-5.9.bis : filtrer depuis une page profonde
  // laisserait une page vide trompeuse). On passe `replace: true` pour ne
  // pas polluer l'historique navigateur avec un entry par click chip.
  const updateFilters = useCallback(
    (next) => {
      setSearchParams(
        (prev) => {
          const sp = new URLSearchParams(prev);
          // `next === null` → suppression du param. `undefined` → no-op.
          const apply = (key, value) => {
            if (value === undefined) return;
            if (value === null) sp.delete(key);
            else sp.set(key, value);
          };
          apply('state', next.stateFilter);
          apply('kind', next.kindFilter);
          // Reset page sauf si explicitement modifié.
          if (next.page !== undefined) {
            if (next.page === 1) sp.delete('page');
            else sp.set('page', String(next.page));
          } else {
            sp.delete('page');
          }
          return sp;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const handleStateFilterChange = useCallback(
    (value) => updateFilters({ stateFilter: value || null }),
    [updateFilters]
  );

  const handleKindFilterChange = useCallback(
    (value) => updateFilters({ kindFilter: value || null }),
    [updateFilters]
  );

  const handleReset = useCallback(
    () => updateFilters({ stateFilter: null, kindFilter: null }),
    [updateFilters]
  );

  const handlePageChange = useCallback(
    (nextPage) => updateFilters({ page: nextPage }),
    [updateFilters]
  );

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
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={handlePageChange} />
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
