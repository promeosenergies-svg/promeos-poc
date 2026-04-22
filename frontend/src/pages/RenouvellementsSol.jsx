/**
 * PROMEOS — RenouvellementsSol (Lot 2 Phase 4, Pattern B pur)
 *
 * Rendu Sol de /renouvellements. Le parent ContractRadarPage.jsx
 * garde data fetch (getContractRadar + getSegmentationProfile),
 * selectedContract state, ScenarioDrawer + ScenarioSummaryModal +
 * SegmentationQuestionnaireModal intégralement préservés.
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
  buildRenewalsKicker,
  buildRenewalsNarrative,
  buildRenewalsSubNarrative,
  buildRenewalRows,
  computeRenewalsKpis,
  interpretImminentCount,
  interpretReadinessAvg,
  interpretExpiredCount,
  buildEmptyState,
  buildFilterConfig,
  filterRows,
  sortRows,
  paginateRows,
  URGENCY_LABELS,
  STATUS_LABELS,
  toneFromUrgency,
  toneFromStatus,
  formatDateFR,
  NBSP,
} from './renouvellements/sol_presenters';

/**
 * @param {Object} props
 * @param {Array} props.contracts         getContractRadar().contracts
 * @param {number} props.horizon          30/60/90/180/365
 * @param {(n)=>void} props.onHorizonChange
 * @param {boolean} [props.loading]
 * @param {string} [props.scopeLabel]
 * @param {Object} [props.segProfile]
 * @param {()=>void} [props.onOpenSegModal]
 * @param {(contract)=>void} props.onOpenScenario triggers ScenarioDrawer legacy
 */
