/**
 * PROMEOS — ContratsSol (Lot 2 Phase 3, Pattern B pur)
 *
 * Rendu Sol de /contrats. Le parent Contrats.jsx garde la logique
 * data (listCadres + getCadreKpis, panels state cadre/annexe, wizard
 * state, escape key handler). ContratsSol se concentre sur Pattern B.
 *
 * Les 3 panels legacy (ContractCadrePanel, ContractAnnexePanel,
 * ContractWizard) restent rendus par le parent — ContratsSol
 * déclenche juste les setters via props (onOpenCadre, onOpenAnnexe,
 * onOpenWizard).
 */
import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SolListPage,
  SolKpiRow,
  SolKpiCard,
  SolExpertToolbar,
  SolExpertGridFull,
  SolPagination,
  SolStatusPill,
  SolButton,
} from '../ui/sol';
import {
  buildContractsKicker,
  buildContractsNarrative,
  buildContractsSubNarrative,
  buildContractRows,
  computePortfolioKpis,
  interpretActiveContracts,
  interpretTotalVolume,
  interpretWeightedPrice,
  buildEmptyState,
  buildFilterConfig,
  filterRows,
  sortRows,
  paginateRows,
  STATUS_LABELS,
  toneFromStatus,
  formatDateFR,
  daysUntil,
  formatFR,
  NBSP,
} from './contrats/sol_presenters';

/**
 * @param {Object} props
 * @param {Array} props.cadres            listCadres() result
 * @param {boolean} [props.loading]
 * @param {number} [props.nbSites]
 * @param {string} [props.scopeLabel]
 * @param {(cadreId)=>void} props.onOpenCadre
 * @param {(annexeId, cadreId)=>void} props.onOpenAnnexe
 * @param {()=>void} props.onOpenWizard
 */
