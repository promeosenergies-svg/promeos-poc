/**
 * PROMEOS — WatchersSol (Lot 2 Phase 7, Pattern B avec prélude cards)
 *
 * Rendu Sol de /watchers. WatchersPage.jsx (loader 327 LOC) reste
 * responsable du fetch listWatchers + listRegEvents, de runWatcher,
 * et de l'ouverture du Review Modal legacy. WatchersSol injecte le
 * Pattern B pur avec un preludeSlot de SolWatcherCard (au lieu du
 * SolKpiRow habituel) : les watchers sont des OBJETS ACTIONABLES,
 * pas des chiffres agrégés.
 */
import React, { useState, useMemo } from 'react';
import {
  SolListPage,
  SolExpertToolbar,
  SolExpertGridFull,
  SolPagination,
  SolStatusPill,
  SolWatcherCard,
  SolButton,
  SolSectionHead,
} from '../ui/sol';
import {
  buildWatchersKicker,
  buildWatchersNarrative,
  buildWatchersSubNarrative,
  buildEventRows,
  buildEmptyState,
  buildFilterConfig,
  filterRows,
  sortRows,
  paginateRows,
  STATUS_LABELS,
  toneFromStatus,
  formatDateFR,
  NBSP,
} from './watchers/sol_presenters';

/**
 * @param {Object} props
 * @param {Array} props.watchers         listWatchers().watchers
 * @param {Array} props.events           listRegEvents().events
 * @param {Object} [props.runResults]    { [watcherName]: { loading?, new_events?, error? } }
 * @param {(name)=>void} props.onRunWatcher
 * @param {(event)=>void} props.onReviewEvent  triggers Review Modal legacy
 * @param {()=>void} [props.onRefresh]
 * @param {boolean} [props.loading]
 */
