/**
 * PROMEOS — Vue exécutive (/cockpit) Cockpit V2
 * Résumé exécutif + KPIs décideur + Briefing + Risques + Opportunités.
 * EssentialsRow + données relégués en bas.
 */
import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, ArrowRight, Search, AlertTriangle } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import {
  getNotificationsSummary,
  getComplianceTimeline,
  getMarketContext,
  getComplianceScoreTrend,
} from '../services/api';
import useRenderTiming from '../hooks/useRenderTiming';
import { fmtKwh } from '../utils/format';
import { toActionsList } from '../services/routes';
import {
  Button,
  Card,
  PageShell,
  Progress,
  Modal,
  Pagination,
  StatusDot,
  Tabs,
  EmptyState,
  ScopeSummary,
  EvidenceDrawer,
  Explain,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import ErrorState from '../ui/ErrorState';
// Cockpit V3 — model + sub-components
import {
  buildTopSites,
  buildOpportunities,
  checkConsistency,
  buildExecutiveKpis,
} from '../models/dashboardEssentials';
// V3: removed imports — buildWatchlist, buildBriefing, buildTodayActions,
// buildExecutiveSummary, computeHealthState (replaced by PriorityHero + topActions)
import EssentialsRow from './cockpit/EssentialsRow';
import OpportunitiesCard from './cockpit/OpportunitiesCard';
import TopSitesCard from './cockpit/TopSitesCard';
import ModuleLaunchers from './cockpit/ModuleLaunchers';
import ExecutiveKpiRow from './cockpit/ExecutiveKpiRow';
import ImpactDecisionPanel from './cockpit/ImpactDecisionPanel';
import DataActivationPanel from './cockpit/DataActivationPanel';
import DataQualityWidget from './cockpit/DataQualityWidget';
import DemoSpotlight from '../components/onboarding/DemoSpotlight';
import { MarketContextCompact } from '../components/purchase/MarketContextBanner';
import { READINESS_WEIGHTS, getRiskStatus, getStatusBadgeProps } from '../lib/constants';
import {
  evidenceConformite,
  evidenceRisque,
  evidenceMaturite,
  evidenceCouverture,
} from '../ui/evidence.fixtures';
import { useComplianceMeta } from '../hooks/useComplianceMeta';

// ── Consistency banner (inline — too small for its own file) ─────────────────
function ConsistencyBanner({ issues }) {
  if (!issues?.length) return null;
  return (
    <div className="flex items-start gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
      <AlertTriangle size={13} className="shrink-0 mt-0.5" />
      <span>{issues[0].label} — synchronisation recommandée.</span>
    </div>
  );
}

const Cockpit = () => {
  useRenderTiming('Cockpit');
  const navigate = useNavigate();
  const _actionDrawer = useActionDrawer(); // V3: available but not used in DG view
  const { org, portefeuille, portefeuilles, scopedSites, sitesLoading } = useScope();
  const { isExpert } = useExpertMode();
  const complianceMeta = useComplianceMeta();
  const [showMaturiteModal, setShowMaturiteModal] = useState(false);
  const [siteSort, setSiteSort] = useState({ col: '', dir: '' });
  const [siteSearch, setSiteSearch] = useState('');
  const [sitePage, setSitePage] = useState(1);
  const [activePtf, setActivePtf] = useState('all');
  const [evidenceOpen, setEvidenceOpen] = useState(null); // KPI id or null
  const [alertsCount, setAlertsCount] = useState(0);
  const [error, setError] = useState(null);
  const [showDetail, setShowDetail] = useState(false); // V3: toggle zone 4
  const sitePageSize = 20;

  // A.2: Unified compliance score from backend
  const [complianceApi, setComplianceApi] = useState(null);
  const [nextDeadline, setNextDeadline] = useState(null);
  const [_totalPenaltyExposure, setTotalPenaltyExposure] = useState(null);
  // A.1: Consumption source tracking
  const [consoSource, setConsoSource] = useState(null);
  // Step 24: Market context compact
  const [marketContext, setMarketContext] = useState(null);
  // Step 33: Compliance score trend (6 months)
  const [scoreTrend, setScoreTrend] = useState(null);

  // Fetch real alert count from notifications summary (same source as CommandCenter)
  useEffect(() => {
    setError(null);
    getNotificationsSummary(org?.id, scopedSites.length === 1 ? scopedSites[0]?.id : null)
      .then((data) => {
        const count = (data?.by_severity?.critical || 0) + (data?.by_severity?.warn || 0);
        setAlertsCount(count);
      })
      .catch((err) => {
        setAlertsCount(0);
        setError(err?.message || 'Erreur chargement des données');
      });
  }, [org, scopedSites]);

  // A.2: Fetch unified compliance score
  useEffect(() => {
    if (!org?.id) return;
    fetch(`/api/compliance/portfolio/score`, {
      headers: { 'X-Org-Id': String(org.id) },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setComplianceApi(data))
      .catch(() => setComplianceApi(null));
  }, [org?.id]);

  // Step 13: Fetch next regulatory deadline
  useEffect(() => {
    if (!org?.id) return;
    getComplianceTimeline()
      .then((data) => {
        setNextDeadline(data?.next_deadline || null);
        setTotalPenaltyExposure(data?.total_penalty_exposure_eur || null);
      })
      .catch(() => {
        setNextDeadline(null);
        setTotalPenaltyExposure(null);
      });
  }, [org?.id]);

  // Step 24: Fetch market context
  useEffect(() => {
    getMarketContext('ELEC')
      .then(setMarketContext)
      .catch(() => setMarketContext(null));
  }, []);

  // Step 33: Fetch compliance score trend
  useEffect(() => {
    if (!org?.id) return;
    getComplianceScoreTrend({ months: 6 })
      .then((data) => setScoreTrend(data?.trend || null))
      .catch(() => setScoreTrend(null));
  }, [org?.id]);

  // A.1: Fetch consumption source from cockpit API (conso_confidence)
  useEffect(() => {
    if (!org?.id) return;
    fetch(`/api/cockpit`, {
      headers: { 'X-Org-Id': String(org.id) },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const conf = data?.stats?.conso_confidence;
        if (conf && conf !== 'none') setConsoSource('metered');
        else setConsoSource(null);
      })
      .catch(() => setConsoSource(null));
  }, [org?.id]);

  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risqueTotal = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const couvertureDonnees =
      total > 0 ? Math.round((sites.filter((s) => s.conso_kwh_an > 0).length / total) * 100) : 0;
    const suiviConformite = total > 0 ? Math.round((conformes / total) * 100) : 0;
    const actionsActives =
      total > 0 ? Math.round((conformes / total) * 60 + ((total - nonConformes) / total) * 40) : 80;
    const readinessScore =
      total > 0
        ? Math.round(
            couvertureDonnees * READINESS_WEIGHTS.data +
              suiviConformite * READINESS_WEIGHTS.conformity +
              actionsActives * READINESS_WEIGHTS.actions
          )
        : 0;
    const compStatus =
      nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    const risqueStatus = getRiskStatus(risqueTotal);
    return {
      total,
      conformes,
      nonConformes,
      aRisque,
      risqueTotal,
      readinessScore,
      couvertureDonnees,
      suiviConformite,
      actionsActives,
      compStatus,
      risqueStatus,
      // A.2: unified compliance score from API (null if not yet loaded)
      compliance_score: complianceApi?.avg_score ?? null,
      compliance_confidence:
        complianceApi?.high_confidence_count > total * 0.6
          ? 'high'
          : complianceApi
            ? 'medium'
            : null,
    };
  }, [scopedSites, complianceApi]);

  const isSingleSite = scopedSites.length === 1;
  const singleSite = isSingleSite ? scopedSites[0] : null;

  // Cockpit V2 — derived model data (no extra API calls)
  const consistency = useMemo(() => checkConsistency(kpis), [kpis]); // eslint-disable-line react-hooks/exhaustive-deps
  const opportunities = useMemo(
    () => buildOpportunities(kpis, scopedSites, { isExpert }),
    [kpis, scopedSites, isExpert]
  ); // eslint-disable-line react-hooks/exhaustive-deps
  const topSites = useMemo(() => buildTopSites(scopedSites), [scopedSites]); // eslint-disable-line react-hooks/exhaustive-deps
  const executiveKpis = useMemo(() => buildExecutiveKpis(kpis, scopedSites), [kpis, scopedSites]); // eslint-disable-line react-hooks/exhaustive-deps

  const scopeLabel = portefeuille
    ? `${org?.nom || 'Societe'} / ${portefeuille.nom}`
    : org?.nom || 'Societe';

  const evidenceMap = useMemo(
    () => ({
      conformite: evidenceConformite(scopeLabel, complianceMeta),
      risque: evidenceRisque(scopeLabel, kpis.risqueTotal),
      maturite: evidenceMaturite(scopeLabel),
      couverture: evidenceCouverture(scopeLabel),
    }),
    [scopeLabel, kpis.risqueTotal, complianceMeta]
  );

  const ptfWithCounts = useMemo(() => {
    return portefeuilles
      .map((pf) => {
        const sites = scopedSites.filter((s) => ((s.id - 1) % 5) + 1 === pf.id);
        const count = sites.length;
        const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
        const risque = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
        const pctConf = count > 0 ? Math.round((conformes / count) * 100) : 0;
        return { ...pf, nb_sites: count, conformes, risque, pctConf };
      })
      .filter((pf) => pf.nb_sites > 0);
  }, [portefeuilles, scopedSites]);

  const ptfTabs = useMemo(() => {
    const tabs = [{ id: 'all', label: `Tous (${scopedSites.length})` }];
    for (const pf of ptfWithCounts) {
      tabs.push({ id: String(pf.id), label: `${pf.nom} (${pf.nb_sites})` });
    }
    return tabs;
  }, [ptfWithCounts, scopedSites.length]);

  const portfolioFilteredSites = useMemo(() => {
    if (activePtf === 'all') return scopedSites;
    const pfId = parseInt(activePtf);
    return scopedSites.filter((s) => ((s.id - 1) % 5) + 1 === pfId);
  }, [activePtf, scopedSites]);

  const filteredSites = useMemo(() => {
    let list = [...portfolioFilteredSites];
    if (siteSearch.trim()) {
      const q = siteSearch.toLowerCase();
      list = list.filter(
        (s) =>
          s.nom.toLowerCase().includes(q) ||
          (s.ville || '').toLowerCase().includes(q) ||
          (s.usage || '').toLowerCase().includes(q)
      );
    }
    if (siteSort.col) {
      list.sort((a, b) => {
        let va = a[siteSort.col];
        let vb = b[siteSort.col];
        if (typeof va === 'number' && typeof vb === 'number') {
          return siteSort.dir === 'asc' ? va - vb : vb - va;
        }
        return siteSort.dir === 'asc'
          ? String(va || '').localeCompare(String(vb || ''))
          : String(vb || '').localeCompare(String(va || ''));
      });
    }
    return list;
  }, [portfolioFilteredSites, siteSearch, siteSort]);

  const sitesPageData = filteredSites.slice((sitePage - 1) * sitePageSize, sitePage * sitePageSize);

  function handleSiteSort(col) {
    setSiteSort((prev) => {
      if (prev.col === col) {
        if (prev.dir === 'asc') return { col, dir: 'desc' };
        if (prev.dir === 'desc') return { col: '', dir: '' };
      }
      return { col, dir: 'asc' };
    });
    setSitePage(1);
  }

  const getStatusInfo = (statut) => {
    const { variant, label } = getStatusBadgeProps(statut);
    return { dot: variant, label };
  };

  // ── V3 final : derive priority #1 for PriorityHero ──
  const priority1 = useMemo(() => {
    // Find the single most critical issue to display
    if (kpis.nonConformes > 0) {
      return {
        type: 'critical',
        title: `${kpis.nonConformes} site${kpis.nonConformes > 1 ? 's' : ''} non conforme${kpis.nonConformes > 1 ? 's' : ''} — mise en conformité requise`,
        impact:
          kpis.risqueTotal > 0 ? `${Math.round(kpis.risqueTotal / 1000)} k€ d'exposition` : null,
        deadline: nextDeadline
          ? `Échéance : ${(() => {
              try {
                return new Date(nextDeadline.deadline).toLocaleDateString('fr-FR', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                });
              } catch {
                return nextDeadline.deadline;
              }
            })()}`
          : null,
        cta: { label: 'Voir conformité', path: '/conformite' },
      };
    }
    if (kpis.aRisque > 0) {
      return {
        type: 'warning',
        title: `${kpis.aRisque} site${kpis.aRisque > 1 ? 's' : ''} à risque réglementaire`,
        impact:
          kpis.risqueTotal > 0 ? `${Math.round(kpis.risqueTotal / 1000)} k€ d'exposition` : null,
        deadline: nextDeadline
          ? `Prochaine échéance : ${nextDeadline.label} (${nextDeadline.days_remaining}j)`
          : null,
        cta: { label: "Voir le plan d'action", path: toActionsList() },
      };
    }
    if (alertsCount > 0) {
      return {
        type: 'info',
        title: `${alertsCount} alerte${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''} à traiter`,
        impact: null,
        deadline: null,
        cta: { label: 'Voir les alertes', path: '/notifications' },
      };
    }
    return {
      type: 'ok',
      title: 'Aucun écart réglementaire détecté',
      impact: null,
      deadline: 'Décret Tertiaire et BACS évalués',
      cta: { label: 'Voir conformité', path: '/conformite' },
    };
  }, [kpis, nextDeadline, alertsCount]);

  // ── V3 final : derive top 3 actions for Zone 3 ──
  const topActions = useMemo(() => {
    const actions = [];
    if (kpis.nonConformes > 0) {
      actions.push({
        id: 'fix-nc',
        label: `Corriger ${kpis.nonConformes > 1 ? 'les' : 'la'} non-conformité${kpis.nonConformes > 1 ? 's' : ''} réglementaire${kpis.nonConformes > 1 ? 's' : ''}`,
        impact: kpis.risqueTotal > 0 ? `${Math.round(kpis.risqueTotal / 1000)} k€` : null,
        path: '/conformite',
      });
    }
    if (kpis.aRisque > 0 && actions.length < 3) {
      actions.push({
        id: 'monitor-risk',
        label: `Surveiller les ${kpis.aRisque} site${kpis.aRisque > 1 ? 's' : ''} à risque`,
        impact: null,
        path: '/conformite',
      });
    }
    if (alertsCount > 0 && actions.length < 3) {
      actions.push({
        id: 'treat-alerts',
        label: `Traiter les ${alertsCount} alerte${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''}`,
        impact: null,
        path: '/notifications',
      });
    }
    // Fill with opportunities if room
    for (const opp of opportunities) {
      if (actions.length >= 3) break;
      actions.push({
        id: opp.id,
        label: `Lancer ${opp.label.charAt(0).toLowerCase()}${opp.label.slice(1)}`,
        impact: null,
        path: opp.path,
      });
    }
    return actions.slice(0, 3);
  }, [kpis, alertsCount, opportunities]);

  // ── V3 final : scope label ──
  const scopeType = isSingleSite ? 'site' : 'groupe';
  const scopeText = isSingleSite
    ? `Cockpit site · ${singleSite?.nom || ''}`
    : `Cockpit groupe · ${kpis.total} site${kpis.total > 1 ? 's' : ''}`;

  // V18-B: guard — don't show empty state while sites are loading
  if (sitesLoading) {
    return (
      <PageShell icon={FileText} title="Vue exécutive" subtitle={<ScopeSummary />}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonTable rows={5} cols={5} />
      </PageShell>
    );
  }

  return (
    <PageShell icon={FileText} title="Vue exécutive" subtitle={<ScopeSummary />}>
      {/* ── Error banner ── */}
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            getNotificationsSummary(org?.id, scopedSites.length === 1 ? scopedSites[0]?.id : null)
              .then((data) =>
                setAlertsCount((data?.by_severity?.critical || 0) + (data?.by_severity?.warn || 0))
              )
              .catch(() => setAlertsCount(0));
          }}
        />
      )}

      {/* ═══════════ SCOPE INDICATOR ═══════════ */}
      <div
        className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${
          scopeType === 'site' ? 'bg-blue-50 border-blue-200' : 'bg-indigo-50 border-indigo-200'
        }`}
      >
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            scopeType === 'site' ? 'bg-blue-100' : 'bg-indigo-100'
          }`}
        >
          <FileText
            size={14}
            className={scopeType === 'site' ? 'text-blue-600' : 'text-indigo-600'}
          />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {scopeType === 'site' ? 'Cockpit site' : 'Cockpit groupe'}
            <span className="text-xs text-gray-400 ml-2 font-normal">
              Dernière analyse :{' '}
              {new Date().toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </p>
          <p className="text-xs text-gray-500">
            {scopeType === 'site'
              ? singleSite?.nom || ''
              : `${kpis.total} site${kpis.total > 1 ? 's' : ''} dans le périmètre`}
          </p>
        </div>
      </div>

      {/* Expert mode indicator */}
      {isExpert && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-50 border border-violet-200 rounded-lg w-fit">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
          <span className="text-xs font-medium text-violet-700">
            Mode expert activé — détails techniques visibles
          </span>
        </div>
      )}

      {/* ═══════════ ZONE 1 : PRIORITÉ #1 (radical) ═══════════ */}
      <div
        className={`rounded-xl border-l-4 p-5 cursor-pointer hover:shadow-md transition ${
          priority1.type === 'critical'
            ? 'bg-red-50 border-red-500'
            : priority1.type === 'warning'
              ? 'bg-amber-50 border-amber-500'
              : priority1.type === 'info'
                ? 'bg-blue-50 border-blue-500'
                : 'bg-green-50 border-green-500'
        }`}
        onClick={() => navigate(priority1.cta.path)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p
              className={`text-base font-semibold ${
                priority1.type === 'critical'
                  ? 'text-red-900'
                  : priority1.type === 'warning'
                    ? 'text-amber-900'
                    : priority1.type === 'info'
                      ? 'text-blue-900'
                      : 'text-green-900'
              }`}
            >
              {priority1.title}
            </p>
            <div className="flex items-center gap-3 mt-1.5 text-sm">
              {priority1.impact && (
                <span className="font-medium text-red-700">{priority1.impact}</span>
              )}
              {priority1.deadline && <span className="text-gray-600">{priority1.deadline}</span>}
            </div>
          </div>
          <Button
            size="sm"
            variant="primary"
            onClick={(e) => {
              e.stopPropagation();
              navigate(priority1.cta.path);
            }}
          >
            {priority1.cta.label} <ArrowRight size={14} />
          </Button>
        </div>
      </div>

      {/* ═══════════ ZONE 2 : KPI DÉCIDEUR (4 tiles, compact) ═══════════ */}
      <div data-tour="step-1">
        <ExecutiveKpiRow
          kpis={executiveKpis}
          onNavigate={navigate}
          onEvidence={setEvidenceOpen}
          isExpert={isExpert}
          scoreTrend={scoreTrend}
        />
      </div>

      {/* Single-site compact row (intégré dans zone 2, pas empilé) */}
      {isSingleSite && singleSite && (
        <div className="flex items-center gap-6 px-4 py-3 bg-gray-50 rounded-lg text-sm">
          <div className="flex items-center gap-2">
            <StatusDot status={getStatusInfo(singleSite.statut_conformite).dot} />
            <span className="text-gray-700">
              {getStatusInfo(singleSite.statut_conformite).label}
            </span>
          </div>
          <div className="text-gray-500">
            Risque :{' '}
            <span className="font-medium text-gray-900">
              {singleSite.risque_eur > 0
                ? `${singleSite.risque_eur.toLocaleString('fr-FR')} €`
                : '0 €'}
            </span>
          </div>
          <div className="text-gray-500">
            Conso :{' '}
            <span className="font-medium text-gray-900">
              {singleSite.conso_kwh_an > 0 ? `${fmtKwh(singleSite.conso_kwh_an)}/an` : '—'}
            </span>
          </div>
          <div className="text-gray-500">
            Surface :{' '}
            <span className="font-medium text-gray-900">
              {singleSite.surface_m2 ? `${singleSite.surface_m2.toLocaleString('fr-FR')} m²` : '—'}
            </span>
          </div>
        </div>
      )}

      {/* ═══════════ ZONE 3 : ACTIONS (3 max, verbes explicites) ═══════════ */}
      {topActions.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
            Actions recommandées
          </h3>
          {topActions.map((action) => (
            <div
              key={action.id}
              className="flex items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
              onClick={() => navigate(action.path)}
            >
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-800">{action.label}</span>
                {action.impact && (
                  <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded">
                    {action.impact}
                  </span>
                )}
              </div>
              <ArrowRight size={14} className="text-gray-400" />
            </div>
          ))}
        </div>
      )}

      {/* ═══════════ ZONE 4 : ANALYSE DÉTAILLÉE (repliée) ═══════════ */}
      <div className="flex justify-center pt-2">
        <button
          onClick={() => setShowDetail((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition"
        >
          {showDetail ? 'Masquer le détail' : 'Analyse détaillée'}
          <svg
            className={`w-4 h-4 transition-transform ${showDetail ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {showDetail && (
        <div className="space-y-4">
          {/* Impact & Décision */}
          <ImpactDecisionPanel kpis={kpis} />

          {/* Market context */}
          <MarketContextCompact marketContext={marketContext} onNavigate={navigate} />

          {/* Top Sites (multi-site only) */}
          {!isSingleSite && <TopSitesCard topSites={topSites} onNavigate={navigate} />}

          {/* Module Launchers (replié) */}
          <ModuleLaunchers kpis={kpis} isExpert={isExpert} onNavigate={navigate} />

          {/* Données & connexions */}
          <EssentialsRow
            kpis={kpis}
            sites={scopedSites}
            onOpenMaturite={() => setShowMaturiteModal(true)}
            onNavigate={navigate}
            consoSource={consoSource}
          />

          {/* Data Activation — masqué si tout activé */}
          {kpis.couvertureDonnees < 100 && <DataActivationPanel kpis={kpis} />}

          {/* Expert only */}
          {isExpert && opportunities.length > 0 && (
            <OpportunitiesCard opportunities={opportunities} onNavigate={navigate} />
          )}
          {isExpert && <DataQualityWidget />}
          {isExpert && !consistency.ok && <ConsistencyBanner issues={consistency.issues} />}
        </div>
      )}

      {/* Portfolio tabs + Sites Table — inside detail zone */}
      {showDetail && !portefeuille && !isSingleSite && ptfWithCounts.length > 1 && (
        <Tabs
          tabs={ptfTabs}
          active={activePtf}
          onChange={(id) => {
            setActivePtf(id);
            setSitePage(1);
            setSiteSearch('');
          }}
        />
      )}

      {showDetail && !isSingleSite && (
        <Card>
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-gray-800">
              <Explain term="distribution_sites">Sites</Explain> ({filteredSites.length})
            </h3>
            <div className="relative w-64">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                type="text"
                placeholder="Rechercher un site…"
                value={siteSearch}
                onChange={(e) => {
                  setSiteSearch(e.target.value);
                  setSitePage(1);
                }}
                className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
                  focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {filteredSites.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={Search}
                title="Aucun site trouvé"
                text={
                  siteSearch
                    ? 'Essayez un autre terme de recherche.'
                    : 'Aucun site dans ce périmètre.'
                }
                ctaLabel={siteSearch ? 'Effacer' : undefined}
                onCta={siteSearch ? () => setSiteSearch('') : undefined}
              />
            </div>
          ) : (
            <>
              <Table>
                <Thead>
                  <tr>
                    <Th
                      sortable
                      sorted={siteSort.col === 'nom' ? siteSort.dir : ''}
                      onSort={() => handleSiteSort('nom')}
                    >
                      Site
                    </Th>
                    <Th
                      sortable
                      sorted={siteSort.col === 'ville' ? siteSort.dir : ''}
                      onSort={() => handleSiteSort('ville')}
                    >
                      Ville
                    </Th>
                    <Th
                      sortable
                      sorted={siteSort.col === 'surface_m2' ? siteSort.dir : ''}
                      onSort={() => handleSiteSort('surface_m2')}
                    >
                      Surface
                    </Th>
                    <Th
                      sortable
                      sorted={siteSort.col === 'statut_conformite' ? siteSort.dir : ''}
                      onSort={() => handleSiteSort('statut_conformite')}
                    >
                      <Explain term="statut_conformite">Conformité</Explain>
                    </Th>
                    <Th
                      sortable
                      sorted={siteSort.col === 'risque_eur' ? siteSort.dir : ''}
                      onSort={() => handleSiteSort('risque_eur')}
                      className="text-right"
                    >
                      Risque
                    </Th>
                    {isExpert && (
                      <Th
                        sortable
                        sorted={siteSort.col === 'conso_kwh_an' ? siteSort.dir : ''}
                        onSort={() => handleSiteSort('conso_kwh_an')}
                        className="text-right"
                      >
                        Conso kWh/an
                      </Th>
                    )}
                    <Th className="w-10" />
                  </tr>
                </Thead>
                <Tbody>
                  {sitesPageData.map((site) => {
                    const si = getStatusInfo(site.statut_conformite);
                    return (
                      <Tr
                        key={site.id}
                        onClick={() => navigate(`/sites/${site.id}`)}
                        className="group cursor-pointer hover:bg-blue-50/40"
                      >
                        <Td>
                          <div className="font-medium text-gray-900">{site.nom}</div>
                          <div className="text-xs text-gray-400">{site.usage}</div>
                        </Td>
                        <Td>{site.ville}</Td>
                        <Td>
                          {site.surface_m2?.toLocaleString('fr-FR')}
                          {'\u00A0'}m²
                        </Td>
                        <Td>
                          <div className="flex items-center gap-1.5">
                            <StatusDot status={si.dot} />
                            <span className="text-xs text-gray-600">{si.label}</span>
                          </div>
                        </Td>
                        <Td className="text-right text-sm font-medium">
                          {site.risque_eur > 0 ? (
                            <span className="text-amber-700">
                              {site.risque_eur.toLocaleString('fr-FR')} €
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </Td>
                        {isExpert && (
                          <Td className="text-right text-gray-600">
                            {site.conso_kwh_an > 0
                              ? site.conso_kwh_an.toLocaleString('fr-FR')
                              : '-'}
                          </Td>
                        )}
                        <Td className="text-right">
                          <ArrowRight
                            size={14}
                            className="text-gray-300 group-hover:text-gray-500 transition"
                          />
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
              <div className="flex items-center justify-end px-4 py-2 border-t border-gray-100">
                <Pagination
                  page={sitePage}
                  pageSize={sitePageSize}
                  total={filteredSites.length}
                  onChange={setSitePage}
                />
              </div>
            </>
          )}
        </Card>
      )}

      {/* Maturité de pilotage — détail modal */}
      <Modal
        open={showMaturiteModal}
        onClose={() => setShowMaturiteModal(false)}
        title="Maturité de pilotage"
      >
        <div className="space-y-5">
          <p className="text-sm text-gray-600">
            Pourcentage de sites avec données à jour, obligations suivies et plan d'action actif
            (pondéré).
          </p>

          <div className="text-center">
            <div className="relative w-24 h-24 mx-auto">
              <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                <circle
                  cx="18"
                  cy="18"
                  r="15.5"
                  fill="none"
                  className="stroke-gray-200"
                  strokeWidth="2.5"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="15.5"
                  fill="none"
                  className="stroke-blue-500"
                  strokeWidth="2.5"
                  strokeDasharray={`${kpis.readinessScore * 0.975} 100`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-900">
                {kpis.readinessScore}%
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              <Explain term="effort_score">Score global périmètre</Explain>
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Couverture données</span>
                <span className="text-xs text-gray-400">
                  poids : {Math.round(READINESS_WEIGHTS.data * 100)}%
                </span>
              </div>
              <Progress value={kpis.couvertureDonnees} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">
                {kpis.couvertureDonnees}% des sites avec consommation renseignée
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Suivi conformité</span>
                <span className="text-xs text-gray-400">
                  poids : {Math.round(READINESS_WEIGHTS.conformity * 100)}%
                </span>
              </div>
              <Progress value={kpis.suiviConformite} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">
                {kpis.suiviConformite}% des sites conformes
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Actions actives</span>
                <span className="text-xs text-gray-400">
                  poids : {Math.round(READINESS_WEIGHTS.actions * 100)}%
                </span>
              </div>
              <Progress value={kpis.actionsActives} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">
                {kpis.actionsActives}% taux d'actions en cours
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              setShowMaturiteModal(false);
              navigate(toActionsList());
            }}
            className="w-full text-center py-2.5 bg-gray-50 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-100 transition"
          >
            Voir les actions
          </button>
        </div>
      </Modal>

      {/* ── Evidence Drawer ("Pourquoi ce chiffre ?") ── */}
      <EvidenceDrawer
        open={!!evidenceOpen}
        onClose={() => setEvidenceOpen(null)}
        evidence={evidenceOpen ? evidenceMap[evidenceOpen] : null}
      />

      {/* ── Onboarding spotlight (C.2b) ── */}
      <DemoSpotlight />
    </PageShell>
  );
};

export default Cockpit;
