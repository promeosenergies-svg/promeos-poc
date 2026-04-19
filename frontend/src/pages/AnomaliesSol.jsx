/**
 * PROMEOS — AnomaliesSol (Lot 2 Phase 2, Pattern B pur)
 *
 * Rendu Sol de l'onglet Anomalies de /anomalies. Le parent
 * AnomaliesPage.jsx garde la logique data (fetch multi-source +
 * merge client-side + dismiss + EvidenceDrawer state) + l'onglet
 * Plan d'actions + l'empty state "scope 0 sites". Ce composant se
 * concentre sur le rendu Pattern B pur.
 *
 * Le drawer EvidenceDrawer reste rendu au niveau du parent —
 * AnomaliesSol déclenche juste `onRowClick(row._raw)` qui ouvre
 * le drawer côté parent.
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
  buildAnomaliesKicker,
  buildAnomaliesNarrative,
  buildAnomaliesSubNarrative,
  interpretActiveCount,
  interpretTotalImpact,
  adaptAnomaliesToRows,
  sortAnomaliesRows,
  paginateRows,
  buildEmptyState,
  buildFilterConfig,
  toneFromSeverity,
  SEVERITY_LABELS,
  FRAMEWORK_LABELS,
  formatFREur,
  NBSP,
} from './anomalies/sol_presenters';

/**
 * @param {Object} props
 * @param {Array}  props.anomalies          liste plate déjà filtrée par parent
 * @param {Array}  props.allAnomalies       total non filtré (pour empty state context)
 * @param {Object} props.kpis               { total, critiques, risque } agrégats
 * @param {Object} props.filters            { fw, sev, site, q } state courant
 * @param {(patch)=>void} props.setFilters
 * @param {()=>void} props.resetFilters
 * @param {boolean} props.hasFilters
 * @param {Array} props.scopedSites
 * @param {Object} [props.anomalyStatuses]  map id → status
 * @param {(raw:Object)=>void} props.onRowClick  triggers EvidenceDrawer legacy
 * @param {Array} [props.selectionActions]  actions masse (contester N)
 * @param {string} [props.scopeLabel]
 */
