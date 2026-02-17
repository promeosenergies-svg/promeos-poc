/**
 * PROMEOS - Conformite (/conformite) V10
 * Cockpit RegOps: 4 tabs (Obligations, Donnees & Qualite, Plan d'execution, Preuves & Rapports).
 * Scope filtering (org/entity/site), empty state reason codes, workflow actions.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck, AlertTriangle, CheckCircle, Clock, FileText,
  ChevronDown, ChevronUp, ChevronRight, Plus, Upload, Building,
  BookOpen, ExternalLink, Zap, RotateCcw, RefreshCw,
  UserCheck, CheckCircle2, XCircle, X, Eye, Search,
  ClipboardList, Database, FolderOpen,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge, PageShell, Progress, Drawer } from '../ui';
import Tabs from '../ui/Tabs';
import { useToast } from '../ui/ToastProvider';
import CreateActionModal from '../components/CreateActionModal';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { track } from '../services/tracker';
import ErrorState from '../ui/ErrorState';
import {
  REG_LABELS, REG_DESCRIPTIONS, STATUT_LABELS, BACKEND_STATUS_MAP,
  WORKFLOW_LABELS, SEVERITY_LABELS, SEVERITY_BADGE_MAP, CONFIDENCE_LABELS,
  COCKPIT_TABS, EMPTY_REASONS as EMPTY_REASONS_LABELS, RULE_LABELS,
  RULE_NEXT_STEPS, RULE_EXPECTED_PROOFS, DRAWER_LABELS,
} from '../domain/compliance/complianceLabels.fr';
import {
  applyKB,
  getComplianceBundle,
  getApiHealth,
  patchComplianceFinding,
  recomputeComplianceRules,
  getDataQuality,
  getFindingDetail,
  getIntakeQuestions,
  resetDb,
} from '../services/api';

const SEVERITY_BADGE = SEVERITY_BADGE_MAP;

const STATUT_CONFIG = {
  non_conforme:  { label: STATUT_LABELS.non_conforme,  color: 'text-red-700',   bg: 'bg-red-50',   border: 'border-red-200',   icon: AlertTriangle },
  a_risque:      { label: STATUT_LABELS.a_risque,      color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', icon: Clock },
  a_qualifier:   { label: STATUT_LABELS.a_qualifier,   color: 'text-blue-700',  bg: 'bg-blue-50',  border: 'border-blue-200',  icon: Search },
  conforme:      { label: STATUT_LABELS.conforme,      color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle },
  hors_perimetre:{ label: STATUT_LABELS.hors_perimetre,color: 'text-gray-500',  bg: 'bg-gray-50',  border: 'border-gray-200',  icon: X },
};

const WORKFLOW_CONFIG = {
  open:           { label: WORKFLOW_LABELS.open,           color: 'bg-red-50 text-red-700' },
  ack:            { label: WORKFLOW_LABELS.ack,            color: 'bg-amber-50 text-amber-700' },
  resolved:       { label: WORKFLOW_LABELS.resolved,       color: 'bg-green-50 text-green-700' },
  false_positive: { label: WORKFLOW_LABELS.false_positive, color: 'bg-gray-100 text-gray-500' },
};

const EMPTY_REASONS = {
  NO_SITES:      { Icon: Building,    ...EMPTY_REASONS_LABELS.NO_SITES },
  NO_EVALUATION: { Icon: RefreshCw,   ...EMPTY_REASONS_LABELS.NO_EVALUATION },
  ALL_COMPLIANT: { Icon: CheckCircle, ...EMPTY_REASONS_LABELS.ALL_COMPLIANT },
  DATA_BLOCKED:  { Icon: Database,    ...EMPTY_REASONS_LABELS.DATA_BLOCKED },
};

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
        <span className="ml-1 text-[9px] text-red-500">{`${window.location.protocol}//${window.location.hostname}:8000/api/health`}</span>
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
    navigator.clipboard.writeText(JSON.stringify({ scope_type: scopeType, scope_id: scopeId, sites_count: scopedSites.length }));
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
  const applicable = entries.some(e => e.applicable);
  const deadlines = entries.map(e => e.deadline).filter(Boolean);
  const closest = deadlines.length ? deadlines.sort()[0] : null;
  const maxPutile = Math.max(...entries.map(e => e.putile_kw || 0));
  const maxThreshold = Math.max(...entries.map(e => e.threshold_kw || 0));
  const triExemption = entries.some(e => e.tri_exemption);
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
  if (scope.siteId) {
    const site = scopedSites[0];
    return `${org.nom} · Site: ${site?.nom || scope.siteId}`;
  }
  if (scope.portefeuilleId) {
    const pf = portefeuilles?.find(p => p.id === scope.portefeuilleId);
    return `${org.nom} · Portefeuille: ${pf?.nom || scope.portefeuilleId} (${scopedSites.length} sites)`;
  }
  return `${org.nom} · Organisation (${scopedSites.length} sites)`;
}

export function isOverdue(obligation) {
  if (!obligation.echeance || obligation.statut === 'conforme') return false;
  return new Date(obligation.echeance) < new Date();
}

function WorkflowBadge({ status }) {
  const cfg = WORKFLOW_CONFIG[status] || WORKFLOW_CONFIG.open;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function ScoreGauge({ pct, isEmpty }) {
  if (isEmpty) {
    return (
      <div className="flex items-center gap-4">
        <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center">
          <span className="text-2xl font-bold text-gray-400">&mdash;</span>
        </div>
        <div className="flex-1">
          <div className="h-3 bg-gray-200 rounded-full" />
          <p className="text-xs text-gray-500 mt-1">Score de conformité global</p>
          <p className="text-xs text-gray-400 mt-0.5">Aucune évaluation disponible</p>
        </div>
      </div>
    );
  }

  const color = pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600';
  const bg = pct >= 80 ? 'bg-green-100' : pct >= 50 ? 'bg-amber-100' : 'bg-red-100';
  const fill = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-4">
      <div className={`w-20 h-20 rounded-full ${bg} flex items-center justify-center`}>
        <span className={`text-2xl font-bold ${color}`}>{pct}%</span>
      </div>
      <div className="flex-1">
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full ${fill} rounded-full transition-all`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-500 mt-1">Score de conformité global</p>
        <p className="text-xs text-gray-400 mt-0.5">Score = sites conformes / sites évalués (pondéré par criticité)</p>
      </div>
    </div>
  );
}

const KB_SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function KBObligationsSection({ scopedSites }) {
  const { isExpert } = useExpertMode();
  const [kbResult, setKbResult] = useState(null);
  const [kbLoading, setKbLoading] = useState(true);
  const [kbError, setKbError] = useState(false);
  const [expandedKb, setExpandedKb] = useState(null);

  useEffect(() => {
    const totalSurface = scopedSites.reduce((s, site) => s + (site.surface_m2 || 0), 0);
    const maxSurface = Math.max(...scopedSites.map(s => s.surface_m2 || 0), 0);
    const estHvacKw = Math.round(maxSurface * 0.1);
    const largeSites = scopedSites.filter(s => (s.surface_m2 || 0) >= 2000);
    const estParkingM2 = largeSites.length > 0 ? Math.round(largeSites[0].surface_m2 * 0.6) : 0;

    const context = {
      site_context: {
        surface_m2: maxSurface,
        hvac_kw: estHvacKw,
        building_type: 'bureau',
        parking_area_m2: estParkingM2,
        tertiaire_area_m2: totalSurface,
        nb_sites: scopedSites.length,
      },
      domain: 'reglementaire',
      allow_drafts: false,
    };

    setKbLoading(true);
    applyKB(context)
      .then((data) => { setKbResult(data); setKbError(false); })
      .catch(() => { setKbError(true); })
      .finally(() => setKbLoading(false));
  }, [scopedSites]);

  if (kbLoading) {
    return (
      <Card>
        <CardBody className="text-center py-6">
          <BookOpen size={24} className="text-blue-300 mx-auto mb-2 animate-pulse" />
          <p className="text-sm text-gray-400">Analyse réglementaire KB en cours\u2026</p>
        </CardBody>
      </Card>
    );
  }

  if (kbError || !kbResult) return null;

  const items = kbResult.applicable_items || [];
  const missing = kbResult.missing_fields || [];
  const suggestions = kbResult.suggestions || [];

  if (items.length === 0 && missing.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <BookOpen size={16} className="text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-700">
          Obligations détectées par la KB ({items.length})
        </h3>
        <Badge status="info">Intelligence KB</Badge>
      </div>

      {items
        .sort((a, b) => (KB_SEVERITY_ORDER[a.severity] ?? 9) - (KB_SEVERITY_ORDER[b.severity] ?? 9))
        .map((item) => (
        <Card key={item.id} className="border-l-4 border-l-blue-400">
          <CardBody className="py-3">
            <div
              className="flex items-start gap-3 cursor-pointer"
              onClick={() => setExpandedKb(expandedKb === item.id ? null : item.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <Badge status={SEVERITY_BADGE[item.severity] || 'neutral'}>{SEVERITY_LABELS[item.severity] || item.severity}</Badge>
                  {item.confidence && (
                    <Badge status={item.confidence === 'high' ? 'ok' : 'neutral'}>{CONFIDENCE_LABELS[item.confidence] || item.confidence}</Badge>
                  )}
                  {item.domain && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-red-50 text-red-700">{item.domain}</span>
                  )}
                </div>
                <h4 className="text-sm font-semibold text-gray-900 leading-tight">{item.title}</h4>
                {expandedKb !== item.id && item.summary && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.summary}</p>
                )}
                {item.why && expandedKb !== item.id && (
                  <p className="text-xs text-blue-600 mt-1">
                    <Zap size={11} className="inline mr-1" />
                    {item.why}
                  </p>
                )}
              </div>
              <button className="p-1 text-gray-400 hover:text-gray-600 shrink-0">
                {expandedKb === item.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            </div>

            {expandedKb === item.id && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                {item.why && (
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Pourquoi applicable</p>
                    <p className="text-sm text-gray-700">{item.why}</p>
                  </div>
                )}
                {item.content_md && (
                  <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-4">
                    {item.content_md}
                  </div>
                )}
                {item.logic?.then?.outputs && (
                  <div className="p-3 bg-amber-50 rounded-lg">
                    <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Actions / Obligations</p>
                    {item.logic.then.outputs.map((output, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-amber-800 mt-1">
                        <span className={`inline-block w-2 h-2 rounded-full ${
                          output.severity === 'critical' ? 'bg-red-500' :
                          output.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'
                        }`} />
                        <span className="font-medium">{output.label}</span>
                        {output.deadline && (
                          <span className="text-amber-600 flex items-center gap-1">
                            <Clock size={11} /> {output.deadline}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {item.sources && item.sources.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 mb-1">Sources réglementaires</p>
                    {item.sources.map((src, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                        <ExternalLink size={12} />
                        <span>{src.label}{src.section ? ` - ${src.section}` : ''}</span>
                      </div>
                    ))}
                  </div>
                )}
                {item.tags && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(item.tags).map(([cat, values]) =>
                      Array.isArray(values) && values.map((v) => (
                        <span key={`${cat}-${v}`} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {cat}:{v}
                        </span>
                      ))
                    )}
                  </div>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  {isExpert && <span>KB ID: {item.id}</span>}
                  {item.updated_at && <span>MAJ: {item.updated_at}</span>}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      ))}

      {missing.length > 0 && (
        <Card className="border-l-4 border-l-amber-300">
          <CardBody className="py-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} className="text-amber-500" />
              <p className="text-xs font-semibold text-amber-700">Données manquantes pour une analyse complète</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.map((field) => (
                <span key={field} className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-xs font-medium">{field}</span>
              ))}
            </div>
            {suggestions.length > 0 && (
              <p className="text-xs text-gray-500 mt-2">{suggestions.join(' ')}</p>
            )}
          </CardBody>
        </Card>
      )}

      <TrustBadge source="PROMEOS KB" period="Analyse réglementaire automatique" confidence="high" />
    </div>
  );
}

/**
 * Transform API sitesData (from /compliance/sites) into obligation-like objects
 * grouped by regulation, for display in ObligationCard.
 */
