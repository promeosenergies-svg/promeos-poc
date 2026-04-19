/**
 * PROMEOS — KBExplorerSol (Lot 6 Phase 2, Pattern B pur)
 *
 * Rendu Sol de /kb. KBExplorerPage.jsx (loader 851 LOC) préservé pour
 * la logique data (searchKBItems + getKBDocs + getKBFullStats + upload
 * + status change + linkTertiaireProof), proof context banner V39.1,
 * deep-link params parsing. KBExplorerSol se concentre sur Pattern B
 * pur avec toggle Items|Documents dans rightSlot (custom, pas nouveau
 * composant Sol).
 */
import React, { useState, useMemo } from 'react';
import {
  SolListPage,
  SolKpiRow,
  SolKpiCard,
  SolExpertToolbar,
  SolExpertGridFull,
  SolPagination,
  SolStatusPill,
} from '../ui/sol';
import {
  buildKbKicker,
  buildKbNarrative,
  buildKbSubNarrative,
  computeKpis,
  interpretTotalItems,
  interpretValidatedRatio,
  interpretDomainsCovered,
  buildItemRows,
  buildDocRows,
  filterRows,
  sortRows,
  paginateRows,
  buildEmptyState,
  buildFilterConfig,
  DOMAIN_LABELS,
  TYPE_LABELS,
  STATUS_LABELS,
  toneFromStatus,
  toneFromConfidence,
  formatDateFR,
  formatFR,
  NBSP,
} from './kb/sol_presenters';

/**
 * @param {Object} props
 * @param {Array} props.items         searchKBItems().results
 * @param {Array} props.docs          getKBDocs().docs
 * @param {Object} props.stats        getKBFullStats()
 * @param {string} props.activeTab    'items' | 'docs'
 * @param {(tab)=>void} props.onTabChange
 * @param {boolean} [props.loading]
 * @param {Object} [props.proofContext]  V39.1 deep-link context
 * @param {string} [props.initialSearch]
 * @param {string} [props.initialDomain]
 * @param {(row)=>void} [props.onRowClick]  expansion OR navigate
 * @param {ReactNode} [props.preludeSlot]  proof banner si contexte deep-link
 */
