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
  Upload,
  Scan,
  RefreshCw,
  CheckCircle2,
  Database,
  FileText,
} from 'lucide-react';
import {
  Card,
  Button,
  Skeleton,
  SkeletonCard,
  PageShell,
  StatusDot,
  EmptyState,
  ErrorState,
  ScopeSummary,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { toActionsList as _toActionsList } from '../services/routes';
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
import DataFreshnessBadge from '../ui/DataFreshnessBadge';
import CrossModuleCTA from '../components/CrossModuleCTA';
import _HealthSummary from '../components/HealthSummary';
import ValueCounterCard from '../components/ValueCounterCard';
import CsatModal from '../components/CsatModal';
import NpsModal from '../components/NpsModal';
// Sprint 2 Vague A ét4' — empilement legacy supprimé (PriorityHero +
// DeadlineBanner + MorningBriefCard) au profit du briefing Sol §5 unique.
// Audit personas Marie : « patch isolé », doctrine v2 §6.3. SolNarrative +
// SolWeekCards portent désormais l'intégralité du récit ATF.
// Sprint 1.1 — grammaire Sol industrialisée (ADR-001)
// Sprint 2 Vague B ét8'-bis — HOC SolBriefingHead/Footer factorise grammaire §5.
import SolBriefingHead from '../ui/sol/SolBriefingHead';
import SolBriefingFooter from '../ui/sol/SolBriefingFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';
import TopDeriveSitesCard from './cockpit/TopDeriveSitesCard';
import TodayActionsCard from './cockpit/TodayActionsCard';
import CockpitTabs from '../ui/CockpitTabs';
import SolPageHeader from '../ui/sol/SolPageHeader';
import _ModuleLaunchers from './cockpit/ModuleLaunchers';
import _EssentialsRow from './cockpit/EssentialsRow';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import { useCockpitData } from '../hooks/useCockpitData';
import {
  Area,
  BarChart,
  Bar,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import { fmtEur, scopeKicker } from '../utils/format';
import SitesBaselineCard from './cockpit/SitesBaselineCard';

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

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
  const { trajectoire, kpis: cockpitKpis } = useCockpitData();
  // Sprint 1.1 — briefing éditorial Sol §5 (ADR-001 grammaire industrialisée).
  // Backend orchestre KPIs + narrative + week-cards via /api/pages/cockpit_daily/briefing.
  const {
    briefing: solBriefing,
    loading: solBriefingLoading,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('cockpit_daily', { persona: 'daily' });

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
    // Source unique backend — pas de fallback conformes/total (règle no-calc-in-front)
    const pctConf =
      cockpitKpis?.conformiteScore != null ? Math.round(cockpitKpis.conformiteScore) : 0;
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
  }, [scopedSites, cockpitKpis]);

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
          titre: f.description || f.rule_code || 'Non-conformité',
          source_label: `Conformité — ${f.site_nom}`,
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
  const _healthState = useMemo(
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
      <PageShell
        icon={LayoutDashboard}
        title={
          <>
            Tableau de bord
            <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600">
              Opérationnel
            </span>
          </>
        }
        subtitle="Chargement..."
      >
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
      <PageShell
        icon={LayoutDashboard}
        title={
          <>
            Tableau de bord
            <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600">
              Opérationnel
            </span>
          </>
        }
        subtitle={<ScopeSummary />}
      >
        <ErrorState title="Erreur de chargement" message={error} onRetry={loadData} />
      </PageShell>
    );
  }

  // Fallback header pendant le chargement du briefing Sol — on garde la
  // signature visuelle même si le backend tarde à répondre.
  const solHeaderFallback = (
    <SolPageHeader
      kicker={solBriefing?.kicker || scopeKicker('ACCUEIL', org?.nom, scopedSites?.length)}
      title={solBriefing?.title || 'Tableau de bord'}
      italicHook={solBriefing?.italicHook || 'opérationnel'}
      subtitle={<ScopeSummary />}
    />
  );

  return (
    <PageShell
      editorialHeader={solHeaderFallback}
      actions={
        <div className="flex items-center gap-2">
          {/* Trust signals : fraîcheur des données + couverture périmètre. */}
          <DataFreshnessBadge
            computedAt={
              kpisJ1?.consoDate
                ? `${kpisJ1.consoDate}T08:00:00Z`
                : (lastSync?.toISOString() ?? null)
            }
            sourceLabel={cockpitKpis?.consoSource === 'metered' ? 'EMS' : null}
          />
          <span
            className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-50 text-gray-600 text-[11px] font-medium border border-gray-200"
            title="Couverture données"
          >
            <Database size={10} />
            {coveragePct}%
          </span>
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
      <CockpitTabs active="dashboard" />

      {/* ── Préambule éditorial Sol §5 (ADR-001 — S1.1bis P0-4) ──
          Le briefing Sol est désormais le PRÉAMBULE UNIQUE de la page.
          Audit Sprint 1.1 : empilement legacy (PriorityHero+DeadlineBanner+
          MorningBriefCard+CTAs+DashboardHeroFeatured) avant la narrative
          Sol était cité comme friction P0 par 6/10 agents. La grammaire
          §5 doit ouvrir la page, pas être noyée en position 7.

          DashboardHeroFeatured fallback chargement supprimé — SolNarrative
          gère son propre état loading via solBriefingLoading + skeleton
          intrinsèque (3 KPIs avec animate-pulse). */}
      {/* Sprint 2 Vague B ét8'-bis — factorisation grammaire §5 via SolBriefingHead.
          Week-cards "Cette semaine chez vous" alimentées via le HOC (ADR-001 +
          ADR-002 chantier α S2 : Sprint 2 alimentera depuis le moteur
          d'événements proactif). */}
      <SolBriefingHead
        briefing={solBriefing}
        error={solBriefingError}
        onRetry={solBriefingRefetch}
        omitHeader
        onNavigate={navigate}
      />

      {/* Sprint 2 Vague A ét4' — bloc legacy supprimé (PriorityHero +
          DeadlineBanner + MorningBriefCard). Les signaux portés par ces
          composants sont désormais incarnés par SolWeekCards (briefing Sol
          §5 ci-dessus). Audit Marie post-Vague A ét2 : la cohabitation
          rétrogradée gâchait l'effet "page nettoyée" attendu de la
          grammaire Sol. */}

      {/* Modals fixed-position (n'affectent pas le flow visuel) */}
      <CsatModal orgId={org?.id} />
      <NpsModal orgId={org?.id} userCreatedAt={org?.created_at} />

      {/* Funnel CTAs compacts — pivots cross-pillar (déplacés post-briefing) */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => navigate('/cockpit')}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-[var(--sol-calme-bg)] hover:bg-[var(--sol-calme-bg)] border border-[var(--sol-calme-fg)]/30 text-[var(--sol-calme-fg)] text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
        >
          <FileText size={14} aria-hidden="true" />
          Préparer le brief CFO
          <ArrowRight size={12} aria-hidden="true" className="opacity-60" />
        </button>
        <button
          type="button"
          onClick={() => navigate('/conformite')}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-[var(--sol-succes-bg)] hover:bg-[var(--sol-succes-bg)] border border-[var(--sol-succes-line)] text-[var(--sol-succes-fg)] text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-succes-fg)]"
        >
          <Scan size={14} aria-hidden="true" />
          Ouvrir conformité
          <ArrowRight size={12} aria-hidden="true" className="opacity-60" />
        </button>
      </div>

      {/* Top 5 sites en dérive (drill-down vers détail site). */}
      <TopDeriveSitesCard sites={scopedSites} totalSites={kpis?.total} />

      {/* ── Graphiques consommation (Step 5 — toujours visibles) ──
          Audit Marie/Jean-Marc : axes lisibles, légendes claires (jour précédent
          vs hier), zones HP/HC visualisées sur le profil journalier. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="charts-conso">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Conso 7 jours — {scopedSites.length} sites (MWh/j)
          </div>
          {weekSeries?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekSeries} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  tickFormatter={(d) => {
                    // Audit : "il manque le mois avec le jour" — afficher
                    // jour court + numéro + mois court (ex. "Mar 22 avr.").
                    if (!d) return '';
                    const days = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
                    const months = [
                      'janv.',
                      'févr.',
                      'mars',
                      'avr.',
                      'mai',
                      'juin',
                      'juil.',
                      'août',
                      'sept.',
                      'oct.',
                      'nov.',
                      'déc.',
                    ];
                    const dt = new Date(d);
                    return `${days[dt.getDay()]} ${dt.getDate()} ${months[dt.getMonth()]}`;
                  }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  tickFormatter={(v) => `${(v / 1000).toFixed(1)}`}
                  label={{
                    value: 'MWh',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 10, fill: '#9ca3af' },
                  }}
                />
                <Tooltip
                  formatter={(v) => [v != null ? `${(v / 1000).toFixed(1)} MWh` : '—', 'Conso']}
                  labelFormatter={(l) => {
                    if (!l) return '';
                    const dt = new Date(l);
                    return dt.toLocaleDateString('fr-FR', {
                      weekday: 'long',
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    });
                  }}
                />
                <Bar dataKey="kwh" name="Cette semaine" fill="#378ADD" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-xs text-gray-400">
              Pas de données disponibles
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Profil journalier — agrégé courbe de charge
            </div>
            {/* Légende HP/HC : zones tarifaires standard FR (HC = 22h-7h).
                Audit : "il manque le dégradé de couleur HP/HC". */}
            <div className="flex items-center gap-3 text-[10px] text-gray-500">
              <span className="inline-flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-amber-100 ring-1 ring-amber-200" />
                Heures pleines
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-indigo-100 ring-1 ring-indigo-200" />
                Heures creuses (22h–7h)
              </span>
            </div>
          </div>
          {hourlyProfile?.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart
                data={hourlyProfile}
                margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
              >
                <defs>
                  <linearGradient id="hphcAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#378ADD" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#378ADD" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                {/* Zones tarifaires : HC standard FR = 22h00 → 06h59 */}
                <ReferenceArea
                  x1="0h"
                  x2="7h"
                  fill="#6366f1"
                  fillOpacity={0.06}
                  ifOverflow="extendDomain"
                />
                <ReferenceArea
                  x1="22h"
                  x2="23h"
                  fill="#6366f1"
                  fillOpacity={0.06}
                  ifOverflow="extendDomain"
                />
                <XAxis dataKey="heure" tick={{ fontSize: 9, fill: '#9ca3af' }} interval={2} />
                <YAxis
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  /* Axe Y propre : unité kW affichée une seule fois en label
                     (audit : "attention à l'axe des Y en kW") */
                  tickFormatter={(v) => `${v}`}
                  label={{
                    value: 'kW',
                    angle: -90,
                    position: 'insideLeft',
                    offset: 8,
                    style: { fontSize: 10, fill: '#6b7280' },
                  }}
                />
                <Tooltip
                  formatter={(v, name) => [v != null ? `${v} kW` : '—', name]}
                  labelFormatter={(h) => `Heure : ${h}`}
                />
                <Legend
                  verticalAlign="bottom"
                  height={20}
                  iconType="line"
                  wrapperStyle={{ fontSize: 10, color: '#6b7280' }}
                />
                <Area
                  type="monotone"
                  dataKey="kw"
                  /* Audit : légende "jour précédent / hier" — désambiguïser :
                     les données affichées sont la moyenne agrégée du dernier
                     jour disponible (typiquement hier). */
                  name="Hier (J-1) — agrégé"
                  stroke="#378ADD"
                  fill="url(#hphcAreaGradient)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                {/* Seuil puissance : 80% du pic comme alerte visuelle */}
                {kpisJ1?.picKw > 0 && (
                  <ReferenceLine
                    y={Math.round(kpisJ1.picKw * 0.8)}
                    stroke="#E24B4A"
                    strokeDasharray="4 3"
                    label={{
                      value: `Seuil ${Math.round(kpisJ1.picKw * 0.8)} kW`,
                      position: 'right',
                      fontSize: 9,
                      fill: '#E24B4A',
                    }}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex flex-col items-center justify-center gap-2 text-xs text-gray-400">
              {/* Audit P0.1 : pas de fake data. Si la courbe n'est pas raccordée,
                  on affiche un état explicite plutôt qu'un profil estimé. */}
              <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 ring-1 ring-amber-200 text-[10px] font-medium uppercase tracking-wide">
                Donnée indisponible
              </span>
              <span>Courbe de charge non raccordée — connecter Enedis pour activer</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Trajectoire + Actions du jour (maquette : 2 colonnes) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Progression trajectoire mensuelle */}
        {trajectoire ? (
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
                objectif {trajectoire.objectifPremierJalonPct ?? -40}%
              </span>
            </div>
            <div className="mb-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-gray-700">Réel 2026</span>
                {trajectoire.reductionPctActuelle != null ? (
                  trajectoire.reductionPctActuelle > trajectoire.objectifPremierJalonPct ? (
                    <span className="text-red-600 font-medium">
                      {trajectoire.reductionPctActuelle}% · retard
                    </span>
                  ) : (
                    <span className="text-green-700 font-medium">
                      {trajectoire.reductionPctActuelle}% · en avance
                    </span>
                  )
                ) : (
                  <span className="text-gray-400">—</span>
                )}
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
                              Math.abs(trajectoire.objectifPremierJalonPct ?? -40)) *
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
                  Obj. {trajectoire.objectifPremierJalonPct ?? -40}%
                </span>
                <span>-40%</span>
              </div>
            </div>
            <div>
              {/* HIGH-2: masquer barre si projection vide */}
              {trajectoire.projectionMwh?.some((v) => v != null) ? (
                <>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-gray-700">Avec actions planifiées</span>
                    <span className="text-green-700 font-medium">Objectif atteignable</span>
                  </div>
                  <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full" style={{ width: '100%' }} />
                  </div>
                </>
              ) : (
                <p className="text-xs text-gray-400 italic mt-2">
                  Projection disponible après ajout d'actions planifiées.
                </p>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Actions à démarrer avant le{' '}
              <span className="text-amber-600 font-medium">30 juin 2026</span> pour atteindre
              l'objectif annuel.
            </p>
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg p-4 min-h-[200px]">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider block mb-3">
              Progression trajectoire mensuelle
            </span>
            <div className="space-y-3 mt-6">
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-2.5 w-full rounded-full" />
              <Skeleton className="h-3 w-40 mt-4" />
              <Skeleton className="h-2.5 w-full rounded-full" />
            </div>
            <p className="text-[10px] text-gray-400 mt-4">Chargement des données trajectoire...</p>
          </div>
        )}

        {/* Actions du jour */}
        <TodayActionsCard actions={todayActions} onNavigate={navigate} />
      </div>

      {/* ── Sites J-1 vs Baseline ── */}
      <SitesBaselineCard consoHierTotal={kpisJ1?.consoHierKwh} />

      {/* Compteur valeur cumulée PROMEOS — footer expert-only (pas de
          vente UI dans le flow principal du dashboard). */}
      {isExpert && <ValueCounterCard orgId={org?.id} />}

      {/* Sections legacy masquées — redondantes avec les widgets cockpit world-class */}
      {/* HealthSummary, BriefingHeroCard, EssentialsRow déplacés dans /cockpit expert mode */}

      {/* Sections complémentaires masquées — redondantes avec cockpit /cockpit */}
      {/* Sites à traiter, ModuleLaunchers → visibles uniquement dans /cockpit */}
      {false && isExpert && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                  title="Aucune alerte réglementaire active"
                  text="Aucune pénalité identifiée. Vérifier les anomalies et preuves séparément."
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
                            <span className="text-amber-700">{fmtEur(site.risque_eur)}</span>
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
      )}

      {/* ModuleLaunchers masqué — accessible via /cockpit expert mode */}

      {/* Sprint 2 Vague B ét8'-bis — SolPageFooter §5 factorisé via HOC. */}
      <SolBriefingFooter briefing={solBriefing} />
    </PageShell>
  );
}