export function sitesToObligations(sitesData, summary) {
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

  return Object.values(byReg).map(obl => ({
    ...obl,
    sites_concernes: obl._site_ids_all.size,
    sites_conformes: obl._site_ids_ok.size,
    proof_status: obl.statut === 'conforme' ? 'ok' : obl.statut === 'a_qualifier' ? 'pending' : obl.statut === 'a_risque' ? 'in_progress' : 'missing',
    pourquoi: `${obl._site_ids_all.size} site(s) concerné(s) par ${obl.regulation}`,
    quoi_faire: obl.findings.filter(f => f.actions?.length).flatMap(f => f.actions).filter((v, i, a) => a.indexOf(v) === i).join('. ') || 'Évaluer la conformité',
    preuve: 'Attestation ou rapport de conformité',
    impact_eur: 0,
  }));
}

function ObligationCard({ obligation, onCreateAction, onWorkflowAction, onUploadProof, proofFiles, onAuditFinding, bacsV2Summary, onNavigateIntake }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_qualifier;
  const Icon = cfg.icon;
  const overdue = isOverdue(obligation);
  const pctConforme = obligation.sites_concernes > 0
    ? Math.round(obligation.sites_conformes / obligation.sites_concernes * 100)
    : 100;
  const files = proofFiles[obligation.id] || [];

  return (
    <Card className={`border-l-4 ${cfg.border} ${overdue ? 'ring-1 ring-red-200' : ''}`}>
      <CardBody>
        {/* Overdue banner */}
        {overdue && (
          <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-red-50 rounded-lg">
            <AlertTriangle size={14} className="text-red-600" />
            <span className="text-xs font-semibold text-red-700">En retard — échéance dépassée ({obligation.echeance})</span>
          </div>
        )}

        {/* Header row */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5`}>
              <Icon size={18} className={cfg.color} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-gray-900">{obligation.regulation}</h3>
                <Badge status={SEVERITY_BADGE[obligation.severity] || 'neutral'}>{SEVERITY_LABELS[obligation.severity] || obligation.severity}</Badge>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
                {overdue && <Badge status="crit">En retard</Badge>}
              </div>
              <p className="text-sm text-gray-600 mt-1">{obligation.description}</p>
            </div>
          </div>
          <button
            onClick={() => { setExpanded(!expanded); track('obligation_toggle', { code: obligation.code, expanded: !expanded }); }}
            className="p-1 hover:bg-gray-100 rounded transition ml-2"
          >
            {expanded ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
          </button>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-500">Sites concernés : </span>
            <span className="font-medium text-gray-800">{obligation.sites_concernes}</span>
          </div>
          <div>
            <span className="text-gray-500">Conformes : </span>
            <span className="font-medium text-green-700">{obligation.sites_conformes}/{obligation.sites_concernes}</span>
            <span className="text-gray-400 ml-1">({pctConforme}%)</span>
          </div>
          {obligation.echeance && (
            <div className="flex items-center gap-1">
              <Clock size={14} className={overdue ? 'text-red-500' : 'text-gray-400'} />
              <span className="text-gray-500">Échéance : </span>
              <span className={`font-medium ${overdue ? 'text-red-600' : 'text-gray-800'}`}>{obligation.echeance}</span>
            </div>
          )}
        </div>

        {/* BACS v2 detail */}
        {obligation.code === 'bacs' && bacsV2Summary && (
          <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${
              bacsV2Summary.applicable ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
            }`}>
              {bacsV2Summary.applicable ? 'Assujetti BACS' : 'Non assujetti'}
            </span>
            {bacsV2Summary.threshold_kw && (
              <span className="text-gray-600">
                Seuil: {bacsV2Summary.threshold_kw >= 290 ? '\u2265290 kW' : '\u226570 kW'}
                {bacsV2Summary.putile_kw ? ` (Putile: ${bacsV2Summary.putile_kw} kW)` : ''}
              </span>
            )}
            {bacsV2Summary.deadline && (
              <span className={`flex items-center gap-1 ${
                new Date(bacsV2Summary.deadline) < new Date() ? 'text-red-600 font-semibold' : 'text-gray-600'
              }`}>
                <Clock size={12} />
                Échéance : {bacsV2Summary.deadline}
              </span>
            )}
            {bacsV2Summary.tri_exemption && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                Exemption TRI possible
              </span>
            )}
          </div>
        )}

        {/* BACS CTA when missing data */}
        {obligation.code === 'bacs' && !bacsV2Summary && onNavigateIntake && (
          <div className="mt-2 p-3 bg-blue-50 rounded-lg flex items-center gap-3">
            <AlertTriangle size={16} className="text-blue-600 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-700">Données BACS incomplètes</p>
              <p className="text-xs text-blue-600">Complétez les données pour déterminer l'applicabilité et l'échéance.</p>
            </div>
            <Button size="sm" variant="secondary" onClick={onNavigateIntake}>
              Compléter données BACS
            </Button>
          </div>
        )}

        {/* Progress bar */}
        <div className="mt-3">
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${pctConforme}%` }} />
          </div>
        </div>

        {/* CTA always visible for non-conforme */}
        {obligation.statut !== 'conforme' && !expanded && (
          <div className="mt-3 flex items-center gap-2">
            <Button onClick={() => onCreateAction(obligation)} size="sm" variant="secondary">
              <Plus size={14} /> Créer action
            </Button>
          </div>
        )}

        {/* Expanded detail */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Pourquoi concerné</p>
                <p className="text-sm text-gray-700">{obligation.pourquoi}</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs font-semibold text-amber-600 uppercase mb-1">Ce qu'il faut faire</p>
                <p className="text-sm text-gray-700">{obligation.quoi_faire}</p>
              </div>
            </div>

            {/* Per-finding detail with workflow */}
            {obligation.findings && obligation.findings.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Findings par site ({obligation.findings.length})</p>
                <div className="rounded-lg border border-gray-200 divide-y divide-gray-100">
                  {obligation.findings.filter(f => f.status === 'NOK' || f.status === 'UNKNOWN').map((f) => (
                    <div key={f.id} className="flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-gray-50 transition-colors">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${f.status === 'NOK' ? 'bg-red-500' : 'bg-amber-500'}`} />
                      <span className="text-gray-700 font-medium truncate flex-1">{f.site_nom}</span>
                      <span className="text-xs text-gray-500 hidden sm:inline">{RULE_LABELS[f.rule_id]?.title_fr || f.regulation || 'Non conforme'}</span>
                      <button
                        onClick={() => onAuditFinding(f.id)}
                        className="text-xs text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50 font-medium flex items-center gap-1 px-2 py-1 rounded transition-colors"
                        title="Voir les détails"
                      >
                        <Eye size={12} /> Détails
                      </button>
                      <WorkflowBadge status={f.insight_status} />
                      {f.insight_status === 'open' && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'ack')}
                          className="text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 font-medium flex items-center gap-1 px-2 py-1 rounded transition-colors"
                        >
                          <UserCheck size={12} /> Prendre en charge
                        </button>
                      )}
                      {f.insight_status === 'ack' && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'resolved')}
                          className="text-xs text-green-600 hover:text-green-800 hover:bg-green-50 font-medium flex items-center gap-1 px-2 py-1 rounded transition-colors"
                        >
                          <CheckCircle2 size={12} /> Résolu
                        </button>
                      )}
                      {(f.insight_status === 'open' || f.insight_status === 'ack') && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'false_positive')}
                          className="text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 font-medium flex items-center gap-1 px-2 py-1 rounded transition-colors"
                        >
                          <XCircle size={12} /> FP
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Proof upload section */}
            <div className="p-3 bg-indigo-50/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-indigo-600 uppercase">Joindre preuve</p>
              </div>
              {files.length > 0 && (
                <div className="space-y-1 mb-2">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-gray-700 bg-white px-2 py-1.5 rounded">
                      <FileText size={14} className="text-indigo-500 shrink-0" />
                      <span className="truncate">{f.name}</span>
                      <span className="text-xs text-gray-400 ml-auto whitespace-nowrap">{f.date}</span>
                    </div>
                  ))}
                </div>
              )}
              <label className="inline-flex items-center gap-2 cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 transition font-medium">
                <Upload size={14} />
                Ajouter un fichier
                <input type="file" className="sr-only" onChange={(e) => { if (e.target.files[0]) onUploadProof(obligation.id, e.target.files[0]); e.target.value = ''; }} />
              </label>
            </div>

            {obligation.statut !== 'conforme' && (
              <Button onClick={() => onCreateAction(obligation)} size="sm">
                <Plus size={14} /> Créer action conformité
              </Button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
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
    <Drawer open={!!findingId} onClose={onClose} title={DRAWER_LABELS.finding_title} wide>
      {loading ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.loading}</div>
      ) : !detail ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.not_found}</div>
      ) : (
        <div className="space-y-5">
          {/* Identity */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.identity}</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {isExpert && <div><span className="text-gray-500">{DRAWER_LABELS.rule_id} :</span> <span className="font-mono font-medium">{detail.rule_id}</span></div>}
              <div><span className="text-gray-500">{DRAWER_LABELS.regulation} :</span> <span className="font-medium">{detail.regulation}</span></div>
              <div><span className="text-gray-500">{DRAWER_LABELS.status} :</span> <span className="font-medium">{STATUT_LABELS[BACKEND_STATUS_MAP[detail.status]] || detail.status}</span></div>
              <div><span className="text-gray-500">{DRAWER_LABELS.severity} :</span> <span className="font-medium">{SEVERITY_LABELS[detail.severity] || detail.severity}</span></div>
              <div><span className="text-gray-500">{DRAWER_LABELS.site} :</span> <span className="font-medium">{detail.site_nom}</span></div>
              {detail.deadline && <div><span className="text-gray-500">{DRAWER_LABELS.deadline} :</span> <span className="font-medium">{detail.deadline}</span></div>}
            </div>
          </div>

          {/* Inputs */}
          {detail.inputs && Object.keys(detail.inputs).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.inputs}</p>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                {Object.entries(detail.inputs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-gray-600 font-mono">{k}</span>
                    <span className="text-gray-900 font-medium">{v === null ? '-' : String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Params */}
          {detail.params && Object.keys(detail.params).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.params}</p>
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
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.evidence_refs}</p>
              <div className="bg-green-50 rounded-lg p-3 text-sm text-gray-700">
                <pre className="whitespace-pre-wrap">{JSON.stringify(detail.evidence_refs, null, 2)}</pre>
              </div>
            </div>
          )}

          {/* Evidence text */}
          {detail.evidence && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.explanation}</p>
              <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{detail.evidence}</p>
            </div>
          )}

          {/* Metadata */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{DRAWER_LABELS.metadata}</p>
            <div className="text-xs text-gray-400 space-y-1">
              {isExpert && detail.engine_version && <div>{DRAWER_LABELS.engine_version} : <span className="font-mono">{detail.engine_version}</span></div>}
              {detail.created_at && <div>{DRAWER_LABELS.computed_at} : {new Date(detail.created_at).toLocaleString('fr-FR')}</div>}
              {detail.updated_at && <div>{DRAWER_LABELS.updated_at} : {new Date(detail.updated_at).toLocaleString('fr-FR')}</div>}
              <div>{DRAWER_LABELS.workflow} : {WORKFLOW_LABELS[detail.insight_status] || detail.insight_status}</div>
              <div>{DRAWER_LABELS.owner} : {detail.owner || '-'}</div>
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}

