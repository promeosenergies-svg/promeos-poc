/**
 * PROMEOS — ConsumptionPortfolioPage (V2)
 * Vue pilotage multi-sites B2B — patrimoine-first.
 *
 * V2: tous les sites du patrimoine affiches (meme sans donnees),
 *     data_status badge, coverage_pct par site, filtre "Sans donnees",
 *     deep-links avec date_from/date_to, CTA "Importer" inline.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Zap,
  Euro,
  Leaf,
  ShieldCheck,
  AlertTriangle,
  Moon,
  Activity,
  Search,
  FileText,
  Plus,
  BarChart3,
  TrendingDown,
  CheckSquare,
  DollarSign,
  Info,
  RotateCcw,
  Upload,
  HelpCircle,
  Eye,
} from 'lucide-react';
import { Card, CardBody, SkeletonCard, KpiCard, EmptyState } from '../ui';
import { useToast } from '../ui';
import InfoTip from '../ui/InfoTip';
import { useScope } from '../contexts/ScopeContext';
import { getPortfolioSummary, getPortfolioSites } from '../services/api';
import {
  toConsoExplorer,
  toConsoDiag,
  toBillIntel,
  toActionNew,
  toActionsList,
  toConsoImport,
} from '../services/routes';
import { fmtEur, fmtKwh, fmtCo2, fmtKw } from '../utils/format';

// ─── Helpers ──────────────────────────────────────────────────────────────
function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 90);
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  };
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Data status badge: ok (green), partial (amber), none (gray) */
function DataStatusBadge({ status, coveragePct }) {
  if (status === 'ok') {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700"
        title={`Couverture ${coveragePct}% — Données complètes`}
      >
        {coveragePct}%
      </span>
    );
  }
  if (status === 'partial') {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700"
        title={`Couverture ${coveragePct}% — Donnees partielles`}
      >
        {coveragePct}%
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-400"
      title="Aucune donnée sur cette période"
    >
      —
    </span>
  );
}

// ─── Top-list row actions (shared by all 4 lists) ─────────────────────────
function TopListActions({ siteId, dates, navigate }) {
  return (
    <span className="inline-flex items-center gap-0.5 ml-2 shrink-0">
      <button
        onClick={(e) => {
          e.stopPropagation();
          navigate(toConsoExplorer({ site_id: siteId, date_from: dates.from, date_to: dates.to }));
        }}
        className="p-0.5 rounded hover:bg-blue-50 text-blue-500"
        title="Explorer ce site"
      >
        <BarChart3 size={11} />
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          navigate(toConsoDiag({ site_id: siteId }));
        }}
        className="p-0.5 rounded hover:bg-amber-50 text-amber-500"
        title="Diagnostic"
      >
        <TrendingDown size={11} />
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          navigate(toBillIntel({ site_id: siteId }));
        }}
        className="p-0.5 rounded hover:bg-gray-100 text-gray-400"
        title="Voir factures"
      >
        <FileText size={11} />
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          navigate(
            toActionNew({
              source_type: 'consommation',
              site_id: siteId,
              source: 'portfolio_toplist',
            })
          );
        }}
        className="p-0.5 rounded hover:bg-green-50 text-green-500"
        title="Créer une action"
      >
        <Plus size={11} />
      </button>
    </span>
  );
}

