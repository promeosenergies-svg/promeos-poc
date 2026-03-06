/**
 * PROMEOS - Conformite (/conformite) V92
 * Cockpit RegOps: 4 tabs (Obligations, Donnees & Qualite, Plan d'execution, Preuves & Rapports).
 * Scope filtering (org/entity/site), empty state reason codes, workflow actions.
 * Sub-components extracted to conformite-tabs/ (V92 split).
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, Plus, RotateCcw, RefreshCw, Database } from 'lucide-react';
import { Button, PageShell, Drawer, ActiveFiltersBar, Explain, GLOSSARY } from '../ui';
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
import ErrorState from '../ui/ErrorState';
import { SkeletonKpi, SkeletonTable } from '../ui/Skeleton';
import { buildWatchlist, buildBriefing, computeHealthState } from '../models/dashboardEssentials';
import HealthSummary from '../components/HealthSummary';
import DossierPrintView from '../components/DossierPrintView';
import {
  REG_LABELS,
  REG_DESCRIPTIONS,
  STATUT_LABELS,
  BACKEND_STATUS_MAP,
  WORKFLOW_LABELS,
  SEVERITY_LABELS,
  COCKPIT_TABS,
  DRAWER_LABELS,
} from '../domain/compliance/complianceLabels.fr';
import {
  getComplianceBundle,
  getApiHealth,
  patchComplianceFinding,
  recomputeComplianceRules,
  getFindingDetail,
  getIntakeQuestions,
  resetDb,
} from '../services/api';
import {
  getComplianceScoreColor,
  getComplianceScoreStatus,
  COMPLIANCE_SCORE_THRESHOLDS,
} from '../lib/constants';

/* ---------- Dev-only badges ---------- */

function DevApiBadge() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getApiHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(false));
  }, []);

  if (health === null) return null; // loading

  const isOk = health && health.ok;
  return (
    <span
      data-testid="api-badge"
      className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full ${
        isOk ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      }`}
      title={isOk ? `v${health.version} · ${health.git_sha}` : 'API injoignable'}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isOk ? 'bg-green-500' : 'bg-red-500'}`} />
      {isOk ? 'API : Connectée' : 'API : Hors ligne'}
      {!isOk && (
        <span className="ml-1 text-[9px] text-red-500">{`${window.location.protocol}//${window.location.hostname}:8001/api/health`}</span>
      )}
    </span>
  );
}

/**
 * Resolve scope type and id from scope object.
 * Exported for testing.
 */
export function resolveScopeLabel(scope) {
  const scopeType = scope.siteId ? 'site' : scope.portefeuilleId ? 'portefeuille' : 'org';
  const scopeId = scope.siteId || scope.portefeuilleId || scope.orgId;
  return { scopeType, scopeId, label: `${scopeType}/${scopeId}` };
}

