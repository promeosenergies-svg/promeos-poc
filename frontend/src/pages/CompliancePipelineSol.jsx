/**
 * PROMEOS — CompliancePipelineSol (Lot 6 Phase 5, Pattern B)
 *
 * Hero Sol + tableau complet pour /compliance/pipeline. Injecté au
 * sommet de CompliancePipelinePage.jsx. Le legacy body (DtProgress
 * multisite + top blockers section + sites grid + drawer "Pourquoi ?")
 * est wrapped `{false && (…)}` en P5.3 (rollback propre).
 *
 * Pattern B pur : SolListPage wrapper + kpiRow 3 SolKpiCard + toolbar
 * filtres + expert grid 8 cols + pagination.
 *
 * Zéro logique métier côté JSX : tous les agrégats, buckets et enums
 * passent par `sol_presenters.js` (14+ helpers testés 59/59).
 * Aria-labels construits via `buildKpiAriaLabel(code, summary)`.
 * Filtres via `buildFilterConfig(summary)`. Tri via `sortRows`.
 * Pagination via `paginateRows` et SolPagination (self-null < pageSize).
 */
import React, { useState, useMemo } from 'react';
import {
  SolListPage,
  SolExpertToolbar,
  SolExpertGridFull,
  SolPagination,
  SolKpiRow,
  SolKpiCard,
  SolStatusPill,
} from '../ui/sol';
import {
  hasSummary,
  formatSitesReady,
  formatDeadlinesD30,
  formatUntrustedSites,
  buildKickerText,
  buildNarrative,
  buildSubNarrative,
  buildEmptyState,
  buildKpiAriaLabel,
  buildFilterConfig,
  interpretSitesReady,
  interpretDeadlinesD30,
  interpretUntrustedSites,
  pipelineRows,
  filterRows,
  sortRows,
  paginateRows,
  NBSP,
} from './compliance-pipeline/sol_presenters';

const TONE_TO_SEMANTIC = {
  succes: 'score',
  calme: 'neutral',
  attention: 'cost',
  refuse: 'cost',
};

const GATE_TO_KIND = { OK: 'ok', WARNING: 'att', BLOCKED: 'risk', UNKNOWN: 'att' };
const ENDPOINT = '/api/compliance/portfolio/summary';

/**
 * @param {Object} props
 * @param {Object|null} props.summary         getPortfolioComplianceSummary({site_id?})
 * @param {boolean} [props.isLoading]
 * @param {Error|null} [props.error]
 * @param {(row)=>void} [props.onRowClick]    drill vers /sites/:id?tab=compliance
 */