export default function AnomaliesSol({
  anomalies = [],
  allAnomalies = [],
  kpis = { total: 0, critiques: 0, risque: 0 },
  filters = {},
  setFilters,
  resetFilters,
  hasFilters = false,
  scopedSites = [],
  anomalyStatuses = {},
  onRowClick,
  selectionActions,
  scopeLabel,
}) {
  const [sortBy, setSortBy] = useState({ column: 'impact_eur', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const rowsAll = useMemo(
    () => adaptAnomaliesToRows(anomalies, anomalyStatuses),
    [anomalies, anomalyStatuses]
  );
  const sorted = useMemo(() => sortAnomaliesRows(rowsAll, sortBy), [rowsAll, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const kicker = buildAnomaliesKicker({
    scopeLabel: scopeLabel || 'Patrimoine',
    activeCount: kpis.total,
  });
  const narrative = buildAnomaliesNarrative({
    anomalies,
    summary: kpis,
  });
  const subNarrative = buildAnomaliesSubNarrative({ anomalies });

  const emptyState = buildEmptyState({
    hasFilters,
    hasAnyAnomaly: allAnomalies.length > 0 || anomalies.length > 0,
  });

  const filterConfig = useMemo(
    () => buildFilterConfig({ scopedSites }),
    [scopedSites]
  );

  const activeFilterCount =
    (filters.fw ? 1 : 0) +
    (filters.sev ? 1 : 0) +
    (filters.site ? 1 : 0) +
    (filters.q ? 1 : 0);

  const handleSort = (columnId) => {
    setSortBy((prev) => {
      if (prev.column === columnId) {
        return { column: columnId, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { column: columnId, direction: 'desc' };
    });
  };

  const handleFilterChange = (id, value) => {
    setFilters?.({ [id]: value });
    setPage(1);
  };

  const columns = [
    { id: 'site', label: 'Site', sortable: true, width: 160, align: 'left' },
    {
      id: 'framework',
      label: 'Cadre',
      sortable: true,
      width: 140,
      render: (v) => (
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--sol-ink-700)',
          }}
        >
          {v}
        </span>
      ),
    },
    {
      id: 'severity',
      label: 'Sévérité',
      sortable: true,
      width: 110,
      render: (v, row) => {
        const rawSev = Object.keys(SEVERITY_LABELS).find((k) => SEVERITY_LABELS[k] === v);
        const kind = toneFromSeverity(rawSev || row?.cells?._raw?.severity);
        const label = v || '—';
        const mapKind = {
          refuse: 'risk',
          attention: 'att',
          afaire: 'att',
          calme: 'ok',
          succes: 'ok',
        };
        return <SolStatusPill kind={mapKind[kind] || 'att'}>{label}</SolStatusPill>;
      },
    },
    { id: 'title', label: 'Anomalie', align: 'left' },
    {
      id: 'impact_eur',
      label: 'Impact',
      sortable: true,
      align: 'right',
      width: 110,
      render: (v) => (v > 0 ? formatFREur(Math.round(v), 0) : '—'),
    },
    {
      id: 'status',
      label: 'Statut',
      width: 110,
      render: (v) => {
        const map = {
          linked: { kind: 'att', label: 'Liée' },
          dismissed: { kind: 'ok', label: 'Ignorée' },
          open: { kind: 'att', label: 'À traiter' },
        };
        const e = map[v] || { kind: 'att', label: v || 'À traiter' };
        return <SolStatusPill kind={e.kind}>{e.label}</SolStatusPill>;
      },
    },
  ];

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        fw: filters.fw || '',
        sev: filters.sev || '',
        site: filters.site || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder="Rechercher une anomalie ou un site…"
      searchValue={filters.q || ''}
      onSearchChange={(v) => handleFilterChange('q', v)}
      selection={
        selectedIds.size > 0
          ? { count: selectedIds.size, total: rowsAll.length }
          : null
      }
      selectionActions={
        selectedIds.size > 0 && selectionActions
          ? selectionActions.map((a) => ({
              ...a,
              onClick: () => a.onClick?.(Array.from(selectedIds)),
            }))
          : []
      }
      activeFilterCount={activeFilterCount}
    />
  );

  const grid = (
    <SolExpertGridFull
      columns={columns}
      rows={pageRows}
      sortBy={sortBy}
      onSort={handleSort}
      selectable
      selectedIds={selectedIds}
      onSelectionChange={setSelectedIds}
      onRowClick={(row) => onRowClick?.(row.cells?._raw || row)}
      emptyState={emptyState}
      highlightColumn="impact_eur"
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Anomalies actives"
        value={kpis.total > 0 ? String(kpis.total) : '—'}
        unit={kpis.total > 1 ? 'détectées' : 'détectée'}
        semantic="cost"
        explainKey="anomaly_active_count"
        headline={interpretActiveCount({ anomalies })}
        source={{ kind: 'calcul', origin: 'patrimoine + shadow billing' }}
      />
      <SolKpiCard
        label="Risque cumulé"
        value={kpis.risque > 0 ? formatFREur(Math.round(kpis.risque), 0) : '—'}
        unit=""
        semantic="cost"
        explainKey="anomaly_total_impact_eur"
        headline={interpretTotalImpact({ summary: kpis })}
        source={{ kind: 'calcul', origin: 'prix pondéré + DJU' }}
      />
      <SolKpiCard
        label="Critiques"
        value={kpis.critiques > 0 ? String(kpis.critiques) : '—'}
        unit={kpis.critiques > 1 ? 'à traiter' : 'à traiter'}
        semantic="score"
        explainKey="anomaly_critical_count"
        headline={
          kpis.critiques > 0
            ? 'Priorité haute — impact réglementaire ou financier immédiat.'
            : 'Aucune anomalie critique active — vigilance maintenue.'
        }
        source={{ kind: 'calcul', origin: 'severity CRITICAL' }}
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

  const resetButton = hasFilters ? (
    <button
      type="button"
      onClick={() => {
        resetFilters?.();
        setPage(1);
      }}
      className="sol-btn sol-btn--ghost"
      style={{ fontSize: 11 }}
    >
      Réinitialiser filtres
    </button>
  ) : null;

  return (
    <SolListPage
      kicker={kicker}
      title="Anomalies"
      titleEm={`· ${NBSP}${allAnomalies.length || kpis.total || 0}${NBSP}sur votre patrimoine`}
      narrative={narrative}
      subNarrative={subNarrative}
      rightSlot={resetButton}
      kpiRow={kpiRow}
      toolbar={toolbar}
      grid={grid}
      pagination={pagination}
    />
  );
}
