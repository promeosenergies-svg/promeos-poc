/**
 * PROMEOS — Tableau de bord (/) Cockpit V2
 * Page quotidienne : Briefing du jour + KPI row + À traiter aujourd'hui + ModuleLaunchers.
 * Neutral-first + controlled accents. KPI accent bars, icon pills,
 * "tout sous contrôle" state, trust signals.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  ArrowRight,
  Clock,
  Upload,
  Scan,
  RefreshCw,
  CheckCircle2,
  ShieldCheck,
  TrendingDown,
  Bell,
  Database,
  FileText,
} from 'lucide-react';
import {
  Card,
  Button,
  SkeletonCard,
  PageShell,
  MetricCard,
  StatusDot,
  EmptyState,
  ErrorState,
  ScopeSummary,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { toActionsList } from '../services/routes';
import {
  getComplianceBundle,
  getActionsSummary,
  getActionsList,
  getNotificationsSummary,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { getRiskStatus } from '../lib/constants';
import { useExpertMode } from '../contexts/ExpertModeContext';
import {
  buildWatchlist,
  buildBriefing,
  buildOpportunities,
  buildTodayActions,
  computeHealthState,
} from '../models/dashboardEssentials';
import HealthSummary from '../components/HealthSummary';
import BriefingHeroCard from './cockpit/BriefingHeroCard';
import TodayActionsCard from './cockpit/TodayActionsCard';
import ModuleLaunchers from './cockpit/ModuleLaunchers';
import EssentialsRow from './cockpit/EssentialsRow';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import { useCockpitData } from '../hooks/useCockpitData';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { fmtKwh } from '../utils/format';
import SitesBaselineCard from './cockpit/SitesBaselineCard';

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

// ── KpiJ1Card — mini card J-1 pour CommandCenter (Step 5) ──
function KpiJ1Card({ label, value, sub, accent = 'neutral', loading: isLoading }) {
  const accentCls =
    {
      neutral: 'border-gray-200',
      warn: 'border-amber-300 bg-amber-50',
      ok: 'border-green-200 bg-green-50',
    }[accent] ?? 'border-gray-200';

  return (
    <div className={`bg-white border rounded-lg p-3 ${accentCls}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      {isLoading ? (
        <div className="h-6 w-20 bg-gray-100 rounded animate-pulse" />
      ) : (
        <div className="text-xl font-semibold text-gray-900">{value}</div>
      )}
      <div className="text-xs text-gray-400 mt-1 truncate">{sub}</div>
    </div>
  );
}

// ── CockpitTabs — navigation Vue exécutive / Tableau de bord ──
function CockpitTabs({ active }) {
  const nav = useNavigate();
  return (
    <div className="flex gap-6 border-b border-gray-200 mb-4">
      <button
        onClick={() => nav('/cockpit')}
        className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
          active === 'cockpit'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'
        }`}
      >
        Vue exécutive — /cockpit
      </button>
      <button
        onClick={() => nav('/')}
        className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
          active === 'dashboard'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'
        }`}
      >
        Tableau de bord — /
      </button>
    </div>
  );
}

/* ── normalizeDashboardModel: prevent contradictions ── */
export function normalizeDashboardModel({ kpis, topActions, alertsCount }) {
  const norm = { ...kpis };
  // If 100% conforme, risk must be 0
  if (norm.pctConf === 100) {
    norm.risque = 0;
    norm.nonConformes = 0;
    norm.aRisque = 0;
  }
  // If 0 risk sites, risque EUR must be 0
  if (norm.nonConformes + norm.aRisque === 0) {
    norm.risque = 0;
  }
  const isAllClear = norm.pctConf === 100 && norm.risque === 0 && alertsCount === 0;
  const actions = isAllClear ? [] : topActions;
  return { kpis: norm, topActions: actions, alertsCount, isAllClear };
}