export default function CompliancePipelineSol({
  summary,
  isLoading = false,
  error = null,
  onRowClick,
}) {
  const [sortBy, setSortBy] = useState({ column: 'compliance_score', direction: 'asc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({
    search: '',
    gate_status: '',
    framework: '',
    untrustedOnly: '',
  });

  // Helpers memoïsés (listes potentiellement grandes en portfolio multi-sites)
  const untrustedIds = useMemo(() => {
    if (!hasSummary(summary)) return new Set();
    const arr = Array.isArray(summary.untrusted_sites) ? summary.untrusted_sites : [];
    return new Set(arr.map((u) => u.site_id));
  }, [summary]);

  const rowsAll = useMemo(() => pipelineRows(summary), [summary]);

  const filtered = useMemo(
    () =>
      filterRows(rowsAll, {
        search: filters.search,
        gate_status: filters.gate_status || 'all',
        framework: filters.framework || 'all',
        untrustedIds,
        untrustedOnly: filters.untrustedOnly === 'untrusted',
      }),
    [rowsAll, filters, untrustedIds]
  );

  const sorted = useMemo(() => sortRows(filtered, sortBy), [filtered, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const filterConfig = useMemo(() => buildFilterConfig(summary), [summary]);

  // 1. Loading
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Chargement du pipeline conformité"
        style={{ padding: '24px 28px', color: 'var(--sol-ink-500)', fontStyle: 'italic' }}
      >
        Chargement du pipeline conformité portefeuille…
      </div>
    );
  }

  // 2. Error
  if (error) {
    return (
      <div
        role="alert"
        style={{
          padding: '24px 28px',
          background: 'var(--sol-refuse-bg)',
          border: '1px solid var(--sol-refuse-fg)',
          borderRadius: 6,
          color: 'var(--sol-refuse-fg)',
          margin: '24px 28px 0',
        }}
      >
        <strong>Erreur chargement pipeline{NBSP}:</strong> {error.message || String(error)}
      </div>
    );
  }

  // 3. Empty
  const empty = buildEmptyState({ summary });
  if (empty) {
    return (
      <div
        role="region"
        aria-label="État vide pipeline conformité"
        style={{
          padding: 28,
          margin: '24px 28px 0',
          background: 'var(--sol-attention-bg)',
          border: '1px dashed var(--sol-attention-fg)',
          borderRadius: 6,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 17,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: '0 0 6px',
          }}
        >
          {empty.title}
        </p>
        <p
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 13.5,
            color: 'var(--sol-ink-700)',
            margin: 0,
            lineHeight: 1.45,
          }}
        >
          {empty.message}
        </p>
      </div>
    );
  }

  // 4. Happy path — tous les agrégats passent par helpers testés
  const kicker = buildKickerText(summary);
  const narrative = buildNarrative(summary);
  const subNarrative = buildSubNarrative(summary);
  const sitesReady = formatSitesReady(summary);
  const deadlinesD30 = formatDeadlinesD30(summary);
  const untrustedSites = formatUntrustedSites(summary);

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Sites prêts"
        value={sitesReady.value != null ? String(sitesReady.value) : '—'}
        unit={sitesReady.total != null ? `/ ${sitesReady.total}` : ''}
        semantic={TONE_TO_SEMANTIC[sitesReady.tone] || 'neutral'}
        explainKey="pipeline_sites_ready"
        headline={interpretSitesReady(summary)}
        ariaLabel={buildKpiAriaLabel('pipeline_sites_ready', summary)}
        source={{ kind: 'calcul', origin: ENDPOINT }}
      />
      <SolKpiCard
        label="Échéances < 30 j"
        value={deadlinesD30.value != null ? String(deadlinesD30.value) : '—'}
        unit="imminentes"
        semantic={TONE_TO_SEMANTIC[deadlinesD30.tone] || 'neutral'}
        explainKey="pipeline_deadlines_d30"
        headline={interpretDeadlinesD30(summary)}
        ariaLabel={buildKpiAriaLabel('pipeline_deadlines_d30', summary)}
        source={{ kind: 'calcul', origin: ENDPOINT }}
      />
      <SolKpiCard
        label="Sites non fiables"
        value={untrustedSites.value != null ? String(untrustedSites.value) : '—'}
        unit={untrustedSites.total != null ? `/ ${untrustedSites.total}` : ''}
        semantic={TONE_TO_SEMANTIC[untrustedSites.tone] || 'neutral'}
        explainKey="pipeline_untrusted_sites"
        headline={interpretUntrustedSites(summary)}
        ariaLabel={buildKpiAriaLabel('pipeline_untrusted_sites', summary)}
        source={{ kind: 'calcul', origin: ENDPOINT }}
      />
    </SolKpiRow>
  );

  const handleSort = (col) => {
    setSortBy((prev) =>
      prev.column === col
        ? { column: col, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { column: col, direction: 'asc' }
    );
  };

  const handleFilterChange = (id, value) => {
    setFilters((prev) => ({ ...prev, [id]: value }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({ search: '', gate_status: '', framework: '', untrustedOnly: '' });
    setPage(1);
  };

  const activeFilterCount =
    (filters.search ? 1 : 0) +
    (filters.gate_status ? 1 : 0) +
    (filters.framework ? 1 : 0) +
    (filters.untrustedOnly ? 1 : 0);

  const columns = [
    { id: 'site_nom', label: 'Site', sortable: true, align: 'left' },
    {
      id: 'gate_status',
      label: 'Gate data',
      sortable: true,
      width: 110,
      render: (v) => <SolStatusPill kind={GATE_TO_KIND[v] || 'att'}>{v || '—'}</SolStatusPill>,
    },
    {
      id: 'completeness_pct',
      label: 'Complétude',
      sortable: true,
      width: 110,
      align: 'right',
      render: (v) => `${v}${NBSP}%`,
    },
    {
      id: 'compliance_score',
      label: 'Score',
      sortable: true,
      width: 90,
      align: 'right',
      render: (v) => String(v),
    },
    {
      id: 'reg_risk',
      label: 'Risque',
      sortable: true,
      width: 90,
      align: 'right',
      render: (v) => String(v),
    },
    {
      id: 'financial_opportunity_eur',
      label: 'Opportunité',
      sortable: true,
      width: 120,
      align: 'right',
      render: (v) => (v > 0 ? `${v.toLocaleString('fr-FR')}${NBSP}€` : '—'),
    },
    {
      id: 'applicable_dt',
      label: 'DT',
      sortable: true,
      width: 60,
      align: 'center',
      render: (v) => (v ? '✓' : '—'),
    },
    {
      id: 'applicable_bacs',
      label: 'BACS',
      sortable: true,
      width: 70,
      align: 'center',
      render: (v) => (v ? '✓' : '—'),
    },
    {
      id: 'applicable_aper',
      label: 'APER',
      sortable: true,
      width: 70,
      align: 'center',
      render: (v) => (v ? '✓' : '—'),
    },
  ];

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        gate_status: filters.gate_status || '',
        framework: filters.framework || '',
        untrustedOnly: filters.untrustedOnly || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder="Rechercher un site…"
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
      onRowClick={onRowClick}
      highlightColumn="compliance_score"
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

  const rightSlot =
    activeFilterCount > 0 ? (
      <button
        type="button"
        onClick={resetFilters}
        className="sol-btn sol-btn--ghost"
        style={{ fontSize: 11 }}
      >
        Réinitialiser filtres
      </button>
    ) : null;

  return (
    <SolListPage
      kicker={kicker}
      title="Pipeline conformité"
      titleEm="· portefeuille"
      narrative={narrative}
      subNarrative={subNarrative}
      rightSlot={rightSlot}
      kpiRow={kpiRow}
      toolbar={toolbar}
      grid={grid}
      pagination={pagination}
    />
  );
}