export default function RenouvellementsSol({
  contracts = [],
  horizon = 90,
  onHorizonChange,
  loading = false,
  scopeLabel,
  segProfile,
  onOpenSegModal,
  onOpenScenario,
}) {
  const [sortBy, setSortBy] = useState({ column: 'days_to_end', direction: 'asc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({ search: '', supplier: '', status: '', urgency: '' });

  const kpis = useMemo(() => computeRenewalsKpis(contracts), [contracts]);
  const rowsAll = useMemo(() => buildRenewalRows(contracts), [contracts]);
  const filtered = useMemo(() => filterRows(rowsAll, filters), [rowsAll, filters]);
  const sorted = useMemo(() => sortRows(filtered, sortBy), [filtered, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const kicker = buildRenewalsKicker({ scopeLabel, imminentCount: kpis.imminentCount90d });
  const narrative = useMemo(() => buildRenewalsNarrative({ contracts, kpis }), [contracts, kpis]);
  const subNarrative = useMemo(() => buildRenewalsSubNarrative({ kpis }), [kpis]);

  const hasFilters = Boolean(
    filters.search || filters.supplier || filters.status || filters.urgency
  );
  const emptyState = buildEmptyState({ hasFilters, hasAnyRenewal: rowsAll.length > 0 });
  const filterConfig = useMemo(() => buildFilterConfig({ contracts }), [contracts]);

  const activeFilterCount =
    (filters.search ? 1 : 0) +
    (filters.supplier ? 1 : 0) +
    (filters.status ? 1 : 0) +
    (filters.urgency ? 1 : 0);

  const handleSort = (columnId) => {
    setSortBy((prev) =>
      prev.column === columnId
        ? { column: columnId, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { column: columnId, direction: 'asc' }
    );
  };

  const handleFilterChange = (id, value) => {
    setFilters((prev) => ({ ...prev, [id]: value }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({ search: '', supplier: '', status: '', urgency: '' });
    setPage(1);
  };

  const columns = [
    { id: 'site', label: 'Site', sortable: true, width: 160, align: 'left' },
    { id: 'supplier', label: 'Fournisseur', sortable: true, width: 150, align: 'left' },
    {
      id: 'end_date',
      label: 'Échéance',
      sortable: true,
      width: 130,
      render: (v) => formatDateFR(v),
    },
    {
      id: 'days_to_end',
      label: 'Jours',
      sortable: true,
      align: 'right',
      width: 90,
      render: (v, row) => {
        if (v == null) return '—';
        const cells = row.cells;
        const kind =
          cells.status === 'expired' || v < 0 ? 'risk' : v <= 30 ? 'risk' : v <= 90 ? 'att' : 'ok';
        return (
          <SolStatusPill kind={kind}>
            {v < 0 ? `+${Math.abs(v)}${NBSP}j` : `${v}${NBSP}j`}
          </SolStatusPill>
        );
      },
    },
    {
      id: 'urgency',
      label: 'Urgence',
      sortable: true,
      width: 100,
      render: (v) => {
        const label = URGENCY_LABELS[v] || v || '—';
        const tone = toneFromUrgency(v);
        const kind =
          { calme: 'ok', attention: 'att', afaire: 'att', refuse: 'risk', succes: 'ok' }[tone] ||
          'att';
        return <SolStatusPill kind={kind}>{label}</SolStatusPill>;
      },
    },
    {
      id: 'indexation',
      label: 'Indexation',
      width: 130,
      render: (v) => v || '—',
    },
    {
      id: 'readiness',
      label: 'Données',
      sortable: true,
      align: 'right',
      width: 110,
      render: (v) => {
        if (v == null)
          return <span style={{ color: 'var(--sol-ink-400)', fontStyle: 'italic' }}>n/d</span>;
        const color =
          v >= 80
            ? 'var(--sol-succes-fg)'
            : v >= 50
              ? 'var(--sol-attention-fg)'
              : 'var(--sol-refuse-fg)';
        return <span style={{ color, fontWeight: 600 }}>{v}%</span>;
      },
    },
    {
      id: 'status',
      label: 'Statut',
      sortable: true,
      width: 110,
      render: (v) => {
        const label = STATUS_LABELS[v] || v || '—';
        const tone = toneFromStatus(v);
        const kind =
          { calme: 'ok', attention: 'att', afaire: 'att', refuse: 'risk', succes: 'ok' }[tone] ||
          'att';
        return <SolStatusPill kind={kind}>{label}</SolStatusPill>;
      },
    },
  ];

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        supplier: filters.supplier || '',
        urgency: filters.urgency || '',
        status: filters.status || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder="Site, fournisseur, contrat…"
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
      onRowClick={(row) => onOpenScenario?.(row.cells._raw)}
      emptyState={emptyState}
      loading={loading}
      highlightColumn="days_to_end"
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Renouvellements imminents"
        value={kpis.imminentCount90d > 0 ? String(kpis.imminentCount90d) : '—'}
        unit={kpis.imminentCount90d > 1 ? 'contrats < 90 j' : 'contrat < 90 j'}
        semantic="cost"
        explainKey="renewal_imminent_count"
        headline={interpretImminentCount({ kpis })}
        source={{ kind: 'calcul', origin: 'radar contrats V99' }}
      />
      <SolKpiCard
        label="Score préparation"
        value={kpis.readinessAvg != null ? String(kpis.readinessAvg) : '—'}
        unit="/100"
        semantic="score"
        explainKey="renewal_readiness_score"
        headline={interpretReadinessAvg({ kpis })}
        source={{ kind: 'calcul', origin: 'moyenne readiness contrats' }}
      />
      <SolKpiCard
        label="Contrats expirés"
        value={kpis.expiredCount > 0 ? String(kpis.expiredCount) : '—'}
        unit={kpis.expiredCount > 1 ? 'à régulariser' : 'à régulariser'}
        semantic="cost"
        explainKey="renewal_expired_count"
        headline={interpretExpiredCount({ kpis })}
        source={{ kind: 'calcul', origin: 'days_to_end < 0' }}
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

  const horizonButtons = (
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
      {[30, 60, 90, 180, 365].map((h) => (
        <button
          key={h}
          type="button"
          onClick={() => onHorizonChange?.(h)}
          aria-pressed={h === horizon}
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11,
            padding: '4px 10px',
            border: 'none',
            borderRadius: 4,
            background: h === horizon ? 'var(--sol-calme-bg)' : 'transparent',
            color: h === horizon ? 'var(--sol-calme-fg)' : 'var(--sol-ink-500)',
            fontWeight: h === horizon ? 600 : 400,
            cursor: 'pointer',
          }}
        >
          {h === 365 ? '1 an' : `${h} j`}
        </button>
      ))}
    </div>
  );

  const segBadge =
    segProfile?.has_profile && segProfile.confidence_score < 50 ? (
      <button
        type="button"
        onClick={onOpenSegModal}
        style={{
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 10.5,
          padding: '4px 10px',
          borderRadius: 4,
          border: '1px solid var(--sol-attention-fg)',
          background: 'var(--sol-attention-bg)',
          color: 'var(--sol-attention-fg)',
          cursor: 'pointer',
        }}
      >
        Profil {Math.round(segProfile.confidence_score)}% · Affiner
      </button>
    ) : null;

  const rightSlot = (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
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
      {segBadge}
      {horizonButtons}
    </div>
  );

  return (
    <SolListPage
      breadcrumb={{
        segments: [{ label: 'Patrimoine', to: '/patrimoine' }, { label: 'Renouvellements' }],
        backTo: '/patrimoine',
      }}
      kicker={kicker}
      title="Renouvellements"
      titleEm={`· horizon ${horizon === 365 ? '1 an' : horizon + ' jours'}`}
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