export default function WatchersSol({
  watchers = [],
  events = [],
  runResults = {},
  onRunWatcher,
  onReviewEvent,
  onRefresh,
  loading = false,
}) {
  const [sortBy, setSortBy] = useState({ column: 'published_at', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({ search: '', source: '', status: '' });

  const rowsAll = useMemo(() => buildEventRows(events), [events]);
  const filtered = useMemo(() => filterRows(rowsAll, filters), [rowsAll, filters]);
  const sorted = useMemo(() => sortRows(filtered, sortBy), [filtered, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const kicker = buildWatchersKicker({ watchersCount: watchers.length });
  const narrative = buildWatchersNarrative({ watchers, events });
  const subNarrative = buildWatchersSubNarrative({ events });

  const hasFilters = Boolean(filters.search || filters.source || filters.status);
  const emptyState = buildEmptyState({ hasFilters, hasAnyEvent: rowsAll.length > 0 });
  const filterConfig = useMemo(() => buildFilterConfig({ watchers, events }), [watchers, events]);

  const activeFilterCount =
    (filters.search ? 1 : 0) + (filters.source ? 1 : 0) + (filters.status ? 1 : 0);

  const handleSort = (col) => {
    setSortBy((prev) =>
      prev.column === col
        ? { column: col, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { column: col, direction: 'desc' }
    );
  };

  const handleFilterChange = (id, value) => {
    setFilters((prev) => ({ ...prev, [id]: value }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({ search: '', source: '', status: '' });
    setPage(1);
  };

  // Prélude : grid de SolWatcherCards (max 6 visibles)
  const preludeSlot = watchers.length > 0 && (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <SolSectionHead
        title="Watchers actifs"
        meta={`${watchers.length}${NBSP}source${watchers.length > 1 ? 's' : ''} surveillée${watchers.length > 1 ? 's' : ''}`}
      />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 14,
        }}
      >
        {watchers.slice(0, 6).map((w) => {
          const r = runResults[w.name];
          const status = r?.loading
            ? 'running'
            : r?.error
              ? 'error'
              : r?.new_events != null
                ? 'ok'
                : 'idle';
          const resultMessage = r?.error
            ? `Erreur : ${r.error}`
            : r?.new_events != null
              ? `${r.new_events}${NBSP}nouveau${r.new_events > 1 ? 'x' : ''} événement${r.new_events > 1 ? 's' : ''}`
              : null;
          return (
            <SolWatcherCard
              key={w.name}
              name={w.name}
              description={w.description}
              status={status}
              resultMessage={resultMessage}
              onRun={() => onRunWatcher?.(w.name)}
            />
          );
        })}
      </div>
    </div>
  );

  const columns = [
    {
      id: 'published_at',
      label: 'Publié le',
      sortable: true,
      width: 120,
      render: (v) => formatDateFR(v),
    },
    { id: 'source_name', label: 'Source', sortable: true, width: 140 },
    { id: 'title', label: 'Événement', align: 'left' },
    {
      id: 'tags',
      label: 'Tags',
      width: 140,
      render: (v) =>
        v ? (
          <span
            style={{
              color: 'var(--sol-ink-500)',
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 10.5,
            }}
          >
            {v}
          </span>
        ) : (
          '—'
        ),
    },
    {
      id: 'status',
      label: 'Statut',
      sortable: true,
      width: 110,
      render: (v) => {
        const label = STATUS_LABELS[v] || v || 'Nouveau';
        const tone = toneFromStatus(v);
        const kind =
          { calme: 'ok', attention: 'att', afaire: 'att', refuse: 'risk', succes: 'ok' }[tone] ||
          'att';
        return <SolStatusPill kind={kind}>{label}</SolStatusPill>;
      },
    },
    {
      id: 'actions',
      label: 'Actions',
      width: 130,
      render: (_, row) => {
        const raw = row.cells._raw;
        const isNew = !raw.status || raw.status === 'new';
        const safeUrl =
          typeof raw.url === 'string' && /^https?:\/\//i.test(raw.url) ? raw.url : null;
        return (
          <div style={{ display: 'flex', gap: 6 }}>
            {safeUrl && (
              <a
                href={safeUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                style={{
                  fontSize: 11,
                  color: 'var(--sol-calme-fg)',
                  textDecoration: 'underline',
                  fontFamily: 'var(--sol-font-mono)',
                }}
              >
                source ↗
              </a>
            )}
            {isNew && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onReviewEvent?.(raw);
                }}
                className="sol-btn sol-btn--secondary"
                style={{ fontSize: 11, padding: '2px 8px' }}
              >
                Réviser
              </button>
            )}
          </div>
        );
      },
    },
  ];

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        source: filters.source || '',
        status: filters.status || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder="Rechercher un événement, source, tag…"
      searchValue={filters.search || ''}
      onSearchChange={(v) => handleFilterChange('search', v)}
      activeFilterCount={activeFilterCount}
    />
  );

  const grid = (
    <SolExpertGridFull
      columns={columns}
      rows={pageRows}
      sortBy={sortBy}
      onSort={handleSort}
      onRowClick={(row) => onReviewEvent?.(row.cells._raw)}
      emptyState={emptyState}
      loading={loading}
      highlightColumn="status"
    />
  );

  const pagination = (
    <SolPagination
      page={page}
      pageSize={pageSize}
      total={sorted.length}
      onPageChange={setPage}
      onPageSizeChange={setPageSize}
    />
  );

  const rightSlot = (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {hasFilters && (
        <button
          type="button"
          onClick={resetFilters}
          className="sol-btn sol-btn--ghost"
          style={{ fontSize: 11 }}
        >
          Réinitialiser filtres
        </button>
      )}
      {onRefresh && (
        <SolButton variant="secondary" onClick={onRefresh}>
          Actualiser
        </SolButton>
      )}
    </div>
  );

  return (
    <SolListPage
      kicker={kicker}
      title="Veille"
      titleEm={`· ${watchers.length}${NBSP}watcher${watchers.length > 1 ? 's' : ''} · ${events.length}${NBSP}événement${events.length > 1 ? 's' : ''}`}
      narrative={narrative}
      subNarrative={subNarrative}
      rightSlot={rightSlot}
      preludeSlot={preludeSlot}
      toolbar={toolbar}
      grid={grid}
      pagination={pagination}
    />
  );
}
