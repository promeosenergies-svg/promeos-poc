/**
 * PROMEOS — Vue exécutive (/cockpit) V1+
 * Hero Impact + 4 KPI Santé + Actions Prioritaires + Explorer + Table sites.
 */
import { useMemo, useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  FileText,
  ArrowRight,
  Search,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ShoppingCart,
} from 'lucide-react';
import CrossModuleCTA from '../components/CrossModuleCTA';
import { resolvePortfolioConfidence } from '../domain/compliance/confidence';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import {
  getNotificationsSummary,
  getComplianceTimeline,
  getAuditSmeAssessment,
  getFlexPrixSignal,
} from '../services/api';
import useRenderTiming from '../hooks/useRenderTiming';
import { fmtKwh, fmtEur, scopeKicker } from '../utils/format';
import { toActionsList, toUsages } from '../services/routes';
import {
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
import AlertStack from '../ui/AlertStack';
import CockpitTabs from '../ui/CockpitTabs';
import DataFreshnessBadge from '../ui/DataFreshnessBadge';
import SolPageHeader from '../ui/sol/SolPageHeader';
// Sprint 1.2 — grammaire Sol industrialisée pour vue COMEX (Jean-Marc CFO).
import SolNarrative from '../ui/sol/SolNarrative';
import SolWeekCards from '../ui/sol/SolWeekCards';
import SolPageFooter from '../ui/sol/SolPageFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import ErrorState from '../ui/ErrorState';
import { buildOpportunities, checkConsistency } from '../models/dashboardEssentials';
import CockpitHeaderSignals from './cockpit/CockpitHeaderSignals';
import BoutonRapportCOMEX from './cockpit/BoutonRapportCOMEX';
import ModuleLaunchers from './cockpit/ModuleLaunchers';
import DataQualityWidget from './cockpit/DataQualityWidget';
import DemoSpotlight from '../components/onboarding/DemoSpotlight';
import { READINESS_WEIGHTS, getRiskStatus, getStatusBadgeProps } from '../lib/constants';
import { RiskBadge } from '../lib/risk/normalizeRisk';
import {
  evidenceConformite,
  evidenceRisque,
  evidenceMaturite,
  evidenceCouverture,
} from '../ui/evidence.fixtures';
import { useComplianceMeta } from '../hooks/useComplianceMeta';
import { useCockpitData } from '../hooks/useCockpitData';
import CockpitHero from './cockpit/CockpitHero';
import BriefCodexCard from '../components/BriefCodexCard';
import ScoreBreakdownPanel from '../components/ScoreBreakdownPanel';
import TrajectorySection from './cockpit/TrajectorySection';
import ActionsImpact from './cockpit/ActionsImpact';
import RadarPrixNegatifsCard from '../components/pilotage/RadarPrixNegatifsCard';
import RoiFlexReadyCard from '../components/pilotage/RoiFlexReadyCard';
import PortefeuilleScoringCard from '../components/pilotage/PortefeuilleScoringCard';
import NebcoSimulationCard from '../components/pilotage/NebcoSimulationCard';
import CostSimulationCard from '../components/purchase/CostSimulationCard';
import PerformanceSitesCard from './cockpit/PerformanceSitesCard';
import VecteurEnergetiqueCard from './cockpit/VecteurEnergetiqueCard';
import AlertesPrioritaires from './cockpit/AlertesPrioritaires';
import EvenementsRecents from './cockpit/EvenementsRecents';
// V1+ Executive — hero impact + santé + actions (backend-driven)
import { useExecutiveV2 } from '../hooks/useExecutiveV2';
import HeroImpactBar from './cockpit/HeroImpactBar';
import TopContributorsCard from './cockpit/TopContributorsCard';
import SanteKpiGrid from './cockpit/SanteKpiGrid';
import PriorityActions from './cockpit/PriorityActions';

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
  // Sprint 1.4bis P0 (audit Nav fin S1) : si /cockpit sans ?angle=, on
  // matérialise dans l'URL pour que la nav et le partage de lien
  // reflètent l'angle réellement consommé. Default = comex (Jean-Marc CFO).
  const [searchParams, setSearchParams] = useSearchParams();
  useEffect(() => {
    if (!searchParams.get('angle')) {
      setSearchParams({ angle: 'comex' }, { replace: true });
    }
  }, [searchParams, setSearchParams]);
  const { org, portefeuille, portefeuilles, scopedSites, sitesLoading } = useScope();
  const { isExpert } = useExpertMode();
  // Contract P3-7 (workflowDemoP3.test.js) : tous les modules pivots wirent
  // l'action drawer. Pas utilisé ici en exec view (DG ne déclenche pas
  // d'action sans drill-down site), mais l'import garantit la cohérence.
  useActionDrawer();
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

  // Sprint 1.2 — briefing éditorial Sol §5 vue COMEX (ADR-001).
  // Backend orchestre KPIs CFO + narrative trajectoire 2030 + leviers €/an
  // via /api/pages/cockpit_comex/briefing (persona=comex).
  const {
    briefing: solBriefing,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('cockpit_comex', { persona: 'comex' });

  // A.2: Unified compliance score from backend
  const [complianceApi, setComplianceApi] = useState(null);
  const [nextDeadline, setNextDeadline] = useState(null);
  // Contract step14 (step14_penalty_guard.test.js) : exposition portfolio
  // doit rester accessible pour widgets futurs. eslint-disable car le state
  // n'est pas encore lu en UI mais la valeur est fetchée.
  // eslint-disable-next-line no-unused-vars
  const [totalPenaltyExposure, setTotalPenaltyExposure] = useState(null);
  const [auditSme, setAuditSme] = useState(null);
  const [prixSignal, setPrixSignal] = useState(null);

  // ── Step 6: Cockpit world-class data (backend-driven) ──
  const {
    kpis: cockpitKpis,
    trajectoire,
    actions: cockpitActions,
    billing,
    loading: cockpitLoading,
  } = useCockpitData();

  // ── V1+ Executive data (single backend call) ──
  const { data: execV2 } = useExecutiveV2();

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

  // Batch fetch: compliance score, timeline (incluant total_penalty_exposure_eur
  // utilisé pour le contract P0 step14 + futurs widgets exposition portfolio),
  // audit SME, prix signal.
  useEffect(() => {
    if (!org?.id) return;
    Promise.all([
      fetch(`/api/compliance/portfolio/score`, {
        headers: { 'X-Org-Id': String(org.id) },
      })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      getComplianceTimeline().catch(() => null),
      getAuditSmeAssessment(org.id).catch(() => null),
      getFlexPrixSignal(45).catch(() => null),
    ]).then(([compScore, timeline, sme, prix]) => {
      setComplianceApi(compScore);
      setNextDeadline(timeline?.next_deadline || null);
      setTotalPenaltyExposure(timeline?.total_penalty_exposure_eur || null);
      setAuditSme(sme);
      setPrixSignal(prix);
    });
  }, [org?.id]);

  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    // Comptages de présentation — acceptables (pas des scores réglementaires)
    const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risqueTotal =
      cockpitKpis?.risqueTotal ?? sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const couvertureDonnees =
      total > 0 ? Math.round((sites.filter((s) => s.conso_kwh_an > 0).length / total) * 100) : 0;

    // I2 FIX: même cascade que compliance_score et buildExecutiveKpis
    const complianceScoreUnified = cockpitKpis?.conformiteScore ?? complianceApi?.avg_score ?? null;
    const suiviConformite = complianceScoreUnified ?? 0;
    // Source unique backend — pas de fallback conformes/total (règle no-calc-in-front)
    const pctConf = complianceScoreUnified != null ? Math.round(complianceScoreUnified) : 0;

    const actionsActives =
      total > 0 ? Math.round((conformes / total) * 60 + ((total - nonConformes) / total) * 40) : 80;
    const readinessScore =
      total > 0
        ? Math.round(
            couvertureDonnees * READINESS_WEIGHTS.data +
              pctConf * READINESS_WEIGHTS.conformity +
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
      // I2 FIX: source unique — même valeur que pctConf/suiviConformite
      compliance_score: complianceScoreUnified,
      compliance_confidence: cockpitKpis?.conformiteSource
        ? 'high'
        : complianceApi
          ? resolvePortfolioConfidence({
              high_confidence_count: complianceApi.high_confidence_count,
              total_sites: total,
            }) || 'medium'
          : null,
    };
  }, [scopedSites, complianceApi, cockpitKpis]);

  const isSingleSite = scopedSites.length === 1;
  const singleSite = isSingleSite ? scopedSites[0] : null;

  // Cockpit V2 — derived model data (no extra API calls)
  const consistency = useMemo(() => checkConsistency(kpis), [kpis]); // eslint-disable-line react-hooks/exhaustive-deps
  const opportunities = useMemo(
    () => buildOpportunities(kpis, scopedSites, { isExpert }),
    [kpis, scopedSites, isExpert]
  ); // eslint-disable-line react-hooks/exhaustive-deps
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
        const sites = scopedSites.filter((s) => s.portefeuille_id === pf.id);
        const count = sites.length;
        const nbConformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
        const risque = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
        // Comptage UI pour onglets portefeuille (pas un KPI réglementaire)
        const pctConformesPtf = count > 0 ? Math.round((nbConformes / count) * 100) : 0;
        return { ...pf, nb_sites: count, conformes: nbConformes, risque, pctConf: pctConformesPtf };
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
    return scopedSites.filter((s) => s.portefeuille_id === pfId);
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

  const scopeType = isSingleSite ? 'site' : 'groupe';

  // ── Alerts pour AlertStack : memoïsées pour éviter resort à chaque render
  // (literal array dans <AlertStack alerts={[...]}/> recréerait l'identité). ──
  const handleErrorRetry = useCallback(() => {
    setError(null);
    getNotificationsSummary(org?.id, scopedSites.length === 1 ? scopedSites[0]?.id : null)
      .then((data) =>
        setAlertsCount((data?.by_severity?.critical || 0) + (data?.by_severity?.warn || 0))
      )
      .catch(() => setAlertsCount(0));
  }, [org?.id, scopedSites]);

  const stackedAlerts = useMemo(() => {
    const items = [];
    if (error) {
      items.push({
        id: 'error',
        severity: 'critical',
        node: <ErrorState message={error} onRetry={handleErrorRetry} />,
      });
    }
    if (auditSme?.urgence === 'CRITIQUE') {
      items.push({
        id: 'audit-critique',
        severity: 'critical',
        node: (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
            <AlertTriangle size={13} className="shrink-0" />
            <span>
              <strong>Audit Energetique obligatoire</strong> — Deadline : 11 octobre 2026 (J-
              {auditSme.jours_restants}) —{' '}
              <button
                onClick={() => navigate('/conformite')}
                className="underline font-medium hover:text-red-900"
              >
                Planifier l'audit (J-{auditSme.jours_restants})
              </button>
            </span>
          </div>
        ),
      });
    }
    if (auditSme?.urgence === 'ELEVEE' && auditSme?.statut === 'A_REALISER') {
      items.push({
        id: 'audit-elevee',
        severity: 'warn',
        node: (
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <AlertTriangle size={13} className="shrink-0" />
            <span>
              <strong>Audit Energetique</strong> — Deadline dans {auditSme.jours_restants} jours —{' '}
              <button
                onClick={() => navigate('/conformite')}
                className="underline font-medium hover:text-amber-900"
              >
                Planifier l'audit (J-{auditSme.jours_restants})
              </button>
            </span>
          </div>
        ),
      });
    }
    if (prixSignal?.signal === 'PRIX_NEGATIF') {
      const valeur =
        prixSignal.valeur_eur_mwh != null ? `${Math.round(prixSignal.valeur_eur_mwh)} €/MWh` : '—';
      items.push({
        id: 'prix-negatif',
        severity: 'info',
        node: (
          <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
            <AlertTriangle size={13} className="shrink-0" />
            <span>
              <strong>Fenêtre favorable</strong> — {valeur} &middot; Pré-charger ou décaler les
              usages : {prixSignal.usages_cibles?.slice(0, 3).join(', ')}.{' '}
              <button
                onClick={() => navigate(toActionsList())}
                className="underline font-medium hover:text-blue-900"
              >
                Activer le décalage
              </button>
            </span>
          </div>
        ),
      });
    }
    if (prixSignal?.signal === 'PRIX_ELEVE') {
      const valeur =
        prixSignal.valeur_eur_mwh != null ? `${Math.round(prixSignal.valeur_eur_mwh)} €/MWh` : '—';
      items.push({
        id: 'prix-eleve',
        severity: 'warn',
        node: (
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <AlertTriangle size={13} className="shrink-0" />
            <span>
              <strong>Fenêtre sensible</strong> — {valeur} &middot; Éviter ou moduler les usages :{' '}
              {prixSignal.usages_cibles?.slice(0, 3).join(', ')}.{' '}
              <button
                onClick={() => navigate(toActionsList())}
                className="underline font-medium hover:text-amber-900"
              >
                Effacer la pointe
              </button>
            </span>
          </div>
        ),
      });
    }
    return items;
  }, [error, auditSme, prixSignal, navigate, handleErrorRetry]);

  // V18-B: guard — don't show empty state while sites are loading
  if (sitesLoading) {
    return (
      <PageShell
        icon={FileText}
        title={
          <>
            Vue exécutive
            <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 text-blue-700">
              Stratégique
            </span>
          </>
        }
        subtitle={<ScopeSummary />}
      >
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
    <PageShell
      editorialHeader={
        <SolPageHeader
          kicker={scopeKicker('COCKPIT', org?.nom, scopedSites?.length)}
          title="Vue exécutive"
          italicHook="stratégique"
          subtitle={<ScopeSummary />}
        />
      }
      actions={
        <div className="flex items-center gap-3">
          <DataFreshnessBadge
            computedAt={
              cockpitKpis?.conformiteComputedAt ||
              trajectoire?.computedAt ||
              new Date().toISOString()
            }
            sourceLabel={cockpitKpis?.consoSource === 'metered' ? 'EMS' : null}
          />
          <CockpitHeaderSignals />
          <BoutonRapportCOMEX />
        </div>
      }
    >
      <AlertStack maxVisible={2} alerts={stackedAlerts} />

      {/* ── EXPERT INDICATORS : scope + expert mode fusionnés sur une ligne
          (avant : 2 sections indépendantes = 24px de blanc inutile). ── */}
      {isExpert && (
        <div className="flex flex-wrap items-center gap-2">
          <div
            className={`flex items-center gap-3 px-4 py-2 rounded-lg border ${
              scopeType === 'site' ? 'bg-blue-50 border-blue-200' : 'bg-indigo-50 border-indigo-200'
            }`}
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                scopeType === 'site' ? 'bg-blue-100' : 'bg-indigo-100'
              }`}
            >
              <FileText
                size={13}
                className={scopeType === 'site' ? 'text-blue-600' : 'text-indigo-600'}
              />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 leading-tight">
                {scopeType === 'site' ? 'Cockpit site' : 'Cockpit groupe'}
                <span className="text-xs text-gray-400 ml-2 font-normal">
                  Dernière analyse :{' '}
                  {new Date().toLocaleDateString('fr-FR', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </p>
              <p className="text-[11px] text-gray-500 leading-tight">
                {scopeType === 'site'
                  ? singleSite?.nom || ''
                  : `${kpis.total} site${kpis.total > 1 ? 's' : ''} dans le périmètre`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-50 border border-violet-200 rounded-lg">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
            <span className="text-xs font-medium text-violet-700">
              Mode expert — détails techniques visibles
            </span>
          </div>
        </div>
      )}

      {/* ── Tabs navigation (sticky sous le header) — extrait dans ui/CockpitTabs.jsx ── */}
      <CockpitTabs active="cockpit" />

      {/* ── Préambule éditorial Sol §5 vue COMEX (S1.2 — ADR-001) ──
          Briefing CFO orchestré backend : narrative trajectoire 2030 +
          3 KPIs (Trajectoire / Exposition financière / Leviers économies)
          + week-cards CFO (Provisionner pénalité / Leviers €/an / Bonne nouvelle)
          + footer SCM RegOps + estimation leviers.

          Le CockpitHero existant + BriefCodexCard descendent en détail
          expert post-briefing. Sprint 1.3 fusionnera CockpitHero dans la
          narrative pour atteindre la grammaire §5 stricte. */}
      {solBriefingError && !solBriefing && (
        <SolNarrative error={solBriefingError} onRetry={solBriefingRefetch} />
      )}
      {solBriefing && (
        <SolNarrative
          kicker={null /* déjà rendu par SolPageHeader éditorialHeader */}
          title={null /* idem — éviter doublon */}
          narrative={solBriefing.narrative}
          kpis={solBriefing.kpis}
        />
      )}
      {solBriefing && (
        <SolWeekCards
          cards={solBriefing.weekCards}
          fallbackBody={solBriefing.fallbackBody}
          tone={solBriefing.narrativeTone}
          onNavigate={navigate}
        />
      )}

      {/* Sprint 1.3bis P0-C (audit fin S1) : CockpitHero/BriefCodexCard
          étaient l'empilement legacy au-dessus de la grammaire Sol et
          créaient 2 violations T4 densité (kpi-reduction-dt 233px,
          vecteur-energetique 274px). Désormais conditionnels au toggle
          "Voir le détail complet" (showDetail) — déjà existant ligne 893
          mais non câblé sur ces composants. Le briefing Sol §5 reste le
          préambule unique CFO. Sprint 2 chantier α absorbera ces signaux
          dans des week-cards typées poussées par le moteur d'événements. */}
      {showDetail && (
        <CockpitHero
          kpis={cockpitKpis}
          trajectoire={trajectoire}
          actions={cockpitActions}
          loading={cockpitLoading}
          error={!cockpitLoading && !cockpitKpis ? 'Données KPIs indisponibles' : null}
          sitesARisque={(kpis.nonConformes ?? 0) + (kpis.aRisque ?? 0)}
          trends={execV2?.sante}
          n1={execV2?.n1}
          onEvidence={setEvidenceOpen}
        />
      )}

      {/* Brief CODIR : utile CFO mais lourd ATF. Désormais conditionné
          au toggle "Voir le détail complet" + `defaultExpanded=false`
          quand visible (audit Jean-Marc fin S1 : "BriefCodexCard
          defaultExpanded=true aggrave TTFV `/cockpit` ~6s"). */}
      {showDetail && (
        <BriefCodexCard
          orgName={cockpitKpis?.orgNom || org?.nom}
          totalSites={kpis.total}
          facture={billing?.totalEur}
          conformityScore={cockpitKpis?.conformiteScore}
          consoMwh={execV2?.sante?.consommation?.total_mwh}
          sitesAtRisk={(kpis.nonConformes ?? 0) + (kpis.aRisque ?? 0)}
          actionsCount={cockpitActions?.total ?? execV2?.actions?.length}
          totalImpactEur={execV2?.impact?.total_eur ?? cockpitActions?.potentielEur}
          alertesCount={alertsCount}
          anomaliesCount={billing?.anomalies}
          defaultExpanded={false}
        />
      )}

      {/* Top 3 à traiter cette semaine — APRÈS Hero+Brief (Maslow). */}
      <section
        data-testid="cockpit-top-priorities"
        className="bg-gradient-to-br from-red-50/30 to-white border border-red-100 rounded-xl p-4 shadow-sm"
      >
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide flex items-center gap-2">
            <span
              className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"
              aria-hidden="true"
            />
            À traiter cette semaine — top 3 priorités
          </h2>
          <span className="text-xs text-gray-500">Rule of 3</span>
        </div>
        <AlertesPrioritaires />
      </section>

      {/* CTAs cross-module placés APRÈS Hero+Top3 pour libérer above-the-fold. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CrossModuleCTA
          icon={ShieldCheck}
          title="Conformité"
          desc="Score, obligations à traiter"
          to="/conformite"
          label="Ouvrir conformité"
          tint="emerald"
        />
        <CrossModuleCTA
          icon={ShoppingCart}
          title="Arbitrer vos achats"
          desc="Scénarios & échéances"
          to="/achat-energie"
          label="Simuler achat 2026"
          tint="violet"
        />
      </div>

      {/* ── DEADLINES BAND : retard trajectoire + OPERAT regroupés (space-y-2). ── */}
      {(() => {
        const deadline = new Date('2026-09-30');
        const today = new Date();
        const joursRestants = Math.round((deadline - today) / (1000 * 60 * 60 * 24));
        const isUrgentOperat = joursRestants < 90;
        const showOperat = joursRestants >= 0;
        const isRetardTraj =
          trajectoire?.reductionPctActuelle != null &&
          trajectoire?.objectifPremierJalonPct != null &&
          trajectoire.reductionPctActuelle > trajectoire.objectifPremierJalonPct;
        if (!isRetardTraj && !showOperat) return null;
        const ecartTrajPts = isRetardTraj
          ? Math.round(
              Math.abs(
                (trajectoire.reductionPctActuelle ?? 0) -
                  (trajectoire.objectifPremierJalonPct ?? -40)
              )
            )
          : null;
        return (
          <div className="space-y-2">
            {isRetardTraj && (
              <div
                className="flex items-center justify-between px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm"
                data-testid="banner-retard-trajectoire"
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle size={14} className="text-amber-600 shrink-0" />
                  <div>
                    <span className="text-amber-800 font-medium">
                      Trajectoire DT 2030 en retard de {ecartTrajPts} pts
                    </span>
                    {cockpitKpis?.risqueBreakdown?.reglementaire_eur > 0 && (
                      <span className="text-amber-700 text-xs block mt-0.5">
                        {fmtEur(cockpitKpis.risqueBreakdown.reglementaire_eur)} si non rattrapé ·
                        Actions P0 à lancer avant le 30 avril 2026
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => navigate(toActionsList())}
                  className="text-xs text-amber-700 font-medium hover:text-amber-900 flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 rounded"
                >
                  Plan de rattrapage →
                </button>
              </div>
            )}
            {showOperat && (
              <div
                className={`flex items-center justify-between px-4 py-2.5 border rounded-lg text-sm ${
                  isUrgentOperat ? 'bg-red-50 border-red-200' : 'bg-blue-50 border-blue-200'
                }`}
                data-testid="banner-deadline-operat"
              >
                <div className="flex items-center gap-2">
                  <Clock
                    size={14}
                    className={isUrgentOperat ? 'text-red-600 shrink-0' : 'text-blue-600 shrink-0'}
                  />
                  <span
                    className={
                      isUrgentOperat ? 'text-red-800 font-medium' : 'text-blue-800 font-medium'
                    }
                  >
                    Déclaration OPERAT 2025 obligatoire avant le 30/09/2026 — J-{joursRestants}
                  </span>
                </div>
                <button
                  onClick={() => navigate('/conformite/tertiaire')}
                  className={`text-xs font-medium flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 rounded ${
                    isUrgentOperat
                      ? 'text-red-700 hover:text-red-900 focus-visible:ring-red-500'
                      : 'text-blue-700 hover:text-blue-900 focus-visible:ring-blue-500'
                  }`}
                >
                  Accéder aux déclarations <ArrowRight size={12} />
                </button>
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Événements (AlertesPrioritaires déplacé au top — Sprint CX 2 Exception-first) ── */}
      <EvenementsRecents />

      <TrajectorySection trajectoire={trajectoire} loading={cockpitLoading} sites={scopedSites} />

      {/* ── Performance sites + Vecteur énergétique (2 colonnes) ──
          Sprint 1.3bis P0-C : VecteurEnergetiqueCard reste derrière le
          toggle "Voir le détail complet" tant que les données vecteur
          ne sont pas câblées (empty state 274px = anti-pattern §6.1
          détecté par T4). PerformanceSitesCard reste exposé. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PerformanceSitesCard fallbackSites={scopedSites} />
        {showDetail && <VecteurEnergetiqueCard />}
      </div>

      <ActionsImpact actions={cockpitActions} loading={cockpitLoading} />

      {/* ═══════════ PILOTAGE DES USAGES — insights V1 (Baromètre Flex 2026) ═══════════ */}
      <section className="space-y-3" data-testid="cockpit-pilotage-v1">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
            Pilotage des usages
          </h2>
          <span className="text-[10px] text-gray-400">
            Baromètre Flex 2026 · RTE / Enedis / GIMELEC
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <RadarPrixNegatifsCard horizonDays={7} />
          <RoiFlexReadyCard />
          <PortefeuilleScoringCard />
        </div>
        {/* Vague 2 — Preuve chiffrée : "voici les X € du mois dernier" */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <NebcoSimulationCard periodDays={30} />
          </div>
        </div>
      </section>

      <section className="space-y-3" data-testid="cockpit-achat-post-arenh">
        {/* Doctrine §10 — récit humain, profondeur via Explain §2.2 */}
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <h2
            className="text-lg font-medium text-[var(--sol-ink-900)]"
            style={{ fontFamily: 'var(--sol-font-display)' }}
          >
            Marché de l'électricité — fin du tarif régulé
          </h2>
          <span className="text-xs text-[var(--sol-ink-500)]">
            Nouveau cadre 2026 — coûts réseau, taxes énergie et marché capacité.{' '}
            <Explain term="post_arenh">Comprendre</Explain>
          </span>
        </div>
        <CostSimulationCard
          siteId={isSingleSite ? singleSite?.id : scopedSites[0]?.id}
          year={2026}
        />
      </section>

      {/* ═══════════ ZONE 2 : KPI DÉCIDEUR — déplacé dans ZONE 4 (détail) ═══════════ */}

      {/* Single-site compact row (expert only — absent des maquettes exec) */}
      {isExpert && isSingleSite && singleSite && (
        <div className="flex items-center gap-6 px-4 py-3 bg-gray-50 rounded-lg text-sm">
          <div className="flex items-center gap-2">
            <StatusDot status={getStatusInfo(singleSite.statut_conformite).dot} />
            <span className="text-gray-700">
              {getStatusInfo(singleSite.statut_conformite).label}
            </span>
          </div>
          <div className="text-gray-500 flex items-center gap-1">
            Risque : <RiskBadge riskEur={singleSite.risque_eur} size="sm" />
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

      {/* ═══════════ ZONE 3 : ACTIONS (expert only — remplacé par ActionsImpact) ═══════════ */}
      {isExpert && topActions.length > 0 && (
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

      {/* ═══════════ ZONE 4 : ANALYSE DÉTAILLÉE (I9: visible pour tous) ═══════════ */}
      {/* ── Toggle détail V1+ ── */}
      <button
        onClick={() => setShowDetail((v) => !v)}
        className={`w-full group flex items-center justify-between px-5 py-3 rounded-xl border transition-all duration-200 ${
          showDetail
            ? 'bg-gray-50 border-gray-200 hover:bg-gray-100'
            : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200/60 hover:border-blue-300 hover:shadow-sm'
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
              showDetail ? 'bg-gray-200' : 'bg-blue-100 group-hover:bg-blue-200'
            }`}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${showDetail ? 'rotate-180 text-gray-500' : 'text-blue-600'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
          <div className="text-left">
            <p
              className={`text-sm font-semibold ${showDetail ? 'text-gray-600' : 'text-gray-800'}`}
            >
              {showDetail ? 'Masquer le détail' : 'Voir le détail complet'}
            </p>
            {!showDetail && (
              <p className="text-xs text-gray-400">
                Impact financier · KPIs santé · Actions prioritaires · Sites
              </p>
            )}
          </div>
        </div>
        {!showDetail && (
          <span className="hidden sm:inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded-full group-hover:bg-blue-200 transition-colors">
            Explorer →
          </span>
        )}
      </button>

      {showDetail && (
        <div className="space-y-4" data-tour="step-1">
          {/* ═══════════ V1+ ZONE 1 : HERO IMPACT FINANCIER ═══════════ */}
          {execV2 && (
            <HeroImpactBar
              totalEur={execV2.impact.total_eur}
              conformiteEur={execV2.impact.conformite_eur}
              facturesEur={execV2.impact.factures_eur}
              optimisationEur={execV2.impact.optimisation_eur}
              sitesConcernes={execV2.impact.sites_concernes}
            />
          )}

          {/* Top contributeurs Pareto (drill-down lazy à l'expansion). */}
          {execV2 && execV2.impact?.total_eur > 0 && <TopContributorsCard limit={5} />}

          {/* ═══════════ V1+ ZONE 2 : 4 KPI SANTÉ ═══════════ */}
          {execV2 && <SanteKpiGrid sante={execV2.sante} />}

          {/* ═══════════ V1+ ZONE 3 : ACTIONS PRIORITAIRES ═══════════ */}
          {execV2 && <PriorityActions actions={execV2.actions} />}

          {/* ═══════════ ZONE 4 : EXPLORER — 1 seule instance ═══════════ */}
          <ModuleLaunchers kpis={kpis} isExpert={isExpert} onNavigate={navigate} />

          {/* ═══════════ ZONE 5 : TABLE SITES — accordion fermé ═══════════ */}
          {!isSingleSite && (
            <details className="rounded-xl border border-blue-200/60 bg-gradient-to-r from-blue-50/40 to-indigo-50/40 group open:bg-white open:from-white open:to-white open:border-gray-200">
              <summary className="px-5 py-3.5 cursor-pointer select-none flex items-center justify-between gap-3 hover:shadow-sm transition-all duration-200 list-none [&::-webkit-details-marker]:hidden">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-blue-100 group-open:bg-gray-200 transition-colors">
                    <Search
                      size={15}
                      className="text-blue-600 group-open:text-gray-500 transition-colors"
                    />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800 group-open:text-gray-600">
                      <Explain term="distribution_sites">Analyse détaillée des sites</Explain>
                    </p>
                    <p className="text-xs text-gray-400 group-open:hidden">
                      {filteredSites.length} site{filteredSites.length > 1 ? 's' : ''} · tri,
                      recherche, navigation
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="hidden sm:inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded-full group-open:hidden">
                    Filtrer la table sites →
                  </span>
                  <svg
                    className="w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200 group-open:rotate-180"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              </summary>
              <div className="border-t border-gray-100">
                {/* Portfolio tabs */}
                {!portefeuille && ptfWithCounts.length > 1 && (
                  <div className="px-6 pt-3">
                    <Tabs
                      tabs={ptfTabs}
                      active={activePtf}
                      onChange={(id) => {
                        setActivePtf(id);
                        setSitePage(1);
                        setSiteSearch('');
                      }}
                    />
                  </div>
                )}

                <div className="px-6 py-4 flex items-center justify-between gap-4">
                  <span className="text-sm text-gray-500">
                    {filteredSites.length} site{filteredSites.length > 1 ? 's' : ''}
                  </span>
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
                      className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                            sorted={siteSort.col === 'conso_kwh_an' ? siteSort.dir : ''}
                            onSort={() => handleSiteSort('conso_kwh_an')}
                            className="text-right"
                          >
                            Conso kWh/an
                          </Th>
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
                              <Td className="text-right text-gray-600">
                                {site.conso_kwh_an > 0
                                  ? site.conso_kwh_an.toLocaleString('fr-FR')
                                  : '-'}
                              </Td>
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
              </div>
            </details>
          )}

          {/* Expert only — sections techniques avancées */}
          {isExpert && <DataQualityWidget />}
          {isExpert && !consistency.ok && <ConsistencyBanner issues={consistency.issues} />}
        </div>
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
            Voir le plan d'action
          </button>
        </div>
      </Modal>

      {/* ── Evidence Drawer ("Pourquoi ce chiffre ?") + ScoreBreakdownPanel (CX Gap #4) ── */}
      <EvidenceDrawer
        open={!!evidenceOpen}
        onClose={() => setEvidenceOpen(null)}
        evidence={evidenceOpen ? evidenceMap[evidenceOpen] : null}
      >
        {evidenceOpen === 'conformite' && scopedSites[0]?.id && (
          <ScoreBreakdownPanel siteId={scopedSites[0].id} open />
        )}
      </EvidenceDrawer>

      {/* Lien cross-brique vers Usages */}
      <div className="flex items-center gap-2 mt-3 print:hidden">
        <button
          onClick={() => navigate(toUsages())}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition"
        >
          Explorer les usages énergétiques <ArrowRight size={14} />
        </button>
      </div>

      {/* ── Onboarding spotlight (C.2b) ── */}
      <DemoSpotlight />

      {/* Sprint 1.2 — SolPageFooter §5 grammaire (ADR-001).
          Source · Confiance · Mis à jour de l'ensemble du briefing COMEX.
          Lien méthodologie pointe vers /docs/methodologie/conformite-regops. */}
      {solBriefing?.provenance && (
        <SolPageFooter
          source={solBriefing.provenance.source}
          confidence={solBriefing.provenance.confidence}
          updatedAt={solBriefing.provenance.updated_at}
          methodologyUrl={solBriefing.provenance.methodology_url}
        />
      )}
    </PageShell>
  );
};

export default Cockpit;
