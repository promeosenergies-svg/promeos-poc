/**
 * PROMEOS - Conformite (/conformite) V92
 * Cockpit RegOps: 4 tabs (Obligations, Donnees & Qualite, Plan d'execution, Preuves & Rapports).
 * Scope filtering (org/entity/site), empty state reason codes, workflow actions.
 * Sub-components extracted to conformite-tabs/ (V92 split).
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ShieldCheck,
  Plus,
  RotateCcw,
  RefreshCw,
  Database,
  Coins,
  ArrowRight,
  CalendarClock,
} from 'lucide-react';
import { Button, PageShell, Drawer, ActiveFiltersBar, Explain } from '../ui';
import { getKpiMessage } from '../services/kpiMessaging';
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
import { computeObligationProfileTags } from '../models/complianceProfileRules';
import HealthSummary from '../components/HealthSummary';
import DossierPrintView from '../components/DossierPrintView';
import RegulatoryTimeline from '../components/compliance/RegulatoryTimeline';
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
  getComplianceTimeline,
  getSegmentationProfile,
} from '../services/api';
import { getComplianceScoreColor, COMPLIANCE_SCORE_THRESHOLDS } from '../lib/constants';

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
      {!isOk && <span className="ml-1 text-[9px] text-red-500">API indisponible</span>}
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
  // Seuil applicable = base sur le putile max reel (pas le max des seuils)
  const applicableThreshold = maxPutile >= 290 ? 290 : 70;
  const triExemption = entries.some((e) => e.tri_exemption);
  return {
    applicable,
    deadline: closest,
    putile_kw: maxPutile || null,
    threshold_kw: applicableThreshold || null,
    tier: maxPutile >= 290 ? 'TIER1' : 'TIER2',
    tri_exemption: triExemption,
  };
}

/**
 * Compute human-readable scope label.
 * Exported for testing.
 */
export function computeScopeLabel(org, scope, scopedSites, portefeuilles) {
  const orgName = org?.nom || 'Societe';
  if (scope?.siteId) {
    const site = scopedSites?.[0];
    return `${orgName} · Site: ${site?.nom || scope.siteId}`;
  }
  if (scope?.portefeuilleId) {
    const pf = portefeuilles?.find((p) => p.id === scope.portefeuilleId);
    return `${orgName} · Portefeuille: ${pf?.nom || scope.portefeuilleId} (${scopedSites?.length || 0} sites)`;
  }
  return `${orgName} · Societe (${scopedSites?.length || 0} sites)`;
}

export function isOverdue(obligation) {
  if (!obligation.echeance || obligation.statut === 'conforme') return false;
  return new Date(obligation.echeance) < new Date();
}

/**
 * Format a deadline date with contextual wording.
 * Past deadlines for non-conforme obligations show "Échéance dépassée depuis le …"
 * Future deadlines show the date normally.
 */