export default function KBExplorerSol({
  items = [],
  docs = [],
  stats = null,
  activeTab = 'items',
  onTabChange,
  loading = false,
  initialSearch = '',
  initialDomain = null,
  onRowClick,
  preludeSlot,
}) {
  const [sortBy, setSortBy] = useState({ column: 'updated_at', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({
    search: initialSearch || '',
    domain: initialDomain || '',
    type: '',
    status: '',
  });
  const [expandedId, setExpandedId] = useState(null);

  const rowsAll = useMemo(
    () => (activeTab === 'docs' ? buildDocRows(docs) : buildItemRows(items)),
    [activeTab, items, docs]
  );
  const filtered = useMemo(() => filterRows(rowsAll, filters), [rowsAll, filters]);
  const sorted = useMemo(() => sortRows(filtered, sortBy), [filtered, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const kpis = useMemo(() => computeKpis(stats), [stats]);
  const kicker = buildKbKicker({ activeTab, stats });
  const narrative = buildKbNarrative({ stats, activeTab });
  const subNarrative = buildKbSubNarrative({ stats });

  const hasFilters = Boolean(filters.search || filters.domain || filters.type || filters.status);
  const emptyState = buildEmptyState({ hasFilters, hasAny: rowsAll.length > 0 });
  const filterConfig = useMemo(
    () => buildFilterConfig({ activeTab, stats }),
    [activeTab, stats]
  );

  const activeFilterCount =
    (filters.search ? 1 : 0) +
    (filters.domain ? 1 : 0) +
    (filters.type ? 1 : 0) +
    (filters.status ? 1 : 0);

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
    setFilters({ search: '', domain: '', type: '', status: '' });
    setPage(1);
  };

  const handleRowClick = (row) => {
    setExpandedId((prev) => (prev === row.id ? null : row.id));
    onRowClick?.(row);
  };

  // Columns dynamiques selon mode
  const itemColumns = [
    { id: 'title', label: 'Article', sortable: true, align: 'left' },
    {
      id: 'domain',
      label: 'Domaine',
      sortable: true,
      width: 130,
      render: (v) => (v ? DOMAIN_LABELS[v] || v : '—'),
    },
    {
      id: 'type',
      label: 'Type',
      sortable: true,
      width: 110,
      render: (v) => {
        if (!v) return '—';
        return <SolStatusPill kind="neutral">{TYPE_LABELS[v] || v}</SolStatusPill>;
      },
    },
    {
      id: 'confidence',
      label: 'Confiance',
      sortable: true,
      width: 110,
      render: (v) => {
        const tone = toneFromConfidence(v);
        const kind = { succes: 'ok', attention: 'att', afaire: 'neutral', calme: 'ok' }[tone] || 'neutral';
        return <SolStatusPill kind={kind}>{v || '—'}</SolStatusPill>;
      },
    },
    {
      id: 'status',
      label: 'Statut',
      sortable: true,
      width: 110,
      render: (v) => {
        const tone = toneFromStatus(v);
        const kind = { succes: 'ok', attention: 'att', afaire: 'att', calme: 'ok', refuse: 'risk' }[tone] || 'att';
        return <SolStatusPill kind={kind}>{STATUS_LABELS[v] || v || '—'}</SolStatusPill>;
      },
    },
    {
      id: 'updated_at',
      label: 'Mise à jour',
      sortable: true,
      width: 120,
      render: (v) => formatDateFR(v),
    },
  ];

  const docColumns = [
    { id: 'title', label: 'Document', sortable: true, align: 'left' },
    {
      id: 'source_type',
      label: 'Format',
      width: 90,
      render: (v) => (
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 10.5,
            textTransform: 'uppercase',
            color: 'var(--sol-ink-500)',
          }}
        >
          {v || '—'}
        </span>
      ),
    },
    {
      id: 'domain',
      label: 'Domaine',
      sortable: true,
      width: 130,
      render: (v) => (v ? DOMAIN_LABELS[v] || v : '—'),
    },
    {
      id: 'nb_chunks',
      label: 'Chunks',
      sortable: true,
      align: 'right',
      width: 90,
      render: (v) => (v > 0 ? formatFR(v, 0) : '—'),
    },
    {
      id: 'status',
      label: 'Statut',
      sortable: true,
      width: 110,
      render: (v) => {
        const tone = toneFromStatus(v);
        const kind = { succes: 'ok', attention: 'att', afaire: 'att', calme: 'ok' }[tone] || 'att';
        return <SolStatusPill kind={kind}>{STATUS_LABELS[v] || v || '—'}</SolStatusPill>;
      },
    },
    {
      id: 'updated_at',
      label: 'Upload',
      sortable: true,
      width: 120,
      render: (v) => formatDateFR(v),
    },
  ];

  const columns = activeTab === 'docs' ? docColumns : itemColumns;

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        domain: filters.domain || '',
        type: filters.type || '',
        status: filters.status || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder={
        activeTab === 'docs'
          ? 'Rechercher un document par titre…'
          : 'Rechercher un article, tag, contenu…'
      }
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
      onRowClick={handleRowClick}
      emptyState={emptyState}
      loading={loading}
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Total indexé"
        value={kpis.total != null ? String(kpis.total) : '—'}
        unit={kpis.total > 1 ? 'articles' : 'article'}
        semantic="neutral"
        explainKey="kb_total_items"
        headline={interpretTotalItems({ stats })}
        source={{ kind: 'calcul', origin: 'moteur FTS5' }}
      />
      <SolKpiCard
        label="Validés"
        value={
          kpis.validatedRatio != null ? `${kpis.validatedRatio}` : '—'
        }
        unit="%"
        semantic="score"
        explainKey="kb_validated_ratio"
        headline={interpretValidatedRatio({ stats })}
        source={{ kind: 'calcul', origin: 'by_status · validated' }}
      />
      <SolKpiCard
        label="Domaines couverts"
        value={kpis.domainsCovered != null ? String(kpis.domainsCovered) : '—'}
        unit="/ 5"
        semantic="score"
        explainKey="kb_domains_covered"
        headline={interpretDomainsCovered({ stats })}
        source={{ kind: 'calcul', origin: 'by_domain non vides' }}
      />
    </SolKpiRow>
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

  // Toggle Items | Documents dans le rightSlot (réutilise pattern horizon Phase 4)
  const tabToggle = (
    <div
      style={{
        display: 'inline-flex',
        gap: 4,
        padding: '2px',
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
      }}
    >
      {[
        { id: 'items', label: 'Items' },
        { id: 'docs', label: 'Documents' },
      ].map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => onTabChange?.(t.id)}
          aria-pressed={t.id === activeTab}
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11,
            padding: '4px 14px',
            border: 'none',
            borderRadius: 4,
            background: t.id === activeTab ? 'var(--sol-calme-bg)' : 'transparent',
            color: t.id === activeTab ? 'var(--sol-calme-fg)' : 'var(--sol-ink-500)',
            fontWeight: t.id === activeTab ? 600 : 400,
            cursor: 'pointer',
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );

  const rightSlot = (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
      {hasFilters && (
        <button
          type="button"
          onClick={resetFilters}
          className="sol-btn sol-btn--ghost"
          style={{ fontSize: 11 }}
        >
          Réinitialiser
        </button>
      )}
      {tabToggle}
    </div>
  );

  // Expanded preview panel (inline, sous la grid)
  const expandedRow = expandedId
    ? pageRows.find((r) => r.id === expandedId)
    : null;
  const expandedPanel = expandedRow && (
    <div
      style={{
        marginTop: 12,
        padding: '18px 22px',
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
        borderLeft: '3px solid var(--sol-calme-fg)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <h3
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 17,
              fontWeight: 600,
              color: 'var(--sol-ink-900)',
              margin: 0,
              marginBottom: 6,
            }}
          >
            {expandedRow.cells.title}
          </h3>
          {expandedRow.cells._raw?.summary && (
            <p
              style={{
                fontFamily: 'var(--sol-font-body)',
                fontSize: 13.5,
                color: 'var(--sol-ink-700)',
                margin: 0,
                lineHeight: 1.55,
                maxWidth: '75ch',
              }}
            >
              {expandedRow.cells._raw.summary}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpandedId(null)}
          aria-label="Fermer le panneau"
          style={{
            background: 'transparent',
            border: 'none',
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 12,
            color: 'var(--sol-ink-500)',
            cursor: 'pointer',
          }}
        >
          ✕ Fermer
        </button>
      </div>
    </div>
  );

  return (
    <SolListPage
      kicker={kicker}
      title="Base de connaissance"
      titleEm={`· ${activeTab === 'docs' ? 'documents sources' : 'items structurés'}`}
      narrative={narrative}
      subNarrative={subNarrative}
      rightSlot={rightSlot}
      kpiRow={kpiRow}
      preludeSlot={preludeSlot}
      toolbar={toolbar}
      grid={
        <>
          {grid}
          {expandedPanel}
        </>
      }
      pagination={pagination}
    />
  );
}