export default function ContratsSol({
  cadres = [],
  loading = false,
  nbSites,
  scopeLabel,
  onOpenCadre,
  onOpenAnnexe,
  onOpenWizard,
}) {
  const [sortBy, setSortBy] = useState({ column: 'end_date', direction: 'asc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({ search: '', supplier: '', chip: '', status: '' });

  const kpis = useMemo(() => computePortfolioKpis(cadres), [cadres]);
  const rowsAll = useMemo(() => buildContractRows(cadres), [cadres]);
  const filtered = useMemo(() => filterRows(rowsAll, filters), [rowsAll, filters]);
  const sorted = useMemo(() => sortRows(filtered, sortBy), [filtered, sortBy]);
  const pageRows = useMemo(() => paginateRows(sorted, page, pageSize), [sorted, page, pageSize]);

  const kicker = buildContractsKicker({ scopeLabel, activeCount: kpis.activeCount });
  const narrative = buildContractsNarrative({ cadres, kpis });
  const subNarrative = buildContractsSubNarrative({ cadres, kpis });

  const navigate = useNavigate();
  const hasFilters = Boolean(filters.search || filters.supplier || filters.chip || filters.status);
  const rawEmpty = buildEmptyState({
    hasFilters,
    hasAnyContract: rowsAll.length > 0,
  });
  const emptyState = useMemo(() => {
    if (!rawEmpty?.ctaLabel || !rawEmpty?.ctaHref) return rawEmpty;
    return {
      title: rawEmpty.title,
      message: rawEmpty.message,
      action: { label: rawEmpty.ctaLabel, onClick: () => navigate(rawEmpty.ctaHref) },
    };
  }, [rawEmpty, navigate]);
  const filterConfig = useMemo(() => buildFilterConfig({ cadres }), [cadres]);

  const activeFilterCount =
    (filters.search ? 1 : 0) +
    (filters.supplier ? 1 : 0) +
    (filters.chip ? 1 : 0) +
    (filters.status ? 1 : 0);

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

  const handleRowClick = (row) => {
    const cells = row.cells;
    if (cells._type === 'cadre') {
      onOpenCadre?.(cells._raw.id);
    } else if (cells._type === 'annexe') {
      onOpenAnnexe?.(cells._raw.id, cells._cadreId);
    }
  };

  const resetFilters = () => {
    setFilters({ search: '', supplier: '', chip: '', status: '' });
    setPage(1);
  };

  const columns = [
    { id: 'site', label: 'Site / Annexe', sortable: true, width: 220, align: 'left' },
    { id: 'supplier', label: 'Fournisseur', sortable: true, width: 140, align: 'left' },
    {
      id: 'energy',
      label: 'Énergie',
      width: 70,
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
          {v || '—'}
        </span>
      ),
    },
    {
      id: 'pricing',
      label: 'Modèle prix',
      sortable: true,
      width: 140,
      render: (v) => v || '—',
    },
    {
      id: 'end_date',
      label: 'Fin',
      sortable: true,
      width: 130,
      render: (v) => {
        const days = daysUntil(v);
        const formatted = formatDateFR(v);
        if (days != null && days > 0 && days <= 90) {
          return (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span>{formatted}</span>
              <span
                style={{
                  fontSize: 9,
                  padding: '1px 5px',
                  borderRadius: 2,
                  background: 'var(--sol-attention-bg)',
                  color: 'var(--sol-attention-fg)',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                }}
              >
                {days}
                {NBSP}j
              </span>
            </span>
          );
        }
        return formatted;
      },
    },
    {
      id: 'volume_mwh',
      label: 'Volume',
      sortable: true,
      align: 'right',
      width: 100,
      render: (v) => (v > 0 ? `${formatFR(Math.round(v), 0)}${NBSP}MWh` : '—'),
    },
    {
      id: 'price_eur_mwh',
      label: '€/MWh',
      sortable: true,
      align: 'right',
      width: 100,
      render: (v) =>
        v != null && v > 0 ? (
          `${formatFR(v, 1)}${NBSP}€`
        ) : (
          <span
            title="Prix non renseigné (indexé ou à compléter)"
            style={{ color: 'var(--sol-ink-400)', fontStyle: 'italic' }}
          >
            indexé
          </span>
        ),
    },
    {
      id: 'status',
      label: 'Statut',
      sortable: true,
      width: 130,
      render: (v) => {
        const label = STATUS_LABELS[v] || v || '—';
        const tone = toneFromStatus(v);
        const kindMap = {
          calme: 'ok',
          attention: 'att',
          afaire: 'att',
          refuse: 'risk',
          succes: 'ok',
        };
        return <SolStatusPill kind={kindMap[tone] || 'att'}>{label}</SolStatusPill>;
      },
    },
  ];

  const toolbar = (
    <SolExpertToolbar
      filters={filterConfig}
      activeFilters={{
        supplier: filters.supplier || '',
        chip: filters.chip || '',
        status: filters.status || '',
      }}
      onFilterChange={handleFilterChange}
      searchPlaceholder="Fournisseur, site, référence…"
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
      highlightColumn="end_date"
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Contrats actifs"
        value={kpis.activeCount > 0 ? String(kpis.activeCount) : '—'}
        unit={kpis.activeCount > 1 ? 'contrats' : 'contrat'}
        semantic="score"
        explainKey="contract_active_count"
        headline={interpretActiveContracts({ kpis })}
        source={{ kind: 'calcul', origin: 'référentiel contrats' }}
      />
      <SolKpiCard
        label="Volume cumulé 12 mois"
        value={kpis.totalVolumeMwh > 0 ? formatFR(kpis.totalVolumeMwh, 0) : '—'}
        unit="MWh"
        semantic="neutral"
        explainKey="contract_total_volume_mwh"
        headline={interpretTotalVolume({ kpis, nbSites })}
        source={{ kind: 'calcul', origin: 'somme annexes + cadres' }}
      />
      <SolKpiCard
        label="Prix pondéré"
        value={kpis.weightedPriceEurMwh != null ? formatFR(kpis.weightedPriceEurMwh, 1) : '—'}
        unit="€/MWh"
        semantic="cost"
        explainKey="contract_weighted_price_eur_mwh"
        headline={interpretWeightedPrice({ kpis })}
        source={{ kind: 'calcul', origin: '(Σ prix × volume) / Σ volume' }}
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
      <SolButton variant="secondary" onClick={onOpenWizard}>
        Importer
      </SolButton>
      <SolButton variant="primary" onClick={onOpenWizard}>
        Nouveau contrat
      </SolButton>
    </div>
  );

  const totalContracts = kpis.totalContracts;

  return (
    <SolListPage
      breadcrumb={{
        segments: [{ label: 'Patrimoine', to: '/patrimoine' }, { label: 'Contrats' }],
        backTo: '/patrimoine',
      }}
      kicker={kicker}
      title="Contrats énergie"
      titleEm={`· ${totalContracts}${NBSP}contrat${totalContracts > 1 ? 's' : ''} portefeuille`}
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