export default function CommandCenter() {
  const navigate = useNavigate();
  const { org, scopedSites, selectedSiteId } = useScope();
  const { isExpert } = useExpertMode();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [compliance, setCompliance] = useState(null);
  const [_actionsSummary, setActionsSummary] = useState(null);
  const [actions, setActions] = useState([]);
  const [alertsSummary, setAlertsSummary] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  // ── Hooks enrichissement Step 5 ──
  const { weekSeries, hourlyProfile, kpisJ1, loading: cmdLoading } = useCommandCenterData();
  const { trajectoire } = useCockpitData();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Pass site_id when a specific site is selected in scope
      const siteParam = selectedSiteId ? { site_id: selectedSiteId } : {};
      const [compBundle, actSummary, actList, notifSummary] = await Promise.all([
        getComplianceBundle({ org_id: org.id, ...siteParam }).catch(() => null),
        getActionsSummary(org.id, selectedSiteId || undefined).catch(() => null),
        getActionsList({
          org_id: org.id,
          limit: 20,
          status: 'open,in_progress',
          ...siteParam,
        }).catch(() => []),
        getNotificationsSummary(org.id, selectedSiteId || undefined).catch(() => null),
      ]);
      setCompliance(compBundle);
      setActionsSummary(actSummary);
      setActions(Array.isArray(actList) ? actList : actList?.actions || []);
      setAlertsSummary(notifSummary);
      setLastSync(new Date());
    } catch {
      setError('Impossible de charger le tableau de bord');
    } finally {
      setLoading(false);
    }
  }, [org.id, selectedSiteId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Raw KPIs from scope
  const rawKpis = useMemo(() => {
    const total = scopedSites.length;
    const conformes = scopedSites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = scopedSites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risque = scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const pctConf = total > 0 ? Math.round((conformes / total) * 100) : 0;
    const couvertureDonnees =
      total > 0
        ? Math.round((scopedSites.filter((s) => s.conso_kwh_an > 0).length / total) * 100)
        : 0;
    const compStatus =
      nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    const risqueStatus = getRiskStatus(risque);
    return {
      total,
      conformes,
      nonConformes,
      aRisque,
      risque,
      pctConf,
      couvertureDonnees,
      compStatus,
      risqueStatus,
    };
  }, [scopedSites]);

  // Top actions — merge compliance + action plan
  const rawTopActions = useMemo(() => {
    const items = [];
    if (compliance?.sites) {
      const findings = compliance.sites
        .flatMap((s) =>
          (s.findings || [])
            .filter((f) => f.status !== 'conforme')
            .map((f) => ({
              ...f,
              site_nom: s.site_nom,
            }))
        )
        .slice(0, 5);
      for (const f of findings) {
        items.push({
          id: `comp-${f.id || f.rule_id}`,
          titre: f.description || f.rule_code || 'Non-conformite',
          source_label: `Conformite — ${f.site_nom}`,
          impact_eur: f.impact_eur || 0,
          priorite: f.severity || 'medium',
          route: '/conformite',
        });
      }
    }
    for (const a of actions.slice(0, 5)) {
      items.push({
        id: `act-${a.id}`,
        titre: a.titre || a.title || 'Action',
        source_label: `Plan d'action — ${a.site_nom || ''}`,
        impact_eur: a.impact_eur || 0,
        priorite: a.priorite || a.priority || 'medium',
        route: '/actions',
      });
    }
    return items
      .sort(
        (a, b) =>
          (PRIORITY_RANK[b.priorite] || 0) - (PRIORITY_RANK[a.priorite] || 0) ||
          b.impact_eur - a.impact_eur
      )
      .slice(0, 5);
  }, [compliance, actions]);

  const rawAlertsCount = useMemo(() => {
    if (!alertsSummary) return 0;
    return (alertsSummary.by_severity?.critical || 0) + (alertsSummary.by_severity?.warn || 0);
  }, [alertsSummary]);

  // Normalized model (no contradictions)
  const { kpis, alertsCount } = useMemo(
    () =>
      normalizeDashboardModel({
        kpis: rawKpis,
        topActions: rawTopActions,
        alertsCount: rawAlertsCount,
      }),
    [rawKpis, rawTopActions, rawAlertsCount]
  );

  // Briefing from scope data (pure model — no extra API call)
  const watchlist = useMemo(() => buildWatchlist(kpis, scopedSites), [kpis, scopedSites]); // eslint-disable-line react-hooks/exhaustive-deps
  const briefing = useMemo(
    () => buildBriefing(kpis, watchlist, alertsCount),
    [kpis, watchlist, alertsCount]
  ); // eslint-disable-line react-hooks/exhaustive-deps
  const opportunities = useMemo(
    () => buildOpportunities(kpis, scopedSites, { isExpert }),
    [kpis, scopedSites, isExpert]
  ); // eslint-disable-line react-hooks/exhaustive-deps
  // Merge watchlist signals + real open actions (rawTopActions) + opportunities
  const todayActions = useMemo(() => {
    const fromModel = buildTodayActions(kpis, watchlist, opportunities);
    // Inject real open actions from the action plan as 'high' priority items
    const seen = new Set(fromModel.map((a) => a.id));
    const fromActions = rawTopActions
      .filter((a) => !seen.has(a.id))
      .map((a) => ({
        id: a.id,
        label: a.titre,
        severity: a.priorite || 'medium',
        path: a.route,
        cta: a.source_label,
        type: 'action',
      }));
    return [...fromModel, ...fromActions].slice(0, 5);
  }, [kpis, watchlist, opportunities, rawTopActions]); // eslint-disable-line react-hooks/exhaustive-deps
  const healthState = useMemo(
    () => computeHealthState({ kpis, watchlist, briefing, consistency: { ok: true }, alertsCount }),
    [kpis, watchlist, briefing, alertsCount]
  ); // eslint-disable-line react-hooks/exhaustive-deps

  // Data coverage (shown in header trust signal)
  const coveragePct = useMemo(() => {
    return kpis.total > 0
      ? Math.round((scopedSites.filter((s) => s.conso_kwh_an > 0).length / kpis.total) * 100)
      : 0;
  }, [scopedSites, kpis.total]);

  const hasSites = scopedSites.length > 0;

  if (loading) {
    return (
      <PageShell icon={LayoutDashboard} title="Tableau de bord" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell icon={LayoutDashboard} title="Tableau de bord" subtitle={<ScopeSummary />}>
        <ErrorState title="Erreur de chargement" message={error} onRetry={loadData} />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={LayoutDashboard}
      title="Tableau de bord"
      subtitle={<ScopeSummary />}
      actions={
        <div className="flex items-center gap-2">
          {/* Trust signals — compact */}
          <div className="hidden sm:flex items-center gap-3 mr-2 text-[11px] text-gray-400">
            {lastSync && (
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {lastSync.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <span className="flex items-center gap-1" title="Couverture données">
              <Database size={11} />
              {coveragePct}%
            </span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => navigate('/cockpit')}>
            <FileText size={14} /> Vue exécutive
          </Button>
          {isExpert && (
            <Button variant="secondary" size="sm" onClick={loadData}>
              <RefreshCw size={14} /> Actualiser
            </Button>
          )}
          {!hasSites ? (
            <Button onClick={() => navigate('/import')}>
              <Upload size={16} /> Importer
            </Button>
          ) : (
            <Button onClick={() => navigate('/conformite')}>
              <Scan size={16} /> Scanner
            </Button>
          )}
        </div>
      }
    >
      {/* ── Health Summary ── */}
      <CockpitTabs active="dashboard" />
      <HealthSummary healthState={healthState} onNavigate={navigate} />

      {/* ── Briefing du jour ── */}
      <BriefingHeroCard briefing={briefing} onNavigate={navigate} />

      {/* ── KPI Row: 3 MetricCards ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          accent="conformite"
          icon={ShieldCheck}
          label="Conformité"
          value={`${kpis.pctConf}%`}
          sub={`${kpis.conformes} / ${kpis.total} sites conformes`}
          status={kpis.compStatus}
          onClick={() => navigate('/conformite')}
        />
        <MetricCard
          accent="risque"
          icon={TrendingDown}
          label="Risque financier"
          value={kpis.risque > 0 ? `${Math.round(kpis.risque / 1000)} k€` : '—'}
          sub={`${kpis.nonConformes + kpis.aRisque} sites à risque (périmètre sélectionné)`}
          status={kpis.risqueStatus}
          onClick={() => navigate(toActionsList())}
        />
        <MetricCard
          accent="alertes"
          icon={Bell}
          label="Alertes actives"
          value={alertsCount}
          sub={
            alertsSummary
              ? `dont ${alertsSummary.by_severity?.critical || 0} critiques`
              : 'Chargement...'
          }
          status={alertsCount > 5 ? 'crit' : alertsCount > 0 ? 'warn' : 'ok'}
          onClick={() => navigate('/anomalies')}
        />
      </div>

      {/* ── Essentiels patrimoine ── */}
      <EssentialsRow
        kpis={kpis}
        sites={scopedSites}
        onOpenMaturite={() => navigate('/cockpit')}
        onNavigate={navigate}
      />

      {/* ── KPIs J-1 (Step 5) ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="kpis-j1">
        <KpiJ1Card
          label="Conso hier (J-1)"
          value={kpisJ1?.consoHierKwh != null ? fmtKwh(kpisJ1.consoHierKwh) : '—'}
          sub={
            kpisJ1?.consoHierKwh != null
              ? `${scopedSites.length} sites · données réelles`
              : 'Chargement...'
          }
          loading={cmdLoading}
        />
        <KpiJ1Card label="Conso ce mois" value="—" sub="Endpoint à venir" loading={cmdLoading} />
        <KpiJ1Card
          label="Pic puissance J-1"
          value={kpisJ1?.picKw != null ? `${kpisJ1.picKw} kW` : '—'}
          sub={kpisJ1?.picKw != null ? 'Maximum horaire agrégé' : 'Pas de données horaires'}
          accent={kpisJ1?.picKw > 40 ? 'warn' : 'neutral'}
          loading={cmdLoading}
        />
        <KpiJ1Card
          label="Intensité CO₂ réseau"
          value={kpisJ1?.co2ResKgKwh != null ? `${kpisJ1.co2ResKgKwh} g/kWh` : '—'}
          sub="Connecteur RTE à brancher"
          loading={cmdLoading}
        />
      </div>

      {/* ── Graphiques consommation (Step 5) ── */}
      {(weekSeries?.length > 0 || hourlyProfile?.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="charts-conso">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Conso 7 jours — {scopedSites.length} sites (kWh/j)
            </div>
            {weekSeries?.length > 0 ? (
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={weekSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    tickFormatter={(d) => d?.slice(5)}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    tickFormatter={(v) => `${Math.round(v)}`}
                  />
                  <Tooltip
                    formatter={(v) => [v != null ? `${Math.round(v)} kWh` : '—', 'Conso']}
                    labelFormatter={(l) => `Jour : ${l}`}
                  />
                  <Bar dataKey="kwh" name="Cette semaine" fill="#378ADD" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[140px] flex items-center justify-center text-xs text-gray-400">
                Pas de données disponibles
              </div>
            )}
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Profil journalier J-1 (kW agrégé)
            </div>
            {hourlyProfile?.length > 0 ? (
              <ResponsiveContainer width="100%" height={140}>
                <ComposedChart data={hourlyProfile}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="heure" tick={{ fontSize: 9, fill: '#9ca3af' }} interval={3} />
                  <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={(v) => `${v}kW`} />
                  <Tooltip formatter={(v, name) => [v != null ? `${v} kW` : '—', name]} />
                  <Area
                    type="monotone"
                    dataKey="kw"
                    name="Réel J-1"
                    stroke="#378ADD"
                    fill="rgba(55,138,221,0.07)"
                    strokeWidth={2}
                    dot={false}
                  />
                  {kpisJ1?.picKw > 38 && (
                    <ReferenceLine
                      y={38}
                      stroke="#E24B4A"
                      strokeDasharray="4 3"
                      label={{ value: 'Seuil', position: 'right', fontSize: 9, fill: '#E24B4A' }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[140px] flex items-center justify-center text-xs text-gray-400">
                Profil horaire indisponible
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Progression trajectoire mensuelle (Step 5) ── */}
      {trajectoire && (
        <div
          className="bg-white border border-gray-200 rounded-lg p-4"
          data-testid="trajectoire-mensuelle"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Progression trajectoire mensuelle
            </span>
            <span className="text-xs font-medium bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
              {trajectoire.reductionPctActuelle != null
                ? `${trajectoire.reductionPctActuelle}%`
                : '—'}{' '}
              objectif {trajectoire.objectif2026Pct ?? -25}%
            </span>
          </div>
          <div className="mb-3">
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-gray-700">Réel 2026</span>
              <span className="text-red-600 font-medium">
                {trajectoire.reductionPctActuelle != null
                  ? `${trajectoire.reductionPctActuelle}% · retard`
                  : '—'}
              </span>
            </div>
            <div className="relative h-2.5 bg-gray-100 rounded-full overflow-visible">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{
                  width: `${
                    trajectoire.reductionPctActuelle != null
                      ? Math.min(
                          100,
                          (Math.abs(trajectoire.reductionPctActuelle) /
                            Math.abs(trajectoire.objectif2026Pct ?? -25)) *
                            100
                        )
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0%</span>
              <span className="text-blue-600 font-medium">
                Obj. {trajectoire.objectif2026Pct ?? -25}%
              </span>
              <span>-40%</span>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-gray-700">Avec actions planifiées</span>
              <span className="text-green-700 font-medium">
                {trajectoire.projectionMwh?.some((v) => v != null) ? 'Objectif atteignable' : '—'}
              </span>
            </div>
            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-teal-500 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Actions à démarrer avant le{' '}
            <span className="text-amber-600 font-medium">30 juin 2026</span> pour atteindre
            l'objectif annuel.
          </p>
        </div>
      )}

      {/* ── À traiter aujourd'hui + Sites à risque ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Deduped priority actions from model */}
        <TodayActionsCard actions={todayActions} onNavigate={navigate} />

        {/* Sites à risque — table with accent on risk column */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Sites à traiter</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/patrimoine')}>
              Patrimoine <ArrowRight size={14} />
            </Button>
          </div>
          {scopedSites.filter(
            (s) => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque'
          ).length === 0 ? (
            <div className="px-5 py-8">
              <EmptyState
                icon={CheckCircle2}
                title="Aucune alerte reglementaire active"
                text="Aucune penalite identifiee. Verifier les anomalies et preuves separement."
              />
            </div>
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Site</Th>
                  <Th>Statut</Th>
                  <Th className="text-right">Risque</Th>
                </tr>
              </Thead>
              <Tbody>
                {scopedSites
                  .filter(
                    (s) =>
                      s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque'
                  )
                  .sort((a, b) => (b.risque_eur || 0) - (a.risque_eur || 0))
                  .slice(0, 8)
                  .map((site) => (
                    <Tr
                      key={site.id}
                      onClick={() => navigate(`/sites/${site.id}`)}
                      className="group cursor-pointer hover:bg-blue-50/40"
                    >
                      <Td>
                        <div className="font-medium text-gray-900">{site.nom}</div>
                        <div className="text-xs text-gray-400">{site.ville}</div>
                      </Td>
                      <Td>
                        <div className="flex items-center gap-1.5">
                          <StatusDot
                            status={site.statut_conformite === 'non_conforme' ? 'crit' : 'warn'}
                          />
                          <span className="text-xs text-gray-600">
                            {site.statut_conformite === 'non_conforme'
                              ? 'Non conforme'
                              : 'À risque'}
                          </span>
                        </div>
                      </Td>
                      <Td className="text-right text-sm font-medium">
                        {site.risque_eur > 0 ? (
                          <span className="text-amber-700">
                            {(site.risque_eur || 0).toLocaleString('fr-FR')} €
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </Td>
                    </Tr>
                  ))}
              </Tbody>
            </Table>
          )}
        </Card>
      </div>

      {/* ── Accès rapide aux modules ── */}
      {/* ── Sites J-1 vs Baseline (Step rapprochement) ── */}
      <SitesBaselineCard />

      <ModuleLaunchers kpis={kpis} isExpert={isExpert} onNavigate={navigate} />
    </PageShell>
  );
}