function DataQualityGate({ siteId, siteName }) {
  const [dq, setDq] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [dqError, setDqError] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    getDataQuality('site', siteId)
      .then((data) => { setDq(data); setDqError(false); })
      .catch(() => { setDqError(true); });
  }, [siteId]);

  if (dqError) {
    return (
      <Card className="border-l-4 border-gray-200">
        <CardBody className="bg-gray-50 py-3">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle size={14} className="text-gray-400" />
            <span>{siteName || 'Site'} — Qualité indisponible</span>
          </div>
        </CardBody>
      </Card>
    );
  }

  if (!dq) return null;

  const statusColors = {
    OK: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800' },
    WARNING: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' },
    BLOCKED: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
  };
  const sc = statusColors[dq.gate_status] || statusColors.WARNING;

  return (
    <Card className={`border-l-4 ${sc.border}`}>
      <CardBody className={sc.bg}>
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className={sc.text} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">
                  {siteName ? `${siteName} — Qualité` : 'Qualité des données'}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${sc.badge}`}>{dq.gate_status}</span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Couverture : {dq.coverage_pct}% &middot; Confiance : {dq.confidence_score}%
              </p>
            </div>
          </div>
          <button className="p-1 text-gray-400 hover:text-gray-600">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
            {/* Per-regulation coverage */}
            {dq.per_regulation && Object.entries(dq.per_regulation).map(([reg, info]) => (
              <div key={reg} className="flex items-center gap-3">
                <span className="text-xs font-medium text-gray-600 w-32 truncate">{REG_LABELS[`decret_${reg}`] || reg}</span>
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${info.status === 'OK' ? 'bg-green-500' : info.status === 'WARNING' ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${info.critical_total > 0 ? (info.critical_ok / info.critical_total) * 100 : 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">{info.critical_ok}/{info.critical_total}</span>
              </div>
            ))}

            {/* Missing critical fields */}
            {dq.missing_critical && dq.missing_critical.length > 0 && (
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="text-xs font-semibold text-red-700 uppercase mb-1">Données critiques manquantes</p>
                <div className="flex flex-wrap gap-1.5">
                  {dq.missing_critical.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
                      {m.field} ({m.regulation})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Missing optional fields */}
            {dq.missing_optional && dq.missing_optional.length > 0 && (
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Données optionnelles manquantes</p>
                <div className="flex flex-wrap gap-1.5">
                  {dq.missing_optional.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                      {m.field}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function ActionRow({ finding, onWorkflowAction, onCreateAction, onAuditFinding }) {
  const { isExpert } = useExpertMode();
  const ruleInfo = RULE_LABELS[finding.rule_id];
  const nextSteps = RULE_NEXT_STEPS[finding.rule_id] || [];
  const expectedProofs = RULE_EXPECTED_PROOFS[finding.rule_id] || [];
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg hover:bg-gray-50/50 transition-colors">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${finding.status === 'NOK' ? 'bg-red-500' : finding.status === 'UNKNOWN' ? 'bg-blue-400' : 'bg-amber-500'}`} />
        <button onClick={() => setExpanded(!expanded)} className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium text-gray-900 truncate">
            {finding.site_nom} — {ruleInfo?.title_fr || REG_LABELS[finding.regulation] || finding.regulation}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {ruleInfo?.why_fr || finding.evidence || 'Non conforme'}
          </p>
          {isExpert && <p className="text-[10px] text-gray-400 font-mono mt-0.5">{finding.rule_id}</p>}
        </button>
        <WorkflowBadge status={finding.insight_status} />
        <button
          onClick={() => onAuditFinding(finding.id)}
          className="text-xs text-indigo-500 hover:text-indigo-700 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
          title="Voir les détails"
        >
          <Eye size={12} /> Détails
        </button>
        {finding.insight_status === 'open' && (
          <button
            onClick={() => onWorkflowAction(finding.id, 'ack')}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
          >
            <UserCheck size={12} /> Prendre en charge
          </button>
        )}
        {finding.insight_status === 'ack' && (
          <button
            onClick={() => onWorkflowAction(finding.id, 'resolved')}
            className="text-xs text-green-600 hover:text-green-800 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-green-50 transition-colors"
          >
            <CheckCircle2 size={12} /> Résolu
          </button>
        )}
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 font-medium shrink-0">Recommandation</span>
        {finding.status === 'NOK' && (
          <Button size="sm" variant="secondary" onClick={() => onCreateAction(finding)}>
            <Plus size={12} /> Créer une action
          </Button>
        )}
      </div>

      {expanded && (nextSteps.length > 0 || expectedProofs.length > 0) && (
        <div className="px-4 pb-3 pt-1 border-t border-gray-100 grid grid-cols-2 gap-4">
          {nextSteps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-1">Prochaines étapes</p>
              <ul className="text-xs text-gray-600 space-y-0.5">
                {nextSteps.map((step, i) => <li key={i} className="flex items-start gap-1"><ChevronRight size={10} className="shrink-0 mt-0.5 text-blue-400" />{step}</li>)}
              </ul>
            </div>
          )}
          {expectedProofs.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-1">Preuves attendues</p>
              <ul className="text-xs text-gray-600 space-y-0.5">
                {expectedProofs.map((proof, i) => <li key={i} className="flex items-start gap-1"><FileText size={10} className="shrink-0 mt-0.5 text-indigo-400" />{proof}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ProofSection({ obligation, files, onUpload }) {
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_qualifier;

  return (
    <Card className={`border-l-4 ${cfg.border}`}>
      <CardBody>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="text-sm font-semibold text-gray-900">{obligation.regulation}</h4>
            <p className="text-xs text-gray-500">{obligation.sites_concernes} site(s) concerné(s)</p>
          </div>
          <Badge status={obligation.statut === 'conforme' ? 'ok' : obligation.statut === 'non_conforme' ? 'crit' : obligation.statut === 'a_qualifier' ? 'info' : 'warn'}>
            {cfg.label}
          </Badge>
        </div>
        {files.length > 0 && (
          <div className="space-y-1 mb-3">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded">
                <FileText size={14} className="text-indigo-500 shrink-0" />
                <span className="truncate flex-1">{f.name}</span>
                <span className="text-xs text-gray-400 whitespace-nowrap">{f.date}</span>
              </div>
            ))}
          </div>
        )}
        {files.length === 0 && (
          <div className="mb-3">
            {obligation.statut === 'conforme' && (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium mb-1">
                Preuve non jointe
              </span>
            )}
            <p className="text-xs text-gray-400">
              {obligation.statut === 'conforme'
                ? 'Vous pouvez joindre un justificatif pour renforcer la conformité.'
                : 'Aucune preuve jointe pour cette obligation.'}
            </p>
          </div>
        )}
        <label className="inline-flex items-center gap-2 cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 transition font-medium">
          <Upload size={14} />
          Ajouter un fichier
          <input type="file" className="sr-only" onChange={(e) => { if (e.target.files[0]) onUpload(obligation.id, e.target.files[0]); e.target.value = ''; }} />
        </label>
      </CardBody>
    </Card>
  );
}

export default function ConformitePage() {
  const { org, scope, scopedSites, portefeuilles, sitesCount } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [prefill, setPrefill] = useState(null);
  const [proofFiles, setProofFiles] = useState({});
  const [statusFilter, setStatusFilter] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [sitesData, setSitesData] = useState([]);
  const [auditFindingId, setAuditFindingId] = useState(null);
  const [activeTab, setActiveTab] = useState('obligations');
  const [intakeQuestions, setIntakeQuestions] = useState([]);
  const [emptyReason, setEmptyReason] = useState(null);
  const [error, setError] = useState(null);
  const [bundle, setBundle] = useState(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    const scopeParams = buildScopeParams({ orgId: org.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId }, scopedSites);

    getComplianceBundle(scopeParams)
      .then((b) => {
        const err = parseBundleError(b);
        if (err) { setError(err); return; }
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
        const reqUrl = err?.config?.baseURL && err?.config?.url
          ? `${err.config.baseURL}${err.config.url}`
          : null;
        if (reqUrl) base.request_url = reqUrl;
        setError(base);
      })
      .finally(() => setLoading(false));
  }, [org.id, scope.portefeuilleId, scope.siteId, scopedSites]);

  useEffect(() => { loadData(); }, [loadData]);

  // Load intake questions for Donnees tab
  useEffect(() => {
    if (scopedSites.length > 0) {
      getIntakeQuestions(scopedSites[0].id)
        .then(data => setIntakeQuestions(data.questions || []))
        .catch(() => setIntakeQuestions([]));
    }
  }, [scopedSites]);

  const obligations = useMemo(() => {
    if (!sitesData.length || !summary) return [];
    return sitesToObligations(sitesData, summary);
  }, [sitesData, summary]);

  const score = useMemo(() => {
    if (!summary) return { pct: 0, total: 0, non_conformes: 0, a_risque: 0, conformes: 0, total_impact_eur: 0 };
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
    () => computeScopeLabel(org, { siteId: scope.siteId, portefeuilleId: scope.portefeuilleId }, scopedSites, portefeuilles),
    [org, scope.siteId, scope.portefeuilleId, scopedSites, portefeuilles],
  );

  const sortedObligations = useMemo(() => {
    let list = [...obligations];
    if (statusFilter) {
      list = list.filter(o => o.statut === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(o =>
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
    return obligations.flatMap(o => o.findings)
      .filter(f => f.status === 'NOK' || f.status === 'UNKNOWN')
      .filter(f => f.insight_status !== 'resolved' && f.insight_status !== 'false_positive');
  }, [obligations]);

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      await recomputeComplianceRules(org.id);
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
    setPrefill({
      titre: `Mise en conformité ${obligation.regulation}`,
      type: 'conformite',
      priorite: obligation.severity === 'critical' ? 'critical' : obligation.severity === 'high' ? 'high' : 'medium',
      description: obligation.quoi_faire,
      obligation_code: obligation.code,
      impact_eur: obligation.impact_eur,
      site: `${obligation.sites_concernes} sites concernés`,
    });
    setShowCreate(true);
    track('conformite_create_action', { regulation: obligation.code });
  }

  function handleCreateFromFinding(finding) {
    setPrefill({
      titre: `Mise en conformité ${REG_LABELS[finding.regulation] || finding.regulation} — ${finding.site_nom}`,
      type: 'conformite',
      priorite: finding.severity === 'critical' ? 'critical' : finding.severity === 'high' ? 'high' : 'medium',
      description: finding.evidence || `Non conforme: ${finding.rule_id}`,
      obligation_code: finding.regulation,
      site: finding.site_nom,
    });
    setShowCreate(true);
    track('conformite_create_action_finding', { rule_id: finding.rule_id });
  }

  function handleSaveAction(action) {
    track('action_create_from_conformite', { titre: action.titre });
  }

  function handleUploadProof(obligationId, file) {
    const entry = { name: file.name, date: new Date().toLocaleDateString('fr-FR') };
    setProofFiles(prev => ({
      ...prev,
      [obligationId]: [...(prev[obligationId] || []), entry],
    }));
    track('proof_upload', { obligation_id: obligationId, file: file.name });
  }

  const overdueCount = obligations.filter(isOverdue).length;

  if (loading) {
    return (
      <PageShell icon={ShieldCheck} title="Conformité réglementaire" subtitle="Chargement...">
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="h-24 bg-gray-200 rounded-lg" />)}
          </div>
          <div className="h-40 bg-gray-200 rounded-lg" />
        </div>
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
      <PageShell icon={ShieldCheck} title="Conformité réglementaire"
                 subtitle={`${org.nom} · ${sitesCount} site${sitesCount !== 1 ? 's' : ''}`}>
        <ErrorState
          title="Erreur de chargement"
          message={error.message || 'Données de conformité indisponibles'}
          onRetry={() => { setError(null); loadData(); }}
          debug={isExpert && (error.error_code || error.status || error.request_url) ? {
            ...(error.status ? { status: error.status } : {}),
            ...(error.error_code ? { error_code: error.error_code } : {}),
            ...(error.trace_id ? { trace_id: error.trace_id } : {}),
            ...(error.hint ? { hint: error.hint } : {}),
            ...(error.request_url ? { request_url: error.request_url } : {}),
          } : null}
          actions={error.hint === 'run_reset_db' ? (
            <Button variant="secondary" onClick={handleResetDb}>
              <RotateCcw size={14} /> Reset DB (dev)
            </Button>
          ) : null}
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={ShieldCheck}
      title="Conformité réglementaire"
      subtitle={scopeLabel}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={handleRecompute} disabled={recomputing}>
            <RefreshCw size={14} className={recomputing ? 'animate-spin' : ''} />
            {recomputing ? 'Évaluation...' : 'Réévaluer'}
          </Button>
          <Button onClick={() => { setPrefill(null); setShowCreate(true); }}>
            <Plus size={16} /> Créer action conformité
          </Button>
        </>
      }
    >

      {/* Expert-only badges */}
      {isExpert && (
        <div className="flex items-center gap-2 -mt-1 mb-1">
          <DevApiBadge />
          <DevScopeBadge scope={{ orgId: org.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId }} scopedSites={scopedSites} />
          {bundle?.meta?.generated_at && (
            <span className="text-[10px] font-mono text-gray-400">
              Synthèse : {new Date(bundle.meta.generated_at).toLocaleTimeString('fr-FR')}
            </span>
          )}
        </div>
      )}

      {/* Cockpit Tabs */}
      <Tabs tabs={COCKPIT_TABS} active={activeTab} onChange={(tab) => { setActiveTab(tab); track('conformite_tab', { tab }); }} />

      {/* ======================== Tab: Obligations ======================== */}
      {activeTab === 'obligations' && (
        <>
          {/* Score + summary */}
          <div className="grid grid-cols-4 gap-4">
            <Card className="col-span-2">
              <CardBody>
                <ScoreGauge pct={score.pct} isEmpty={!!emptyReason && emptyReason !== 'ALL_COMPLIANT'} />
                <TrustBadge source="RegOps" period={`périmètre : ${scopedSites.length} sites`} confidence="medium" className="mt-2" />
              </CardBody>
            </Card>
            <Card
              className={`cursor-pointer transition hover:shadow-md ${statusFilter === 'non_conforme' ? 'ring-2 ring-red-400' : ''}`}
              onClick={() => setStatusFilter(statusFilter === 'non_conforme' ? null : 'non_conforme')}
            >
              <CardBody className="bg-red-50">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle size={16} className="text-red-600" />
                  <p className="text-xs text-gray-500 font-medium">Non conformes</p>
                </div>
                <p className="text-2xl font-bold text-red-700">{score.non_conformes}</p>
                <p className="text-xs text-gray-500 mt-1">sites</p>
              </CardBody>
            </Card>
            <Card
              className={`cursor-pointer transition hover:shadow-md ${statusFilter === 'a_risque' ? 'ring-2 ring-amber-400' : ''}`}
              onClick={() => setStatusFilter(statusFilter === 'a_risque' ? null : 'a_risque')}
            >
              <CardBody className="bg-amber-50">
                <div className="flex items-center gap-2 mb-1">
                  <Clock size={16} className="text-amber-600" />
                  <p className="text-xs text-gray-500 font-medium">À évaluer</p>
                </div>
                <p className="text-2xl font-bold text-amber-700">{score.a_risque}</p>
                <p className="text-xs text-gray-500 mt-1">sites</p>
              </CardBody>
            </Card>
          </div>

          {/* Active filter indicator */}
          {statusFilter && (
            <div className="flex items-center gap-2">
              <Badge status={statusFilter === 'non_conforme' ? 'crit' : 'warn'}>
                Filtre : {statusFilter === 'non_conforme' ? 'Non conformes' : 'À risque'}
              </Badge>
              <button
                onClick={() => setStatusFilter(null)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition"
              >
                <RotateCcw size={12} /> Réinitialiser
              </button>
            </div>
          )}

          {/* Overdue alert */}
          {overdueCount > 0 && !statusFilter && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle size={16} className="text-red-600" />
              <span className="text-sm font-medium text-red-700">
                {overdueCount} obligation(s) en retard — échéance(s) dépassée(s)
              </span>
            </div>
          )}

          {/* Obligations list */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">
                {statusFilter || searchQuery.trim() ? sortedObligations.length : score.total} Obligations réglementaires
              </h3>
              <div className="relative w-64">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Rechercher une obligation..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            {emptyReason && EMPTY_REASONS[emptyReason] ? (
              <EmptyState
                icon={EMPTY_REASONS[emptyReason].Icon || ShieldCheck}
                title={EMPTY_REASONS[emptyReason].title}
                text={EMPTY_REASONS[emptyReason].text}
                ctaLabel={EMPTY_REASONS[emptyReason].ctaLabel}
                onCta={EMPTY_REASONS[emptyReason].ctaPath ? () => navigate(EMPTY_REASONS[emptyReason].ctaPath) : undefined}
              />
            ) : sortedObligations.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title="Aucune obligation détectée"
                text="Cliquez Réévaluer pour lancer l'évaluation, ou ajoutez des sites à votre patrimoine."
                ctaLabel="Aller au patrimoine"
              />
            ) : (
              <div className="space-y-3">
                {sortedObligations.map((o) => (
                  <ObligationCard
                    key={o.id}
                    obligation={o}
                    onCreateAction={handleCreateFromObligation}
                    onWorkflowAction={handleWorkflowAction}
                    onUploadProof={handleUploadProof}
                    proofFiles={proofFiles}
                    onAuditFinding={setAuditFindingId}
                    bacsV2Summary={o.code === 'bacs' ? bacsV2Summary : undefined}
                    onNavigateIntake={o.code === 'bacs' && scopedSites[0] ? () => { navigate(`/intake/${scopedSites[0].id}`); track('bacs_complete_data'); } : undefined}
                  />
                ))}
              </div>
            )}
          </div>

          {/* KB Obligations (from knowledge base apply engine) */}
          <KBObligationsSection scopedSites={scopedSites} />
        </>
      )}

      {/* ======================== Tab: Donnees & Qualite ======================== */}
      {activeTab === 'donnees' && (
        <div className="space-y-4">
          {scopedSites.length === 0 ? (
            <EmptyState icon={Database} title="Aucun site dans le périmètre" text="Ajoutez des sites pour analyser la qualité des données." />
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Database size={16} className="text-blue-600" />
                <h3 className="text-sm font-semibold text-gray-700">Qualité des données par site ({scopedSites.length})</h3>
              </div>
              {scopedSites.map(site => (
                <DataQualityGate key={site.id} siteId={site.id} siteName={site.nom} />
              ))}

              {/* Smart Intake questions */}
              {intakeQuestions.length > 0 && (
                <Card>
                  <CardBody>
                    <div className="flex items-center gap-2 mb-3">
                      <ClipboardList size={16} className="text-indigo-600" />
                      <h3 className="text-sm font-semibold text-gray-700">Questions en attente ({intakeQuestions.length})</h3>
                    </div>
                    <div className="space-y-2">
                      {intakeQuestions.slice(0, 5).map((q, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                          <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                            q.severity === 'critical' ? 'bg-red-500' : q.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'
                          }`} />
                          <div className="flex-1">
                            <p className="text-sm text-gray-800">{q.question}</p>
                            {q.help && <p className="text-xs text-gray-500 mt-0.5">{q.help}</p>}
                            <div className="flex items-center gap-2 mt-1">
                              {q.regulations?.map(r => (
                                <span key={r} className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">{REG_LABELS[r] || r}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    {intakeQuestions.length > 5 && (
                      <p className="text-xs text-gray-400 mt-2">+ {intakeQuestions.length - 5} autres questions</p>
                    )}
                    <Button
                      variant="secondary"
                      size="sm"
                      className="mt-3"
                      onClick={() => { navigate(`/intake/${scopedSites[0]?.id}`); track('conformite_goto_intake'); }}
                    >
                      Compléter le questionnaire
                    </Button>
                  </CardBody>
                </Card>
              )}
            </>
          )}
        </div>
      )}

      {/* ======================== Tab: Plan d'execution ======================== */}
      {activeTab === 'execution' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ClipboardList size={16} className="text-blue-600" />
              <h3 className="text-sm font-semibold text-gray-700">
                Recommandations ({actionableFindings.length})
              </h3>
            </div>
            {actionableFindings.length > 0 && (
              <Button variant="secondary" size="sm" onClick={() => { setPrefill(null); setShowCreate(true); }}>
                <Plus size={14} /> Nouvelle action
              </Button>
            )}
          </div>

          {actionableFindings.length === 0 ? (
            <EmptyState
              icon={CheckCircle}
              title="Aucune action en attente"
              text={emptyReason === 'ALL_COMPLIANT'
                ? 'Toutes les obligations sont conformes. Aucune action requise.'
                : 'Lancez une évaluation pour identifier les actions nécessaires.'}
            />
          ) : (
            <div className="space-y-2">
              {actionableFindings.map(f => (
                <ActionRow
                  key={f.id}
                  finding={f}
                  onWorkflowAction={handleWorkflowAction}
                  onCreateAction={handleCreateFromFinding}
                  onAuditFinding={setAuditFindingId}
                />
              ))}
            </div>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => { navigate('/plan-actions'); track('conformite_goto_plan_actions'); }}
          >
            <ExternalLink size={14} /> Voir le plan d'actions complet
          </Button>
        </div>
      )}

      {/* ======================== Tab: Preuves & Rapports ======================== */}
      {activeTab === 'preuves' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <FolderOpen size={16} className="text-indigo-600" />
            <h3 className="text-sm font-semibold text-gray-700">Preuves par obligation ({obligations.length})</h3>
          </div>

          {obligations.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="Aucune obligation"
              text="Lancez une évaluation pour voir les obligations et joindre des preuves."
            />
          ) : (
            <>
              {obligations.map(o => (
                <ProofSection
                  key={o.id}
                  obligation={o}
                  files={proofFiles[o.id] || []}
                  onUpload={handleUploadProof}
                />
              ))}
            </>
          )}

          <TrustBadge source="Preuves locales" period="Téléversement local (non enregistré)" confidence="low" />
        </div>
      )}

      {/* Create Action Modal */}
      <CreateActionModal
        open={showCreate}
        onClose={() => { setShowCreate(false); setPrefill(null); }}
        onSave={handleSaveAction}
        prefill={prefill}
      />

      {/* Finding Audit Drawer */}
      <FindingAuditDrawer
        findingId={auditFindingId}
        onClose={() => setAuditFindingId(null)}
      />
    </PageShell>
  );
}