export function formatDeadline(echeance, statut) {
  if (!echeance) return null;
  const d = new Date(echeance);
  const formatted = d.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
  if (statut !== 'conforme' && d < new Date()) {
    return { text: `Échéance dépassée depuis le ${formatted}`, overdue: true };
  }
  return { text: formatted, overdue: false };
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
      // CEE = incentive, not obligation — skip here
      if (f.category === 'incentive' || (f.regulation || '').toLowerCase().includes('cee'))
        continue;
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

/**
 * Extract CEE/incentive findings from sitesData (separated from obligations).
 */
export function sitesToIncentives(sitesData) {
  if (!sitesData || !sitesData.length) return [];
  const items = [];
  for (const site of sitesData) {
    for (const f of site.findings) {
      if (f.category === 'incentive' || (f.regulation || '').toLowerCase().includes('cee')) {
        items.push({ ...f, site_nom: site.site_nom, site_id: site.site_id });
      }
    }
  }
  return items;
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
    <Drawer
      open={!!findingId}
      onClose={onClose}
      title={<Explain term="finding">{DRAWER_LABELS.finding_title}</Explain>}
      wide
    >
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
                <span className="text-gray-500">
                  <Explain term="severite">{DRAWER_LABELS.severity}</Explain> :
                </span>{' '}
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
                  <span className="font-medium">
                    {new Date(detail.deadline).toLocaleDateString('fr-FR', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </span>
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

/**
 * ComplianceSummaryBanner — Bandeau contextuel 3 états (vert/rouge/ambre).
 * Affiche un message actionnable + CTA selon le niveau de conformité.
 */
function ComplianceSummaryBanner({ score, obligations, timeline, isExpert, navigate }) {
  const nextDeadline = timeline?.next_deadline || null;
  const pct = score?.pct ?? 0;
  const nonConformes = score?.non_conformes ?? 0;
  const aRisque = score?.a_risque ?? 0;
  const totalSites = score?.total ?? 0;

  // Determine state: green (>=70 & 0 NC), red (<40 or NC>0), amber (else)
  let state = 'amber';
  if (pct >= 70 && nonConformes === 0) state = 'green';
  else if (pct < 40 || nonConformes > 0) state = 'red';

  const stateConfig = {
    green: {
      bg: 'bg-green-50 border-green-200',
      iconColor: 'text-green-600',
      textColor: 'text-green-800',
      subColor: 'text-green-600',
    },
    amber: {
      bg: 'bg-amber-50 border-amber-200',
      iconColor: 'text-amber-600',
      textColor: 'text-amber-800',
      subColor: 'text-amber-600',
    },
    red: {
      bg: 'bg-red-50 border-red-200',
      iconColor: 'text-red-600',
      textColor: 'text-red-800',
      subColor: 'text-red-600',
    },
  };

  const cfg = stateConfig[state];

  // kpiMessaging for conformite
  const conformiteMsg = getKpiMessage('conformite', pct, {
    totalSites,
    sitesAtRisk: aRisque,
    sitesNonConformes: nonConformes,
  });
  // kpiMessaging for risque
  const risqueMsg = getKpiMessage('risque', score?.total_impact_eur ?? 0, {
    sitesAtRisk: aRisque,
  });

  return (
    <div
      data-testid="compliance-summary-banner"
      data-state={state}
      className={`p-4 border rounded-lg ${cfg.bg}`}
    >
      <div className="flex items-start gap-3">
        <ShieldCheck size={20} className={`${cfg.iconColor} mt-0.5 shrink-0`} />
        <div className="flex-1 min-w-0">
          {/* Main message from kpiMessaging */}
          {conformiteMsg && (
            <p
              className={`text-sm font-medium ${cfg.textColor}`}
              data-testid="kpi-message-conformite"
            >
              {isExpert ? conformiteMsg.expert : conformiteMsg.simple}
            </p>
          )}
          {/* Risque message */}
          {risqueMsg && risqueMsg.severity !== 'ok' && (
            <p className={`text-xs mt-1 ${cfg.subColor}`} data-testid="kpi-message-risque">
              {isExpert ? risqueMsg.expert : risqueMsg.simple}
            </p>
          )}
          {/* Next deadline */}
          {nextDeadline && (
            <p
              className="text-xs mt-1.5 flex items-center gap-1 text-gray-600"
              data-testid="next-deadline"
            >
              <CalendarClock size={12} />
              Prochaine échéance : {nextDeadline.label || nextDeadline.regulation} —{' '}
              {new Date(nextDeadline.deadline).toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
              {nextDeadline.days_remaining != null && (
                <span
                  className={nextDeadline.days_remaining <= 30 ? 'font-semibold text-red-600' : ''}
                >
                  {' '}
                  (dans {nextDeadline.days_remaining} jour
                  {nextDeadline.days_remaining > 1 ? 's' : ''})
                </span>
              )}
            </p>
          )}
        </div>
        {/* CTA buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {state === 'red' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                navigate('/actions');
              }}
              data-testid="cta-plan-action"
            >
              Voir le plan d&apos;action <ArrowRight size={14} />
            </Button>
          )}
          {state === 'amber' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                navigate('/conformite?tab=execution');
              }}
              data-testid="cta-preparer-echeances"
            >
              Préparer les échéances <ArrowRight size={14} />
            </Button>
          )}
        </div>
      </div>

      {/* B2 — Résumé exécutif 1 ligne */}
      {(() => {
        const oblCount = obligations?.length || 0;
        const ncCount = nonConformes;
        const urgentDeadline = nextDeadline?.days_remaining;
        const urgentLabel =
          urgentDeadline != null && urgentDeadline <= 90
            ? `1 échéance sous ${urgentDeadline} jour${urgentDeadline > 1 ? 's' : ''}`
            : null;
        const parts = [
          `${oblCount} obligation${oblCount > 1 ? 's' : ''} active${oblCount > 1 ? 's' : ''}`,
          ncCount > 0 ? `${ncCount} non conforme${ncCount > 1 ? 's' : ''}` : null,
          aRisque > 0 ? `${aRisque} à qualifier` : null,
          urgentLabel,
        ].filter(Boolean);
        if (parts.length === 0) return null;
        return (
          <p data-testid="executive-summary" className="text-xs text-gray-600 mt-2 font-medium">
            {parts.join(' · ')}
          </p>
        );
      })()}

      {/* B2 — Top 3 urgences */}
      {(() => {
        if (!obligations?.length) return null;
        // Compute urgency: severity × proximity × penalty
        const sevWeight = { critical: 100, high: 70, medium: 40, low: 10 };
        const scored = obligations
          .filter((o) => o.statut !== 'conforme' && o.statut !== 'hors_perimetre')
          .map((o) => {
            const sev = sevWeight[o.severity] || 10;
            const daysLeft = o.echeance
              ? Math.max(0, (new Date(o.echeance) - new Date()) / 86400000)
              : 999;
            const proximity = daysLeft <= 0 ? 100 : daysLeft <= 90 ? 80 : daysLeft <= 365 ? 50 : 20;
            const penalty = (o.findings || []).reduce(
              (s, f) => s + (f.estimated_penalty_eur || 0),
              0
            );
            return {
              ...o,
              _urgency: sev * 0.4 + proximity * 0.4 + Math.min(penalty / 100, 20) * 0.2,
            };
          })
          .sort((a, b) => b._urgency - a._urgency)
          .slice(0, 3);
        if (scored.length === 0) return null;
        return (
          <div
            data-testid="top3-urgences"
            className="mt-3 p-3 bg-white/60 rounded-lg border border-gray-200/50"
          >
            <p className="text-xs font-semibold text-gray-700 uppercase mb-2">
              Top {scored.length} urgence{scored.length > 1 ? 's' : ''}
            </p>
            <div className="space-y-1.5">
              {scored.map((o, i) => (
                <div key={o.id} className="flex items-center gap-2 text-sm">
                  <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      o.severity === 'critical'
                        ? 'bg-red-500'
                        : o.severity === 'high'
                          ? 'bg-orange-500'
                          : 'bg-amber-400'
                    }`}
                  />
                  <span className="font-medium text-gray-800 flex-1 truncate">{o.regulation}</span>
                  {o.echeance &&
                    (() => {
                      const dl = formatDeadline(o.echeance, o.statut);
                      return (
                        <span
                          className={`text-xs ${dl.overdue ? 'text-red-600 font-semibold' : 'text-gray-500'}`}
                        >
                          {dl.text}
                        </span>
                      );
                    })()}
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      o.statut === 'non_conforme'
                        ? 'bg-red-50 text-red-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}
                  >
                    {o.statut === 'non_conforme' ? 'Non conforme' : 'À qualifier'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
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
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'obligations');
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

  // V1.3: Fetch segmentation profile for "Adapté à votre profil" badge
  useEffect(() => {
    getSegmentationProfile()
      .then((p) => setSegProfile(p))
      .catch(() => setSegProfile(null));
  }, []);

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
  }, [obligations, statusFilter, searchQuery, profileTags]);

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
        <div
          data-section="compliance-score-header"
          className="p-4 bg-white border border-gray-200 rounded-lg"
        >
          <div className="flex items-center gap-6">
            {/* Score display */}
            <div className="text-center min-w-[100px]">
              <p className="text-xs text-gray-500 mb-1">Score conformité</p>
              <span
                className={`text-3xl font-bold ${getComplianceScoreColor(complianceScore.score ?? complianceScore.avg_score)}`}
              >
                {Math.round(complianceScore.score ?? complianceScore.avg_score ?? 0)}
              </span>
              <span className="text-lg text-gray-400">/100</span>
              {segProfile?.has_profile && Object.keys(segProfile.answers || {}).length > 0 && (
                <>
                  <p
                    className="text-[10px] text-blue-600 font-medium mt-1"
                    data-testid="profile-badge"
                  >
                    Adapté à votre profil
                  </p>
                  <p className="text-[9px] text-gray-400 mt-0.5" data-testid="profile-explain">
                    Certaines obligations et priorités sont ajustées selon votre profil déclaré ou
                    détecté.
                  </p>
                </>
              )}
            </div>
            {/* Breakdown bars */}
            <div className="flex-1 space-y-2">
              {(complianceScore.breakdown || []).map((fw) => {
                const fwLabel =
                  fw.framework === 'tertiaire_operat'
                    ? 'Décret Tertiaire'
                    : fw.framework === 'bacs'
                      ? 'BACS'
                      : 'APER';
                const weightPct = fw.weight != null ? `${Math.round(fw.weight * 100)}%` : '';
                const isAvailable = fw.available !== false && fw.source !== 'default';
                return (
                  <div key={fw.framework} className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-36 truncate">
                      {fwLabel}
                      {weightPct && isAvailable ? ` (${weightPct})` : ''}
                    </span>
                    {isAvailable ? (
                      <>
                        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${fw.score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : fw.score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${Math.min(100, fw.score)}%` }}
                          />
                        </div>
                        <span
                          className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(fw.score)}`}
                        >
                          {Math.round(fw.score)}
                        </span>
                      </>
                    ) : (
                      <span className="text-xs text-gray-400 italic">Non applicable</span>
                    )}
                  </div>
                );
              })}
              {/* Fallback: show breakdown_avg from portfolio if no breakdown */}
              {!complianceScore.breakdown &&
                complianceScore.breakdown_avg &&
                Object.entries(complianceScore.breakdown_avg).map(([fw, score]) => {
                  const fwLabel =
                    fw === 'tertiaire_operat'
                      ? 'Décret Tertiaire'
                      : fw === 'bacs'
                        ? 'BACS'
                        : 'APER';
                  return (
                    <div key={fw} className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 w-36 truncate">{fwLabel}</span>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min(100, score)}%` }}
                        />
                      </div>
                      <span
                        className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(score)}`}
                      >
                        {Math.round(score)}
                      </span>
                    </div>
                  );
                })}
            </div>
            {/* Confidence */}
            {(complianceScore.confidence || complianceScore.high_confidence_count != null) && (
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Confiance</p>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    complianceScore.confidence === 'high' ||
                    complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6
                      ? 'bg-green-100 text-green-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {complianceScore.confidence === 'high' ||
                  complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6
                    ? 'Données fiables'
                    : 'Données partielles'}
                </span>
              </div>
            )}
          </div>
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

      {/* Financements mobilisables (CEE) — masqué V1.2, prévu évolution future */}
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

      {/* Finding Audit Drawer */}
      <FindingAuditDrawer findingId={auditFindingId} onClose={() => setAuditFindingId(null)} />

      {/* Dossier print view (Étape 5) */}
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