// ─── Component ─────────────────────────────────────────────────────────────
export default function ConsumptionPortfolioPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const { selectedSiteId, resetScope, scopeLabel, portefeuille } = useScope();
  const [searchParams] = useSearchParams();
  const dates = useMemo(() => {
    const f = searchParams.get('from');
    const t = searchParams.get('to');
    if (f && t) return { from: f, to: t };
    return defaultDateRange();
  }, [searchParams]);

  // Summary KPIs
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  // Sites table
  const [sites, setSites] = useState([]);
  const [sitesTotal, setSitesTotal] = useState(0);
  const [sitesLoading, setSitesLoading] = useState(true);
  const [sort, setSort] = useState('impact_desc');
  const [search, setSearch] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState(null);
  const [anomalyFilter, setAnomalyFilter] = useState(false);
  const [actionsFilter, setActionsFilter] = useState(null);
  const [noDataFilter, setNoDataFilter] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 25;
  const sitesTableRef = useRef(null);

  function scrollToTable() {
    sitesTableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const _hasActiveFilters =
    !!search || !!confidenceFilter || anomalyFilter || !!actionsFilter || noDataFilter;

  function handleResetFilters() {
    setSearch('');
    setConfidenceFilter(null);
    setAnomalyFilter(false);
    setActionsFilter(null);
    setNoDataFilter(false);
    setSort('impact_desc');
    setPage(0);
  }

  // ─── Fetch summary ────────────────────────────────────────────────────
  useEffect(() => {
    setSummaryLoading(true);
    getPortfolioSummary({ from: dates.from, to: dates.to, portefeuille_id: portefeuille?.id })
      .then(setSummary)
      .catch(() => addToast({ type: 'error', message: 'Erreur chargement resume portfolio' }))
      .finally(() => setSummaryLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates.from, dates.to, portefeuille?.id]);

  // ─── Fetch sites table ────────────────────────────────────────────────
  const fetchSites = useCallback(() => {
    setSitesLoading(true);
    getPortfolioSites({
      from: dates.from,
      to: dates.to,
      portefeuille_id: portefeuille?.id,
      sort,
      confidence: confidenceFilter || undefined,
      with_anomalies: anomalyFilter || undefined,
      with_actions: actionsFilter || undefined,
      without_data: noDataFilter || undefined,
      search: search || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((data) => {
        setSites(data.rows || []);
        setSitesTotal(data.total || 0);
      })
      .catch(() => addToast({ type: 'error', message: 'Erreur chargement sites portfolio' }))
      .finally(() => setSitesLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    dates.from,
    dates.to,
    portefeuille?.id,
    sort,
    confidenceFilter,
    anomalyFilter,
    actionsFilter,
    noDataFilter,
    search,
    page,
  ]);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);
  useEffect(() => {
    setPage(0);
  }, [sort, search, confidenceFilter, anomalyFilter, actionsFilter, noDataFilter]);

  // ─── Computed ─────────────────────────────────────────────────────────
  const totalPages = Math.ceil(sitesTotal / PAGE_SIZE);
  const cov = summary?.coverage;
  const tot = summary?.totals;

  const confLevel = useMemo(() => {
    if (!cov) return null;
    const { high = 0, medium = 0, low = 0 } = cov.confidence_split || {};
    const total = high + medium + low;
    if (total === 0) return 'low';
    if (high / total >= 0.7) return 'high';
    if ((high + medium) / total >= 0.5) return 'medium';
    return 'low';
  }, [cov]);

  const coveragePct = useMemo(() => {
    if (!cov || !cov.sites_total) return 0;
    return Math.round((cov.sites_with_data / cov.sites_total) * 100);
  }, [cov]);

  const top5ForAction = useMemo(() => {
    if (!summary?.top_impact?.length && !summary?.top_drift?.length) return [];
    const pool = summary.top_impact?.length ? summary.top_impact : summary.top_drift || [];
    return pool.slice(0, 5);
  }, [summary]);

  // ─── Grouped action handler ──────────────────────────────────────────
  function handleGroupedAction() {
    if (top5ForAction.length === 0) return;
    const siteIds = top5ForAction.map((r) => r.site_id);
    navigate(
      toActionNew({
        source_type: 'consommation',
        source: 'portfolio_campagne',
        title: `Campagne portfolio — ${siteIds.length} sites prioritaires`,
        site_id: siteIds[0],
        site_ids: siteIds,
      })
    );
  }

  // ─── Row click → Explorer (with date context) ─────────────────────────
  function handleRowClick(row) {
    if (row.data_status === 'none') {
      navigate(toConsoImport());
      return;
    }
    navigate(toConsoExplorer({ site_id: row.site_id, date_from: dates.from, date_to: dates.to }));
  }

  // ─── Render ───────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ═══ SCOPE BANNER ═══ */}
      {selectedSiteId && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <Info size={16} className="text-blue-500 shrink-0" />
          <p className="text-sm text-blue-700 flex-1">
            <strong>Portefeuille = vue multi-sites.</strong> Le bandeau indique « {scopeLabel} »,
            mais cette page affiche tous vos sites. Pour explorer un site seul, cliquez sur sa
            ligne.
          </p>
          <button
            onClick={() => resetScope()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-white border border-blue-300 rounded-lg hover:bg-blue-100 transition shrink-0"
          >
            Passer a Tous les sites
          </button>
        </div>
      )}

      {/* ═══ PILOTAGE HEADER ═══ */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Portefeuille Consommation</h2>
          <p className="text-sm text-gray-500">
            Vous pilotez {cov?.sites_total ?? '—'} sites sur la période du {fmtDate(dates.from)} au{' '}
            {fmtDate(dates.to)}
            {cov?.sites_without_data > 0 && (
              <span className="text-amber-600"> — {cov.sites_without_data} sans données</span>
            )}
          </p>
        </div>
        {cov && (
          <div
            className="flex items-center gap-1.5 shrink-0"
            title="La couverture indique le % de sites avec des relevés sur la période. Plus elle est élevée, plus les KPIs sont fiables."
          >
            <span
              className={`text-sm font-semibold ${coveragePct >= 80 ? 'text-green-600' : coveragePct >= 50 ? 'text-amber-600' : 'text-red-600'}`}
            >
              Couverture {coveragePct}%
            </span>
            <HelpCircle size={13} className="text-gray-400 cursor-help" />
          </div>
        )}
      </div>

      {/* ═══ KPI CARDS ═══ */}
      {summaryLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard
            icon={Zap}
            label={
              <>
                kWh total{' '}
                <InfoTip content="Somme des kWh électricité relevés sur tous les sites pour la période sélectionnée." />
              </>
            }
            value={fmtKwh(tot?.kwh_total)}
          />
          <KpiCard
            icon={Euro}
            label={
              <>
                Coût estimé{' '}
                <InfoTip content="Estimation basée sur le prix de référence de chaque site (contrat > profil tarifaire > défaut 0,18 EUR/kWh)." />
              </>
            }
            value={fmtEur(tot?.eur_total)}
            sub={
              tot?.eur_source === 'estime'
                ? 'Estimation à 0,18 EUR/kWh'
                : 'Prix mixtes (contrats + défaut)'
            }
          />
          <KpiCard
            icon={Leaf}
            label={
              <>
                Émissions CO₂{' '}
                <InfoTip content="Facteur d'émission ADEME 2024 : 0,052 kgCO₂e/kWh pour l'électricité en France." />
              </>
            }
            value={fmtCo2(tot?.co2_total)}
            sub="Facteur ADEME 2024"
          />
          <KpiCard
            icon={ShieldCheck}
            label={
              <>
                Couverture donnees{' '}
                <InfoTip content="Nombre de sites avec au moins un relevé sur la période. Confiance = densité de données vs attendu." />
              </>
            }
            value={`${cov?.sites_with_data || 0} / ${cov?.sites_total || 0} sites`}
            sub={
              confLevel ? (
                <>
                  {`Confiance ${confLevel === 'high' ? 'haute' : confLevel === 'medium' ? 'moyenne' : 'basse'}`}{' '}
                  <InfoTip
                    content="Haute = ≥ 80% des relevés attendus. Moyenne = 30-80%. Basse = < 30%."
                    size={10}
                  />
                </>
              ) : undefined
            }
          />
        </div>
      ) : null}

      {/* ═══ OU AGIR MAINTENANT ═══ */}
      {summary && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Ou agir en priorite</h2>
            {top5ForAction.length > 0 && (
              <button
                onClick={handleGroupedAction}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
              >
                <CheckSquare size={14} />
                Lancer campagne ({top5ForAction.length} sites)
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Top impact EUR */}
            <Card
              className="cursor-pointer hover:ring-2 hover:ring-blue-200 transition"
              onClick={() => {
                setSort('impact_desc');
                scrollToTable();
              }}
            >
              <CardBody>
                <div className="flex items-center gap-2 mb-3">
                  <DollarSign size={16} className="text-rose-500" />
                  <h3 className="text-sm font-semibold text-gray-700">Impact financier estimé</h3>
                </div>
                {summary.top_impact?.length > 0 ? (
                  <ul className="space-y-2">
                    {summary.top_impact.map((r) => (
                      <li key={r.site_id} className="flex items-center text-xs">
                        <span className="text-gray-700 truncate flex-1">{r.site_name}</span>
                        <span className="text-rose-600 font-medium ml-2 shrink-0">
                          {fmtEur(r.impact_eur_estimated)}
                        </span>
                        <TopListActions siteId={r.site_id} dates={dates} navigate={navigate} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400">Aucun impact détecté</p>
                )}
              </CardBody>
            </Card>

            {/* Top derive */}
            <Card
              className="cursor-pointer hover:ring-2 hover:ring-blue-200 transition"
              onClick={() => {
                setAnomalyFilter(true);
                setSort('diagnostics');
                scrollToTable();
              }}
            >
              <CardBody>
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle size={16} className="text-amber-500" />
                  <h3 className="text-sm font-semibold text-gray-700">Dérives détectées</h3>
                </div>
                {summary.top_drift?.length > 0 ? (
                  <ul className="space-y-2">
                    {summary.top_drift.map((r) => (
                      <li key={r.site_id} className="flex items-center text-xs">
                        <span className="text-gray-700 truncate flex-1">{r.site_name}</span>
                        <span className="text-amber-600 font-medium ml-2 shrink-0">
                          {r.diagnostics_count} alertes
                        </span>
                        <TopListActions siteId={r.site_id} dates={dates} navigate={navigate} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400">Aucune dérive détectée</p>
                )}
              </CardBody>
            </Card>

            {/* Top base nocturne */}
            <Card
              className="cursor-pointer hover:ring-2 hover:ring-blue-200 transition"
              onClick={() => {
                setSort('base_night');
                scrollToTable();
              }}
            >
              <CardBody>
                <div className="flex items-center gap-2 mb-3">
                  <Moon size={16} className="text-indigo-500" />
                  <h3 className="text-sm font-semibold text-gray-700">Consommation nocturne</h3>
                </div>
                {summary.top_base_night?.length > 0 ? (
                  <ul className="space-y-2">
                    {summary.top_base_night.map((r) => (
                      <li key={r.site_id} className="flex items-center text-xs">
                        <span className="text-gray-700 truncate flex-1">{r.site_name}</span>
                        <span className="text-indigo-600 font-medium ml-2 shrink-0">
                          {r.base_night_pct}%
                        </span>
                        <TopListActions siteId={r.site_id} dates={dates} navigate={navigate} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400">Pas de données</p>
                )}
              </CardBody>
            </Card>

            {/* Top pics */}
            <Card
              className="cursor-pointer hover:ring-2 hover:ring-blue-200 transition"
              onClick={() => {
                setSort('peak');
                scrollToTable();
              }}
            >
              <CardBody>
                <div className="flex items-center gap-2 mb-3">
                  <Activity size={16} className="text-red-500" />
                  <h3 className="text-sm font-semibold text-gray-700">Pics de puissance</h3>
                </div>
                {summary.top_peaks?.length > 0 ? (
                  <ul className="space-y-2">
                    {summary.top_peaks.map((r) => (
                      <li key={r.site_id} className="flex items-center text-xs">
                        <span className="text-gray-700 truncate flex-1">{r.site_name}</span>
                        <span className="text-red-600 font-medium ml-2 shrink-0">
                          {r.peak_kw} kW
                        </span>
                        <TopListActions siteId={r.site_id} dates={dates} navigate={navigate} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-400">Pas de données</p>
                )}
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {/* ═══ SITES TABLE ═══ */}
      <div ref={sitesTableRef}>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Tous les sites</h2>

        {/* Filters bar */}
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Rechercher un site..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-sm border rounded-lg bg-white focus:ring-1 focus:ring-blue-300 focus:border-blue-400 outline-none w-56"
            />
          </div>

          {['high', 'medium', 'low'].map((c) => (
            <button
              key={c}
              onClick={() => setConfidenceFilter(confidenceFilter === c ? null : c)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                confidenceFilter === c
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {c === 'high' ? 'Haute' : c === 'medium' ? 'Moyenne' : 'Basse'}
            </button>
          ))}

          <button
            onClick={() => setAnomalyFilter(!anomalyFilter)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              anomalyFilter
                ? 'bg-amber-100 text-amber-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Anomalies
          </button>

          <button
            onClick={() => setActionsFilter(actionsFilter === 'with' ? null : 'with')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              actionsFilter === 'with'
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Avec actions
          </button>
          <button
            onClick={() => setActionsFilter(actionsFilter === 'without' ? null : 'without')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              actionsFilter === 'without'
                ? 'bg-gray-200 text-gray-800'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Sans action
          </button>

          <button
            onClick={() => setNoDataFilter(!noDataFilter)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              noDataFilter
                ? 'bg-red-100 text-red-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Sans données
          </button>

          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="text-xs border rounded-lg px-2 py-1.5 bg-white"
          >
            <option value="impact_desc">Impact EUR décroissant</option>
            <option value="kwh_desc">kWh décroissant</option>
            <option value="kwh_asc">kWh croissant</option>
            <option value="name">Nom A-Z</option>
            <option value="peak">P95 kW</option>
            <option value="base_night">Base nocturne</option>
            <option value="diagnostics">Diagnostics</option>
            <option value="coverage">Couverture donnees</option>
          </select>
        </div>

        {/* Table */}
        {sitesLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : sites.length === 0 ? (
          /* Empty state: Cas A (aucune donnee) vs Cas B (filtres trop restrictifs) */
          (cov?.sites_total || 0) === 0 ? (
            /* Cas A: aucune donnee du tout */
            <EmptyState
              icon={BarChart3}
              title="Aucune donnée de consommation"
              text="Aucune donnée disponible sur la période sélectionnée. Importez vos relevés ou changez la période pour voir vos sites."
              ctaLabel="Importer des données"
              onCta={() => navigate(toConsoImport())}
            />
          ) : (
            /* Cas B: filtres trop restrictifs */
            <EmptyState
              icon={Search}
              title="Aucun site ne correspond aux filtres"
              text={`${cov.sites_total} sites existent mais sont masqués par vos critères.`}
              actions={
                <div className="space-y-4">
                  {/* Active filter chips */}
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    {search && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-gray-100 text-gray-600">
                        Recherche : « {search} »
                      </span>
                    )}
                    {confidenceFilter && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-blue-100 text-blue-600">
                        Confiance :{' '}
                        {confidenceFilter === 'high'
                          ? 'Haute'
                          : confidenceFilter === 'medium'
                            ? 'Moyenne'
                            : 'Basse'}
                      </span>
                    )}
                    {anomalyFilter && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-amber-100 text-amber-600">
                        Anomalies uniquement
                      </span>
                    )}
                    {actionsFilter && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-green-100 text-green-600">
                        {actionsFilter === 'with' ? 'Avec actions' : 'Sans action'}
                      </span>
                    )}
                    {noDataFilter && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-red-100 text-red-600">
                        Sans données
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleResetFilters}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                    >
                      <RotateCcw size={14} />
                      Réinitialiser les filtres
                    </button>
                    <button
                      onClick={() => navigate(toConsoImport())}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                    >
                      <Upload size={14} />
                      Importer des données
                    </button>
                  </div>
                </div>
              }
            />
          )
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left">
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500">Site</th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-center">
                      Couverture{' '}
                      <InfoTip
                        content="% de relevés reçus vs attendus selon la fréquence du compteur."
                        size={10}
                      />
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right">
                      Impact EUR
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right">
                      kWh
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right">
                      EUR
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right">
                      P95 kW{' '}
                      <InfoTip
                        content="95e percentile des relevés kWh (proxy puissance). Utile pour détecter les dépassements de puissance souscrite."
                        size={10}
                      />
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right">
                      Base nuit{' '}
                      <InfoTip
                        content="Part de la conso nocturne (22h-6h) dans la conso totale. Théorique si plat = 33%. Un % élevé signale un talon (chauffage, serveurs)."
                        size={10}
                      />
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-center">
                      Diag.
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-center">
                      Actions
                    </th>
                    <th className="py-2 px-3 text-xs font-semibold text-gray-500 text-right"></th>
                  </tr>
                </thead>
                <tbody>
                  {sites.map((row) => (
                    <tr
                      key={row.site_id}
                      className={`border-b border-gray-100 hover:bg-gray-50 transition cursor-pointer ${row.data_status === 'none' ? 'bg-gray-50/50' : ''}`}
                      onClick={() => handleRowClick(row)}
                      title={
                        row.data_status === 'none'
                          ? 'Aucune donnée — cliquez pour importer'
                          : 'Cliquez pour explorer ce site'
                      }
                    >
                      <td className="py-2 px-3">
                        <span className="font-medium text-gray-800">{row.site_name}</span>
                        {row.last_reading_date && (
                          <span className="block text-[10px] text-gray-400">
                            Dernier releve : {fmtDate(row.last_reading_date)}
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <DataStatusBadge status={row.data_status} coveragePct={row.coverage_pct} />
                      </td>
                      <td className="py-2 px-3 text-right">
                        {row.impact_eur_estimated > 0 ? (
                          <span className="text-rose-600 font-medium">
                            {fmtEur(row.impact_eur_estimated)}
                          </span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-700">
                        {row.data_status !== 'none' ? fmtKwh(row.kwh) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-700">
                        {row.data_status !== 'none' ? fmtEur(row.eur) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-700">
                        {row.peak_kw != null ? fmtKw(row.peak_kw) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-700">
                        {row.base_night_pct != null ? `${row.base_night_pct}%` : '—'}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {row.diagnostics_count > 0 ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(toConsoDiag({ site_id: row.site_id }));
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-700 hover:bg-amber-200 transition"
                            title="Voir les diagnostics"
                          >
                            {row.diagnostics_count}
                          </button>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {row.open_actions_count > 0 ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(toActionsList({ site_id: row.site_id }));
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 text-green-700 hover:bg-green-200 transition"
                            title="Voir les actions en cours"
                          >
                            <Eye size={10} />
                            {row.open_actions_count}
                          </button>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(
                                toActionNew({
                                  source_type: 'consommation',
                                  site_id: row.site_id,
                                  source: 'portfolio',
                                })
                              );
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-500 hover:bg-gray-200 transition"
                            title="Créer une action"
                          >
                            <Plus size={10} />
                          </button>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {row.data_status !== 'none' ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(
                                  toConsoExplorer({
                                    site_id: row.site_id,
                                    date_from: dates.from,
                                    date_to: dates.to,
                                  })
                                );
                              }}
                              className="p-1 rounded hover:bg-blue-50 text-blue-500"
                              title="Explorer"
                            >
                              <BarChart3 size={14} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(toConsoDiag({ site_id: row.site_id }));
                              }}
                              className="p-1 rounded hover:bg-amber-50 text-amber-500"
                              title="Diagnostic"
                            >
                              <TrendingDown size={14} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(toBillIntel({ site_id: row.site_id }));
                              }}
                              className="p-1 rounded hover:bg-gray-100 text-gray-500"
                              title="Voir factures"
                            >
                              <FileText size={14} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(
                                  toActionNew({
                                    source_type: 'consommation',
                                    site_id: row.site_id,
                                    source: 'portfolio',
                                  })
                                );
                              }}
                              className="p-1 rounded hover:bg-green-50 text-green-500"
                              title="Créer une action"
                            >
                              <Plus size={14} />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(toConsoImport());
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition"
                            title="Importer des donnees pour ce site"
                          >
                            <Upload size={10} />
                            Importer
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-xs text-gray-400">{sitesTotal} sites</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="px-3 py-1 text-xs rounded border bg-white disabled:opacity-40"
                  >
                    Précédent
                  </button>
                  <span className="text-xs text-gray-500">
                    {page + 1} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-3 py-1 text-xs rounded border bg-white disabled:opacity-40"
                  >
                    Suivant
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