export function DevScopeBadge({ scope, scopedSites }) {
  const [copied, setCopied] = useState(false);
  const { scopeType, scopeId, label } = resolveScopeLabel(scope);

  const handleCopy = () => {
    navigator.clipboard.writeText(
      JSON.stringify({ scope_type: scopeType, scope_id: scopeId, sites_count: scopedSites.length })
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <span
      data-testid="scope-badge"
      className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 cursor-pointer"
      onClick={handleCopy}
      title={`Copier le périmètre : ${label} (${scopedSites.length} sites)`}
    >
      <Database size={10} />
      {label}
      <span className="text-indigo-400">({scopedSites.length})</span>
      {copied && <span className="text-green-600 font-medium">copié</span>}
    </span>
  );
}

/**
 * Build API scope params from ScopeContext.
 * Always includes org_id. Adds portefeuille_id or site_id based on scope.
 */
export function buildScopeParams(scope, scopedSites) {
  const params = { org_id: scope.orgId };
  if (scopedSites.length === 1) {
    params.site_id = scopedSites[0].id;
  } else if (scope.portefeuilleId) {
    params.portefeuille_id = scope.portefeuilleId;
  }
  return params;
}

/**
 * Parse a bundle response for error state.
 * Returns null if the bundle is healthy, or an error object with message/error_code/trace_id/hint.
 */
export function parseBundleError(bundle) {
  if (!bundle) return { message: 'Données de conformité indisponibles' };
  if (bundle.error_code) {
    return {
      message: bundle.empty_reason_message || 'Données de conformité indisponibles',
      error_code: bundle.error_code,
      trace_id: bundle.trace_id,
      hint: bundle.hint,
    };
  }
  return null;
}

/**
 * Compute aggregated BACS v2 summary from bundle.bacs_v2 data.
 * Exported for testing.
 */
export function computeBacsV2Summary(bacsV2Data) {
  if (!bacsV2Data) return null;
  const entries = Object.values(bacsV2Data);
  if (entries.length === 0) return null;
  const applicable = entries.some((e) => e.applicable);
  const deadlines = entries.map((e) => e.deadline).filter(Boolean);
  const closest = deadlines.length ? deadlines.sort()[0] : null;
  const maxPutile = Math.max(...entries.map((e) => e.putile_kw || 0));
  const maxThreshold = Math.max(...entries.map((e) => e.threshold_kw || 0));
  const triExemption = entries.some((e) => e.tri_exemption);
  return {
    applicable,
    deadline: closest,
    putile_kw: maxPutile || null,
    threshold_kw: maxThreshold || null,
    tier: maxThreshold >= 290 ? 'TIER1' : 'TIER2',
    tri_exemption: triExemption,
  };
}

/**
 * Compute human-readable scope label.
 * Exported for testing.
 */
export function computeScopeLabel(org, scope, scopedSites, portefeuilles) {
  const orgName = org?.nom || 'Organisation';
  if (scope?.siteId) {
    const site = scopedSites?.[0];
    return `${orgName} · Site: ${site?.nom || scope.siteId}`;
  }
  if (scope?.portefeuilleId) {
    const pf = portefeuilles?.find((p) => p.id === scope.portefeuilleId);
    return `${orgName} · Portefeuille: ${pf?.nom || scope.portefeuilleId} (${scopedSites?.length || 0} sites)`;
  }
  return `${orgName} · Organisation (${scopedSites?.length || 0} sites)`;
}

export function isOverdue(obligation) {
  if (!obligation.echeance || obligation.statut === 'conforme') return false;
  return new Date(obligation.echeance) < new Date();
}

/**
 * Transform API sitesData (from /compliance/sites) into obligation-like objects
 * grouped by regulation, for display in ObligationCard.
 */
export function sitesToObligations(sitesData, _summary) {
  if (!sitesData || !sitesData.length) return [];
  const byReg = {};

  for (const site of sitesData) {
    for (const f of site.findings) {
      const reg = f.regulation;
      if (!byReg[reg]) {
        byReg[reg] = {
          id: reg,
          regulation: REG_LABELS[reg] || reg,
          code: reg,
          description: REG_DESCRIPTIONS[reg] || reg,
          severity: 'low',
          statut: 'conforme',
          echeance: null,
          sites_concernes: 0,
          sites_conformes: 0,
          findings: [],
          _site_ids_all: new Set(),
          _site_ids_ok: new Set(),
        };
      }
      const obl = byReg[reg];
      obl.findings.push({ ...f, site_nom: site.site_nom, site_id: site.site_id });
      obl._site_ids_all.add(site.site_id);

      // Track worst severity
      const sevOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      if (f.severity && (sevOrder[f.severity] || 0) > (sevOrder[obl.severity] || 0)) {
        obl.severity = f.severity;
      }

      // Track worst status
      if (f.status === 'NOK') {
        obl.statut = 'non_conforme';
      } else if (f.status === 'UNKNOWN' && obl.statut === 'conforme') {
        obl.statut = 'a_qualifier';
      } else if (f.status === 'OUT_OF_SCOPE') {
        if (obl.statut === 'conforme') obl.statut = 'hors_perimetre';
      }

      // Track closest deadline
      if (f.deadline) {
        if (!obl.echeance || f.deadline < obl.echeance) {
          obl.echeance = f.deadline;
        }
      }

      // Track OK sites
      if (f.status === 'OK') {
        obl._site_ids_ok.add(site.site_id);
      }
    }
  }

  return Object.values(byReg).map((obl) => ({
    ...obl,
    sites_concernes: obl._site_ids_all.size,
    sites_conformes: obl._site_ids_ok.size,
    proof_status:
      obl.statut === 'conforme'
        ? 'ok'
        : obl.statut === 'a_qualifier'
          ? 'pending'
          : obl.statut === 'a_risque'
            ? 'in_progress'
            : 'missing',
    pourquoi: `${obl._site_ids_all.size} site(s) concerné(s) par ${obl.regulation}`,
    quoi_faire:
      obl.findings
        .filter((f) => f.actions?.length)
        .flatMap((f) => f.actions)
        .filter((v, i, a) => a.indexOf(v) === i)
        .join('. ') || 'Évaluer la conformité',
    preuve: 'Attestation ou rapport de conformité',
    impact_eur: 0,
  }));
}

function FindingAuditDrawer({ findingId, onClose }) {
  const { isExpert } = useExpertMode();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!findingId) return;
    setLoading(true);
    getFindingDetail(findingId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [findingId]);

  return (
    <Drawer open={!!findingId} onClose={onClose} title={<Explain term="finding">{DRAWER_LABELS.finding_title}</Explain>} wide>
      {loading ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.loading}</div>
      ) : !detail ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.not_found}</div>
      ) : (
        <div className="space-y-5">
          {/* Identity */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
              {DRAWER_LABELS.identity}
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {isExpert && (
                <div>
                  <span className="text-gray-500">{DRAWER_LABELS.rule_id} :</span>{' '}
                  <span className="font-mono font-medium">{detail.rule_id}</span>
                </div>
              )}
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.regulation} :</span>{' '}
                <span className="font-medium">{detail.regulation}</span>
              </div>
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.status} :</span>{' '}
                <span className="font-medium">
                  {STATUT_LABELS[BACKEND_STATUS_MAP[detail.status]] || detail.status}
                </span>
              </div>
              <div>
                <span className="text-gray-500"><Explain term="severite">{DRAWER_LABELS.severity}</Explain> :</span>{' '}
                <span className="font-medium">
                  {SEVERITY_LABELS[detail.severity] || detail.severity}
                </span>
              </div>
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.site} :</span>{' '}
                <span className="font-medium">{detail.site_nom}</span>
              </div>
              {detail.deadline && (
                <div>
                  <span className="text-gray-500">{DRAWER_LABELS.deadline} :</span>{' '}
                  <span className="font-medium">{detail.deadline}</span>
                </div>
              )}
            </div>
          </div>

          {/* Inputs */}
          {detail.inputs && Object.keys(detail.inputs).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.inputs}
              </p>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                {Object.entries(detail.inputs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-gray-600 font-mono">{k}</span>
                    <span className="text-gray-900 font-medium">
                      {v === null ? '-' : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Params */}
          {detail.params && Object.keys(detail.params).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.params}
              </p>
              <div className="bg-blue-50 rounded-lg p-3 space-y-1">
                {Object.entries(detail.params).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-blue-600 font-mono">{k}</span>
                    <span className="text-gray-900 font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence */}
          {detail.evidence_refs && Object.keys(detail.evidence_refs).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.evidence_refs}
              </p>
              <div className="bg-green-50 rounded-lg p-3 text-sm text-gray-700">
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(detail.evidence_refs, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Evidence text */}
          {detail.evidence && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.explanation}
              </p>
              <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{detail.evidence}</p>
            </div>
          )}

          {/* Metadata */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
              {DRAWER_LABELS.metadata}
            </p>
            <div className="text-xs text-gray-400 space-y-1">
              {isExpert && detail.engine_version && (
                <div>
                  {DRAWER_LABELS.engine_version} :{' '}
                  <span className="font-mono">{detail.engine_version}</span>
                </div>
              )}
              {detail.created_at && (
                <div>
                  {DRAWER_LABELS.computed_at} :{' '}
                  {new Date(detail.created_at).toLocaleString('fr-FR')}
                </div>
              )}
              {detail.updated_at && (
                <div>
                  {DRAWER_LABELS.updated_at} : {new Date(detail.updated_at).toLocaleString('fr-FR')}
                </div>
              )}
              <div>
                {DRAWER_LABELS.workflow} :{' '}
                {WORKFLOW_LABELS[detail.insight_status] || detail.insight_status}
              </div>
              <div>
                {DRAWER_LABELS.owner} : {detail.owner || '-'}
              </div>
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}

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
  const [activeTab, setActiveTab] = useState(
    searchParams.get('tab') || 'obligations',
  );
  const [intakeQuestions, setIntakeQuestions] = useState([]);
  const [emptyReason, setEmptyReason] = useState(null);
  const [error, setError] = useState(null);
  const [bundle, setBundle] = useState(null);
  const [dossierSource, setDossierSource] = useState(null);
  const [complianceScore, setComplianceScore] = useState(null); // A.2 unified score

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
    return {
      pct: summary.pct_ok || 0,
      total: obligations.length,
      non_conformes: summary.sites_nok || 0,
      a_risque: summary.sites_unknown || 0,
      conformes: summary.sites_ok || 0,
      total_impact_eur: 0,
    };
  }, [summary, obligations]);

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

  const sortedObligations = useMemo(() => {
    let list = [...obligations];
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
      const aOver = isOverdue(a) ? 0 : 1;
      const bOver = isOverdue(b) ? 0 : 1;
      if (aOver !== bOver) return aOver - bOver;
      const order = { non_conforme: 0, a_risque: 1, conforme: 2 };
      return (order[a.statut] ?? 9) - (order[b.statut] ?? 9);
    });
    return list;
  }, [obligations, statusFilter, searchQuery]);

  const actionableFindings = useMemo(() => {
    return obligations
      .flatMap((o) => o.findings)
      .filter((f) => f.status === 'NOK' || f.status === 'UNKNOWN')
      .filter((f) => f.insight_status !== 'resolved' && f.insight_status !== 'false_positive');
  }, [obligations]);

  // ── Guided Mode + NBA + Données metrics ──
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

  const handleNbaAction = useCallback(
    (ctaAction) => {
      if (ctaAction.type === 'navigate') navigate(ctaAction.path);
      else if (ctaAction.type === 'tab') setActiveTab(ctaAction.tab);
      else if (ctaAction.type === 'drawer') openActionDrawer(ctaAction.prefill);
      track('nba_click', { action_id: nextBestAction?.id });
    },
    [navigate, openActionDrawer, nextBestAction]
  );

  const handleStepClick = useCallback(
    (step) => {
      if (step.ctaTarget?.tab) setActiveTab(step.ctaTarget.tab);
      else if (step.ctaTarget?.path) navigate(step.ctaTarget.path);
      track('guided_step_click', { step_id: step.id });
    },
    [navigate]
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
          site: finding.site_nom,
        },
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
              <Button variant="secondary" onClick={handleResetDb}>
                <RotateCcw size={14} /> Reset DB (dev)
              </Button>
            ) : null
          }
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={ShieldCheck}
      title={<><Explain term="statut_conformite">Conformité</Explain> réglementaire</>}
      subtitle={scopeLabel}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={handleRecompute} disabled={recomputing}>
            <RefreshCw size={14} className={recomputing ? 'animate-spin' : ''} />
            {recomputing ? 'Évaluation...' : 'Réévaluer'}
          </Button>
          <Button onClick={() => openActionDrawer({})}>
            <Plus size={16} /> Créer action conformité
          </Button>
        </>
      }
    >
      {/* Expert-only badges */}
      {isExpert && (
        <div className="flex items-center gap-2 -mt-1 mb-1">
          <DevApiBadge />
          <DevScopeBadge
            scope={{ orgId: org?.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId }}
            scopedSites={scopedSites}
          />
          {bundle?.meta?.generated_at && (
            <span className="text-[10px] font-mono text-gray-400">
              <Explain term="report_pct">Synthèse</Explain> : {new Date(bundle.meta.generated_at).toLocaleTimeString('fr-FR')}
            </span>
          )}
        </div>
      )}

      {/* Health Summary (compact) */}
      {complianceHealth && (
        <HealthSummary healthState={complianceHealth} onNavigate={navigate} compact />
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
      {complianceScore && (
        <div data-section="compliance-score-header" className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center gap-6">
            {/* Score display */}
            <div className="text-center min-w-[100px]">
              <p className="text-xs text-gray-500 mb-1">Score conformité</p>
              <span className={`text-3xl font-bold ${getComplianceScoreColor(complianceScore.score ?? complianceScore.avg_score)}`}>
                {Math.round(complianceScore.score ?? complianceScore.avg_score ?? 0)}
              </span>
              <span className="text-lg text-gray-400">/100</span>
            </div>
            {/* Breakdown bars */}
            <div className="flex-1 space-y-2">
              {(complianceScore.breakdown || []).map((fw) => (
                <div key={fw.framework} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-32 truncate">
                    {fw.framework === 'tertiaire_operat' ? 'Décret Tertiaire (45%)' : fw.framework === 'bacs' ? 'BACS (30%)' : 'APER (25%)'}
                  </span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${fw.score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : fw.score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(100, fw.score)}%` }}
                    />
                  </div>
                  <span className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(fw.score)}`}>
                    {Math.round(fw.score)}
                  </span>
                </div>
              ))}
              {/* Fallback: show breakdown_avg from portfolio if no breakdown */}
              {!complianceScore.breakdown && complianceScore.breakdown_avg && (
                Object.entries(complianceScore.breakdown_avg).map(([fw, score]) => (
                  <div key={fw} className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-32 truncate">
                      {fw === 'tertiaire_operat' ? 'Décret Tertiaire (45%)' : fw === 'bacs' ? 'BACS (30%)' : 'APER (25%)'}
                    </span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, score)}%` }}
                      />
                    </div>
                    <span className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(score)}`}>
                      {Math.round(score)}
                    </span>
                  </div>
                ))
              )}
            </div>
            {/* Confidence */}
            {(complianceScore.confidence || complianceScore.high_confidence_count != null) && (
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Confiance</p>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  (complianceScore.confidence === 'high' || (complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6))
                    ? 'bg-green-100 text-green-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {(complianceScore.confidence === 'high' || (complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6))
                    ? 'Données fiables'
                    : 'Données partielles'}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cockpit Tabs */}
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

      {/* Finding Audit Drawer */}
      <FindingAuditDrawer findingId={auditFindingId} onClose={() => setAuditFindingId(null)} />

      {/* Dossier print view (Étape 5) */}
      <DossierPrintView
        open={!!dossierSource}
        onClose={() => setDossierSource(null)}
        sourceType={dossierSource?.sourceType}
        sourceId={dossierSource?.sourceId}
        sourceLabel={dossierSource?.label}
        orgLabel={org?.nom}
      />
    </PageShell>
  );
}
