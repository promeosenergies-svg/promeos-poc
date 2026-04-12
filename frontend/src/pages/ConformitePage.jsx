/**
 * PROMEOS - Conformite (/conformite) V92
 * Cockpit RegOps: 4 tabs (Obligations, Donnees & Qualite, Plan d'execution, Preuves & Rapports).
 * Scope filtering (org/entity/site), empty state reason codes, workflow actions.
 * Sub-components extracted to conformite-tabs/ (V92 split).
 * V101: sections extracted to components/conformite/.
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, Plus, RotateCcw, RefreshCw, Coins, ShoppingCart, Radio } from 'lucide-react';
import { toUsages } from '../services/routes';
import { Button, PageShell, ActiveFiltersBar, Explain } from '../ui';
import ObligationsTab from './conformite-tabs/ObligationsTab';
import DonneesTab from './conformite-tabs/DonneesTab';
import ExecutionTab from './conformite-tabs/ExecutionTab';
import PreuvesTab from './conformite-tabs/PreuvesTab';
import GuidedModeBandeau from './conformite-tabs/GuidedModeBandeau';
import NextBestActionCard from './conformite-tabs/NextBestActionCard';
import {
  computeGuidedSteps,
  computeNextBestAction,
  computeDonneesMetrics,
} from '../models/guidedModeModel';
import Tabs from '../ui/Tabs';
import { useToast } from '../ui/ToastProvider';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { track } from '../services/tracker';
import { RiskBadge } from '../lib/risk/normalizeRisk';
import EmptyState from '../ui/EmptyState';
import ErrorState from '../ui/ErrorState';
import { SkeletonKpi, SkeletonTable } from '../ui/Skeleton';
import { buildWatchlist, buildBriefing, computeHealthState } from '../models/dashboardEssentials';
import { computeObligationProfileTags } from '../models/complianceProfileRules';
import HealthSummary from '../components/HealthSummary';
import CrossModuleCTA from '../components/CrossModuleCTA';
import DossierPrintView from '../components/DossierPrintView';
import RegulatoryTimeline from '../components/compliance/RegulatoryTimeline';
import { REG_LABELS, STATUT_LABELS, COCKPIT_TABS } from '../domain/compliance/complianceLabels.fr';
import {
  getComplianceBundle,
  patchComplianceFinding,
  recomputeComplianceRules,
  getIntakeQuestions,
  resetDb,
  getComplianceTimeline,
  getSegmentationProfile,
  getAuditSmeAssessment,
} from '../services/api';

// V7 — regulation filter map (URL ?regulation=) → list of obligation codes to match
const REGULATION_FILTER_MAP = {
  dt: ['decret_tertiaire_operat', 'decret_tertiaire', 'dt'],
  bacs: ['bacs'],
  aper: ['aper'],
  'audit-sme': ['audit_sme', 'audit_energetique'],
};
const ALLOWED_REGULATION_FILTERS = Object.keys(REGULATION_FILTER_MAP);

// Extracted sub-components
import { DevApiBadge, DevScopeBadge } from '../components/conformite/DevBadges';
import FindingAuditDrawer from '../components/conformite/FindingAuditDrawer';
import ComplianceSummaryBanner from '../components/conformite/ComplianceSummaryBanner';
import ComplianceScoreHeader from '../components/conformite/ComplianceScoreHeader';
import AuditSmeCard from '../components/conformite/AuditSmeCard';
import {
  buildScopeParams,
  parseBundleError,
  computeBacsV2Summary,
  computeScopeLabel,
  isOverdue,
  sitesToObligations,
  sitesToIncentives,
  resolveScopeLabel,
  formatDeadline,
} from '../components/conformite/conformiteUtils';

// Re-export utilities for backward compatibility (tests import from this file)
export {
  resolveScopeLabel,
  buildScopeParams,
  parseBundleError,
  computeBacsV2Summary,
  computeScopeLabel,
  isOverdue,
  formatDeadline,
  sitesToObligations,
  sitesToIncentives,
};
export { DevScopeBadge };

export default function ConformitePage() {
  const { org, scope, scopedSites, portefeuilles, sitesCount, sitesLoading } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const navigate = useNavigate();
  const { openActionDrawer } = useActionDrawer();
  const [proofFiles, setProofFiles] = useState({});
  const [statusFilter, setStatusFilter] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [sitesData, setSitesData] = useState([]);
  const [auditFindingId, setAuditFindingId] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'obligations');
  const rawRegulationFilter = searchParams.get('regulation');
  const regulationFilter = ALLOWED_REGULATION_FILTERS.includes(rawRegulationFilter)
    ? rawRegulationFilter
    : null;
  const tabsRef = useRef(null);
  const [intakeQuestions, setIntakeQuestions] = useState([]);
  const [emptyReason, setEmptyReason] = useState(null);
  const [error, setError] = useState(null);
  const [bundle, setBundle] = useState(null);
  const [dossierSource, setDossierSource] = useState(null);
  const [complianceScore, setComplianceScore] = useState(null); // A.2 unified score
  const [timeline, setTimeline] = useState(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [segProfile, setSegProfile] = useState(null);
  const [auditSme, setAuditSme] = useState(null);

  const loadData = useCallback(() => {
    if (sitesLoading) return; // V18-B: wait for scope to be ready before fetching
    setLoading(true);
    setError(null);
    const scopeParams = buildScopeParams(
      { orgId: org?.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId },
      scopedSites
    );

    getComplianceBundle(scopeParams)
      .then((b) => {
        const err = parseBundleError(b);
        if (err) {
          setError(err);
          return;
        }
        setBundle(b);
        setSummary(b.summary);
        setSitesData(b.sites);
        if (scopedSites.length === 0) setEmptyReason('NO_SITES');
        else if (b.empty_reason_code) setEmptyReason(b.empty_reason_code);
        else setEmptyReason(null);
      })
      .catch((err) => {
        const status = err?.response?.status;
        const base = parseBundleError(null);
        if (status) base.status = status;
        const reqUrl =
          err?.config?.baseURL && err?.config?.url
            ? `${err.config.baseURL}${err.config.url}`
            : null;
        if (reqUrl) base.request_url = reqUrl;
        setError(base);
      })
      .finally(() => setLoading(false));
  }, [org?.id, scope.portefeuilleId, scope.siteId, scopedSites, sitesLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadData();
  }, [loadData]);

  // A.2: Fetch unified compliance score
  useEffect(() => {
    if (sitesLoading || !org?.id) return;
    const isSingleSite = scopedSites.length === 1;
    const url = isSingleSite
      ? `/api/compliance/sites/${scopedSites[0].id}/score`
      : `/api/compliance/portfolio/score`;
    fetch(url, { headers: { 'X-Org-Id': String(org.id) } })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setComplianceScore(data))
      .catch(() => setComplianceScore(null));
  }, [org?.id, scopedSites, sitesLoading]);

  // Step 13: Fetch regulatory timeline
  useEffect(() => {
    if (sitesLoading || !org?.id) return;
    setTimelineLoading(true);
    getComplianceTimeline()
      .then((data) => setTimeline(data))
      .catch(() => setTimeline(null))
      .finally(() => setTimelineLoading(false));
  }, [org?.id, sitesLoading]);

  // V1.3: Fetch segmentation profile for "Adapte a votre profil" badge
  useEffect(() => {
    getSegmentationProfile()
      .then((p) => setSegProfile(p))
      .catch(() => setSegProfile(null));
  }, []);

  // Audit Energetique / SME (Loi 2025-391)
  useEffect(() => {
    if (!org?.id) return;
    getAuditSmeAssessment(org.id)
      .then(setAuditSme)
      .catch(() => setAuditSme(null));
  }, [org?.id]);

  // Load intake questions for Donnees tab
  useEffect(() => {
    if (scopedSites.length > 0) {
      getIntakeQuestions(scopedSites[0].id)
        .then((data) => setIntakeQuestions(data.questions || []))
        .catch(() => setIntakeQuestions([]));
    }
  }, [scopedSites]);

  const obligations = useMemo(() => {
    if (!sitesData.length || !summary) return [];
    return sitesToObligations(sitesData, summary);
  }, [sitesData, summary]);

  // P2 — Seed demo proof files so the Preuves tab shows a realistic cycle
  useEffect(() => {
    if (obligations.length > 0 && Object.keys(proofFiles).length === 0) {
      const seed = {};
      for (const o of obligations) {
        if (o.code === 'decret_tertiaire_operat') {
          // Complete: 2 proofs deposited (matches RULE_EXPECTED_PROOFS DT)
          seed[o.id] = [
            { name: 'Declaration_OPERAT_2025.pdf', date: '15/01/2026' },
            { name: 'Attestation_trajectoire_-40pct.pdf', date: '20/02/2026' },
          ];
        } else if (o.code === 'bacs') {
          // Partial: 1 proof deposited (out of 2 expected)
          seed[o.id] = [{ name: 'Rapport_audit_GTB_2025.pdf', date: '10/12/2025' }];
        }
        // aper: no proof → stays "Manquantes"
      }
      if (Object.keys(seed).length > 0) setProofFiles(seed);
    }
  }, [obligations]); // eslint-disable-line react-hooks/exhaustive-deps

  const incentives = useMemo(() => {
    if (!sitesData.length) return [];
    return sitesToIncentives(sitesData);
  }, [sitesData]);

  const complianceHealth = useMemo(() => {
    if (!bundle || !sitesData.length) return null;
    const nc = sitesData.filter((s) => s.statut_conformite === 'non_conforme').length;
    const ar = sitesData.filter((s) => s.statut_conformite === 'a_risque').length;
    const total = sitesData.length;
    const conformes = sitesData.filter((s) => s.statut_conformite === 'conforme').length;
    const simpleKpis = {
      total,
      conformes,
      nonConformes: nc,
      aRisque: ar,
      risqueTotal: 0,
      couvertureDonnees: 100,
    };
    const wl = buildWatchlist(simpleKpis, sitesData);
    const br = buildBriefing(simpleKpis, wl);
    return computeHealthState({
      kpis: simpleKpis,
      watchlist: wl,
      briefing: br,
      consistency: { ok: true },
      alertsCount: 0,
    });
  }, [bundle, sitesData]);

  const score = useMemo(() => {
    if (!summary)
      return { pct: 0, total: 0, non_conformes: 0, a_risque: 0, conformes: 0, total_impact_eur: 0 };
    // Use unified compliance score (59/100) instead of pct_ok (0%) to avoid contradiction
    const unifiedPct = complianceScore
      ? Math.round(complianceScore.score ?? complianceScore.avg_score ?? 0)
      : summary.pct_ok || 0;
    return {
      pct: unifiedPct,
      total: summary.total_sites || scopedSites?.length || 0,
      non_conformes: summary.sites_nok || 0,
      a_risque: summary.sites_unknown || 0,
      conformes: summary.sites_ok || 0,
      total_impact_eur: 0,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, obligations, complianceScore, scopedSites]);

  const bacsV2Summary = useMemo(() => computeBacsV2Summary(bundle?.bacs_v2), [bundle]);

  const scopeLabel = useMemo(
    () =>
      computeScopeLabel(
        org,
        { siteId: scope.siteId, portefeuilleId: scope.portefeuilleId },
        scopedSites,
        portefeuilles
      ),
    [org, scope.siteId, scope.portefeuilleId, scopedSites, portefeuilles]
  );

  // V1.4: profile tags for obligation cards
  const profileTags = useMemo(
    () => computeObligationProfileTags(obligations, segProfile),
    [obligations, segProfile]
  );

  const sortedObligations = useMemo(() => {
    let list = [...obligations];
    if (regulationFilter) {
      const allowedCodes = REGULATION_FILTER_MAP[regulationFilter] || [];
      list = list.filter((o) =>
        allowedCodes.some((code) => (o.code || '').toLowerCase().includes(code.toLowerCase()))
      );
    }
    if (statusFilter) {
      list = list.filter((o) => o.statut === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (o) =>
          o.regulation.toLowerCase().includes(q) ||
          o.description.toLowerCase().includes(q) ||
          o.code.toLowerCase().includes(q)
      );
    }
    list.sort((a, b) => {
      // 1. Overdue first (never overridden by profile)
      const aOver = isOverdue(a) ? 0 : 1;
      const bOver = isOverdue(b) ? 0 : 1;
      if (aOver !== bOver) return aOver - bOver;
      // 2. Statut metier (never overridden by profile)
      const order = { non_conforme: 0, a_risque: 1, a_qualifier: 2, conforme: 3 };
      const aStatut = order[a.statut] ?? 9;
      const bStatut = order[b.statut] ?? 9;
      if (aStatut !== bStatut) return aStatut - bStatut;
      // 3. V1.4: profile boost WITHIN same group only
      const aBoost = profileTags.get(a.id || a.code)?.priorityBoost || 0;
      const bBoost = profileTags.get(b.id || b.code)?.priorityBoost || 0;
      if (aBoost !== bBoost) return bBoost - aBoost;
      // 4. Stable secondary sort by code
      return (a.code || '').localeCompare(b.code || '');
    });
    return list;
  }, [obligations, statusFilter, searchQuery, profileTags, regulationFilter]);

  const actionableFindings = useMemo(() => {
    return obligations
      .flatMap((o) => o.findings)
      .filter((f) => f.status === 'NOK' || f.status === 'UNKNOWN')
      .filter((f) => f.insight_status !== 'resolved' && f.insight_status !== 'false_positive');
  }, [obligations]);

  // ── Guided Mode + NBA + Donnees metrics ──
  const guidedSteps = useMemo(() => {
    if (isExpert || !sitesData.length) return [];
    return computeGuidedSteps(bundle, sitesData, summary, {
      obligations,
      actionableFindings,
      proofFiles,
      bacsV2Summary,
    });
  }, [
    isExpert,
    bundle,
    sitesData,
    summary,
    obligations,
    actionableFindings,
    proofFiles,
    bacsV2Summary,
  ]);

  const nextBestAction = useMemo(() => {
    if (!sitesData.length) return null;
    return computeNextBestAction(bundle, sitesData, summary, {
      obligations,
      actionableFindings,
      proofFiles,
      bacsV2Summary,
    });
  }, [bundle, sitesData, summary, obligations, actionableFindings, proofFiles, bacsV2Summary]);

  const donneesMetrics = useMemo(() => {
    if (!sitesData.length) return null;
    return computeDonneesMetrics(sitesData, [], {});
  }, [sitesData]);

  const switchToTab = useCallback(
    (tab) => {
      setActiveTab(tab);
      setSearchParams({ tab }, { replace: true });
      // Scroll tabs into view so the user sees the change
      setTimeout(() => {
        tabsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    },
    [setSearchParams]
  );

  const handleNbaAction = useCallback(
    (ctaAction) => {
      if (ctaAction.type === 'navigate') navigate(ctaAction.path);
      else if (ctaAction.type === 'tab') switchToTab(ctaAction.tab);
      else if (ctaAction.type === 'drawer') openActionDrawer(ctaAction.prefill);
      track('nba_click', { action_id: nextBestAction?.id });
    },
    [navigate, openActionDrawer, nextBestAction, switchToTab]
  );

  const handleStepClick = useCallback(
    (step) => {
      if (step.ctaTarget?.tab) switchToTab(step.ctaTarget.tab);
      else if (step.ctaTarget?.path) navigate(step.ctaTarget.path);
      track('guided_step_click', { step_id: step.id });
    },
    [navigate, switchToTab]
  );

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      await recomputeComplianceRules(org?.id);
      loadData();
      track('conformite_recompute');
    } catch {
      setError('Erreur lors de la réévaluation des règles');
    } finally {
      setRecomputing(false);
    }
  };

  const handleWorkflowAction = async (findingId, newStatus) => {
    try {
      await patchComplianceFinding(findingId, { status: newStatus });
      loadData();
      track('conformite_workflow', { finding_id: findingId, status: newStatus });
    } catch {
      toast('Erreur lors de la mise à jour du workflow', 'error');
    }
  };

  function handleCreateFromObligation(obligation) {
    openActionDrawer(
      {
        prefill: {
          titre: `Mise en conformité ${obligation.regulation}`,
          type: 'conformite',
          priorite:
            obligation.severity === 'critical'
              ? 'critical'
              : obligation.severity === 'high'
                ? 'high'
                : 'medium',
          description: obligation.quoi_faire,
          obligation_code: obligation.code,
          impact_eur: obligation.impact_eur,
          site: `${obligation.sites_concernes} sites concernés`,
        },
        sourceType: 'compliance',
        sourceId: obligation.code,
        evidenceRequired: obligation.severity === 'critical',
      },
      {
        onSave: (action) => track('action_create_from_conformite', { titre: action.titre }),
      }
    );
    track('conformite_create_action', { regulation: obligation.code });
  }

  function handleCreateFromFinding(finding) {
    openActionDrawer(
      {
        prefill: {
          titre: `Mise en conformité ${REG_LABELS[finding.regulation] || finding.regulation} — ${finding.site_nom}`,
          type: 'conformite',
          priorite:
            finding.severity === 'critical'
              ? 'critical'
              : finding.severity === 'high'
                ? 'high'
                : 'medium',
          description: finding.evidence || `Non conforme: ${finding.rule_id}`,
          obligation_code: finding.regulation,
          impact_eur: finding.penalty_exposure || finding.impact_eur,
          site: finding.site_nom,
        },
        siteId: finding.site_id,
        sourceType: 'compliance',
        sourceId: finding.rule_id,
        evidenceRequired: finding.severity === 'critical',
      },
      {
        onSave: (action) => track('action_create_from_conformite', { titre: action.titre }),
      }
    );
    track('conformite_create_action_finding', { rule_id: finding.rule_id });
  }

  function handleUploadProof(obligationId, file) {
    const entry = { name: file.name, date: new Date().toLocaleDateString('fr-FR') };
    setProofFiles((prev) => ({
      ...prev,
      [obligationId]: [...(prev[obligationId] || []), entry],
    }));
    track('proof_upload', { obligation_id: obligationId, file: file.name });
  }

  const overdueCount = obligations.filter(isOverdue).length;

  if (loading) {
    return (
      <PageShell icon={ShieldCheck} title="Conformité réglementaire" subtitle="Chargement...">
        <SkeletonKpi count={4} />
        <SkeletonTable rows={5} cols={4} />
      </PageShell>
    );
  }

  if (error) {
    const handleResetDb = async () => {
      try {
        await resetDb();
        setError(null);
        loadData();
      } catch {
        setError({ message: 'Échec du reset de la base de données' });
      }
    };

    return (
      <PageShell
        icon={ShieldCheck}
        title="Conformité réglementaire"
        subtitle={`${org?.nom || 'Organisation'} · ${sitesCount} site${sitesCount !== 1 ? 's' : ''}`}
      >
        <ErrorState
          title="Erreur de chargement"
          message={error.message || 'Données de conformité indisponibles'}
          onRetry={() => {
            setError(null);
            loadData();
          }}
          debug={
            isExpert && (error.error_code || error.status || error.request_url)
              ? {
                  ...(error.status ? { status: error.status } : {}),
                  ...(error.error_code ? { error_code: error.error_code } : {}),
                  ...(error.trace_id ? { trace_id: error.trace_id } : {}),
                  ...(error.hint ? { hint: error.hint } : {}),
                  ...(error.request_url ? { request_url: error.request_url } : {}),
                }
              : null
          }
          actions={
            error.hint === 'run_reset_db' ? (
              isExpert ? (
                <Button variant="secondary" onClick={handleResetDb}>
                  <RotateCcw size={14} /> Reset DB (dev)
                </Button>
              ) : (
                <p className="text-sm text-gray-500">
                  Contactez l'administrateur pour résoudre ce problème.
                </p>
              )
            ) : null
          }
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={ShieldCheck}
      title={
        <>
          <Explain term="statut_conformite">Conformité</Explain> réglementaire
        </>
      }
      subtitle={scopeLabel}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={handleRecompute} disabled={recomputing}>
            <RefreshCw size={14} className={recomputing ? 'animate-spin' : ''} />
            {recomputing ? 'Évaluation...' : 'Réévaluer'}
          </Button>
          <Button onClick={() => openActionDrawer({})}>
            <Plus size={16} /> Créer une action
          </Button>
        </>
      }
    >
      {/* Freshness — dernière évaluation + fallback */}
      {bundle?.meta?.generated_at ? (
        <span className="text-xs text-gray-400 ml-2">
          Dernière évaluation :{' '}
          {new Date(bundle.meta.generated_at).toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          })}
        </span>
      ) : (
        <span className="text-xs text-gray-400 ml-2">Évaluation en attente</span>
      )}

      {/* Expert-only badges — dev environment only */}
      {isExpert && import.meta.env.DEV && (
        <div className="flex items-center gap-2 -mt-1 mb-1">
          <DevApiBadge />
          <DevScopeBadge
            scope={{ orgId: org?.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId }}
            scopedSites={scopedSites}
          />
          {bundle?.meta?.generated_at && (
            <span className="text-[10px] font-mono text-gray-400">
              <Explain term="report_pct">Synthèse</Explain> :{' '}
              {new Date(bundle.meta.generated_at).toLocaleTimeString('fr-FR')}
            </span>
          )}
        </div>
      )}

      {/* Health Summary (compact) — expert only to reduce visual overload */}
      {isExpert && complianceHealth && (
        <HealthSummary healthState={complianceHealth} onNavigate={navigate} compact />
      )}

      {/* Cross-module CTAs — transforme la nav passive en funnel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
        <CrossModuleCTA
          icon={ShoppingCart}
          title="Arbitrer vos contrats énergie"
          desc="Comparer scénarios d'achat alignés avec vos obligations"
          to="/achat-energie"
          label="Scénarios"
          tint="violet"
        />
        <CrossModuleCTA
          icon={Radio}
          title="Valoriser vos flexibilités"
          desc="Effacement NEBEF, Tempo, capacité — gisements détectés"
          to="/flex"
          label="Flex"
          tint="yellow"
        />
      </div>

      {/* Step 21: Compliance Summary Banner — messages actionnables */}
      {summary && (
        <ComplianceSummaryBanner
          score={score}
          obligations={obligations}
          timeline={timeline}
          isExpert={isExpert}
          navigate={navigate}
        />
      )}

      {/* Empty state when no obligations found */}
      {!summary && emptyReason === 'NO_SITES' && (
        <EmptyState
          variant="empty"
          title="Aucun site dans le périmètre"
          text="Ajoutez ou sélectionnez des sites pour analyser la conformité réglementaire."
          ctaLabel="Voir le patrimoine"
          onCta={() => navigate('/patrimoine')}
        />
      )}
      {!summary && emptyReason && emptyReason !== 'NO_SITES' && (
        <EmptyState
          variant="partial"
          title="Conformité : données partielles"
          text="Les données de conformité sont incomplètes. Complétez les informations pour obtenir une analyse fiable."
        />
      )}

      {/* Risk summary badge — risque financier global */}
      {score.total_impact_eur > 0 && (
        <div className="flex items-center gap-2 mb-2" data-testid="conformite-risk-badge">
          <span className="text-sm text-gray-600">Risque financier global :</span>
          <RiskBadge riskEur={score.total_impact_eur} size="sm" />
        </div>
      )}

      {/* Guided Mode Bandeau (non-expert only) */}
      {!isExpert && guidedSteps.length > 0 && (
        <GuidedModeBandeau steps={guidedSteps} onStepClick={handleStepClick} />
      )}

      {/* Next Best Action hero card */}
      {nextBestAction && nextBestAction.id !== 'nba-all-good' && (
        <NextBestActionCard action={nextBestAction} onAction={handleNbaAction} />
      )}

      {/* A.2: Unified compliance score header */}
      <ComplianceScoreHeader complianceScore={complianceScore} segProfile={segProfile} />

      {/* Audit Energetique / SME (Loi 2025-391) */}
      {auditSme && auditSme.obligation !== 'AUCUNE' && (
        <div id="audit-sme">
          <AuditSmeCard assessment={auditSme} />
        </div>
      )}

      {/* Step 13: Frise reglementaire */}
      <RegulatoryTimeline
        events={timeline?.events || []}
        today={timeline?.today}
        loading={timelineLoading}
      />

      {/* Cockpit Tabs */}
      <div ref={tabsRef} />
      <Tabs
        tabs={COCKPIT_TABS}
        active={activeTab}
        onChange={(tab) => {
          setActiveTab(tab);
          setSearchParams({ tab }, { replace: true });
          track('conformite_tab', { tab });
        }}
      />

      {/* Active Filters Bar (obligations tab) */}
      {activeTab === 'obligations' && (
        <ActiveFiltersBar
          filters={[
            statusFilter && {
              key: 'status',
              label: 'Statut',
              value: STATUT_LABELS[statusFilter] || statusFilter,
              onRemove: () => setStatusFilter(null),
            },
            searchQuery.trim() && {
              key: 'search',
              label: 'Recherche',
              value: searchQuery,
              onRemove: () => setSearchQuery(''),
            },
          ].filter(Boolean)}
          total={obligations.length}
          filtered={sortedObligations.length}
          onReset={() => {
            setStatusFilter(null);
            setSearchQuery('');
          }}
        />
      )}

      {/* ======================== Tab: Obligations ======================== */}
      {activeTab === 'obligations' && (
        <ObligationsTab
          score={score}
          emptyReason={emptyReason}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          sortedObligations={sortedObligations}
          overdueCount={overdueCount}
          handleCreateFromObligation={handleCreateFromObligation}
          handleWorkflowAction={handleWorkflowAction}
          handleUploadProof={handleUploadProof}
          proofFiles={proofFiles}
          setAuditFindingId={setAuditFindingId}
          bacsV2Summary={bacsV2Summary}
          scopedSites={scopedSites}
          navigate={navigate}
          isExpert={isExpert}
          setDossierSource={setDossierSource}
          profileTags={profileTags}
          onNavigateIntake={
            scopedSites[0]
              ? () => {
                  navigate(`/intake/${scopedSites[0].id}`);
                  track('bacs_complete_data');
                }
              : undefined
          }
        />
      )}

      {/* Financements mobilisables (CEE) — masque V1.2, prevu evolution future */}
      {false && activeTab === 'obligations' && incentives.length > 0 && (
        <div
          className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-6"
          data-section="incentives"
        >
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Coins size={18} className="text-amber-500" />
            Financements mobilisables
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Certificats d'Économies d'Énergie (CEE) — mécanisme de financement, pas une obligation
            réglementaire.
          </p>
          <div className="space-y-3">
            {incentives.map((f, idx) => (
              <div key={idx} className="bg-white border border-amber-100 rounded-lg p-4">
                <div className="flex items-start justify-between mb-1">
                  <h4 className="font-medium text-gray-800">{f.rule_id || f.regulation}</h4>
                  <span className="px-3 py-1 rounded text-xs font-semibold bg-green-100 text-green-700">
                    Éligible CEE
                  </span>
                </div>
                <p className="text-sm text-gray-600">{f.evidence || f.explanation || ''}</p>
                {f.site_nom && <p className="text-xs text-gray-400 mt-1">Site : {f.site_nom}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ======================== Tab: Donnees & Qualite ======================== */}
      {activeTab === 'donnees' && (
        <DonneesTab
          scopedSites={scopedSites}
          intakeQuestions={intakeQuestions}
          navigate={navigate}
          donneesMetrics={donneesMetrics}
        />
      )}

      {/* ======================== Tab: Plan d'execution ======================== */}
      {activeTab === 'execution' && (
        <ExecutionTab
          actionableFindings={actionableFindings}
          emptyReason={emptyReason}
          handleWorkflowAction={handleWorkflowAction}
          handleCreateFromFinding={handleCreateFromFinding}
          setAuditFindingId={setAuditFindingId}
          openActionDrawer={openActionDrawer}
          navigate={navigate}
          proofFiles={proofFiles}
        />
      )}

      {/* ======================== Tab: Preuves & Rapports ======================== */}
      {activeTab === 'preuves' && (
        <PreuvesTab
          obligations={obligations}
          proofFiles={proofFiles}
          handleUploadProof={handleUploadProof}
        />
      )}

      {/* Lien cross-brique vers Usages */}
      <div className="flex items-center gap-2 mt-3 print:hidden">
        <button
          onClick={() => navigate(toUsages())}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition"
        >
          Voir les UES du site →
        </button>
      </div>

      {/* Finding Audit Drawer */}
      <FindingAuditDrawer findingId={auditFindingId} onClose={() => setAuditFindingId(null)} />

      {/* Dossier print view (Etape 5) */}
      <DossierPrintView
        open={!!dossierSource}
        onClose={() => setDossierSource(null)}
        sourceType={dossierSource?.sourceType || 'compliance'}
        sourceId={dossierSource?.sourceId || dossierSource?.code}
        sourceLabel={dossierSource?.label || dossierSource?.regulation}
        orgLabel={org?.nom}
        complianceData={{
          score: complianceScore?.score ?? complianceScore?.avg_score,
          confidence: complianceScore?.confidence,
          topUrgences: obligations
            .filter((o) => o.statut !== 'conforme' && o.statut !== 'hors_perimetre')
            .sort((a, b) => {
              const sev = { critical: 4, high: 3, medium: 2, low: 1 };
              return (sev[b.severity] || 0) - (sev[a.severity] || 0);
            })
            .slice(0, 3)
            .map((o) => ({
              regulation: o.regulation,
              statut: o.statut,
              echeance: o.echeance,
              penalty: (o.findings || []).reduce((s, f) => s + (f.estimated_penalty_eur || 0), 0),
            })),
          missingProofs: obligations
            .filter((o) => o.statut !== 'conforme' && !(proofFiles[o.id]?.length > 0))
            .map((o) => `${o.regulation} — preuve non déposée`),
          nextDeadline: timeline?.next_deadline
            ? {
                label: timeline.next_deadline.label || timeline.next_deadline.regulation,
                date: timeline.next_deadline.deadline,
              }
            : null,
        }}
      />
    </PageShell>
  );
}
