/**
 * ObligationsTab — Extracted from ConformitePage (V92 split)
 * Tab "Obligations" with ScoreGauge, ObligationCards, KBObligationsSection.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  ChevronDown,
  ChevronUp,
  Plus,
  Upload,
  BookOpen,
  ExternalLink,
  Zap,
  Search,
  UserCheck,
  CheckCircle2,
  XCircle,
  Eye,
  Printer,
  Coins,
  Scale,
  Info,
  Lightbulb,
  Shield,
  Building2,
  ArrowRight,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge, Explain } from '../../ui';
import { fmtEur } from '../../utils/format';
import { useExpertMode } from '../../contexts/ExpertModeContext';
import { track } from '../../services/tracker';
import { applyKB } from '../../services/api';
import { getKpiMessage } from '../../services/kpiMessaging';
import {
  STATUT_LABELS,
  SEVERITY_LABELS,
  SEVERITY_BADGE_MAP,
  CONFIDENCE_LABELS,
  WORKFLOW_LABELS,
  RULE_LABELS,
  RULE_LEGAL_REFS,
  RULE_OPTIONS,
  RULE_EXPECTED_PROOFS,
} from '../../domain/compliance/complianceLabels.fr';
import { isOverdue, formatDeadline } from '../ConformitePage';

const SEVERITY_BADGE = SEVERITY_BADGE_MAP;

const STATUT_CONFIG = {
  non_conforme: {
    label: STATUT_LABELS.non_conforme,
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: AlertTriangle,
  },
  a_risque: {
    label: STATUT_LABELS.a_risque,
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: Clock,
  },
  a_qualifier: {
    label: STATUT_LABELS.a_qualifier,
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: Search,
  },
  conforme: {
    label: STATUT_LABELS.conforme,
    color: 'text-green-700',
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: CheckCircle,
  },
};

const WORKFLOW_CONFIG = {
  open: { label: WORKFLOW_LABELS.open, color: 'bg-red-50 text-red-700' },
  ack: { label: WORKFLOW_LABELS.ack, color: 'bg-amber-50 text-amber-700' },
  resolved: { label: WORKFLOW_LABELS.resolved, color: 'bg-green-50 text-green-700' },
  false_positive: { label: WORKFLOW_LABELS.false_positive, color: 'bg-gray-100 text-gray-500' },
};

function WorkflowBadge({ status }) {
  const cfg = WORKFLOW_CONFIG[status] || WORKFLOW_CONFIG.open;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}
    >
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
          <p className="text-xs text-gray-500 mt-1">
            <Explain term="compliance_score">Score de conformité global</Explain>
          </p>
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
          <div
            className={`h-full ${fill} rounded-full transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          <Explain term="compliance_score">Score de conformité global</Explain>
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Score = sites conformes / sites évalués (pondéré par criticité)
        </p>
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
    const maxSurface = Math.max(...scopedSites.map((s) => s.surface_m2 || 0), 0);
    const estHvacKw = Math.round(maxSurface * 0.1);
    const largeSites = scopedSites.filter((s) => (s.surface_m2 || 0) >= 2000);
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
      .then((data) => {
        setKbResult(data);
        setKbError(false);
      })
      .catch(() => {
        setKbError(true);
      })
      .finally(() => setKbLoading(false));
  }, [scopedSites]);

  if (kbLoading) {
    return (
      <Card>
        <CardBody className="text-center py-6">
          <BookOpen size={24} className="text-blue-300 mx-auto mb-2 animate-pulse" />
          <p className="text-sm text-gray-400">Analyse réglementaire KB en cours…</p>
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
                    <Badge status={SEVERITY_BADGE[item.severity] || 'neutral'}>
                      {SEVERITY_LABELS[item.severity] || item.severity}
                    </Badge>
                    {item.confidence && (
                      <Badge status={item.confidence === 'high' ? 'ok' : 'neutral'}>
                        {CONFIDENCE_LABELS[item.confidence] || item.confidence}
                      </Badge>
                    )}
                    {item.domain && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-red-50 text-red-700">
                        {item.domain}
                      </span>
                    )}
                  </div>
                  <h4 className="text-sm font-semibold text-gray-900 leading-tight">
                    {item.title}
                  </h4>
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
                      <p className="text-xs font-semibold text-blue-600 uppercase mb-1">
                        Pourquoi applicable
                      </p>
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
                      <p className="text-xs font-semibold text-amber-700 uppercase mb-1">
                        Actions / Obligations
                      </p>
                      {item.logic.then.outputs.map((output, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 text-xs text-amber-800 mt-1"
                        >
                          <span
                            className={`inline-block w-2 h-2 rounded-full ${
                              output.severity === 'critical'
                                ? 'bg-red-500'
                                : output.severity === 'high'
                                  ? 'bg-orange-500'
                                  : 'bg-blue-500'
                            }`}
                          />
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
                      <p className="text-xs font-semibold text-gray-500 mb-1">
                        Sources réglementaires
                      </p>
                      {item.sources.map((src, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                          <ExternalLink size={12} />
                          <span>
                            {src.label}
                            {src.section ? ` - ${src.section}` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {item.tags && (
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(item.tags).map(
                        ([cat, values]) =>
                          Array.isArray(values) &&
                          values.map((v) => (
                            <span
                              key={`${cat}-${v}`}
                              className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                            >
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
              <p className="text-xs font-semibold text-amber-700">
                Données manquantes pour une analyse complète
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.map((field) => (
                <span
                  key={field}
                  className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-xs font-medium"
                >
                  {field}
                </span>
              ))}
            </div>
            {suggestions.length > 0 && (
              <p className="text-xs text-gray-500 mt-2">{suggestions.join(' ')}</p>
            )}
          </CardBody>
        </Card>
      )}

      <TrustBadge
        source="PROMEOS KB"
        period="Analyse réglementaire automatique"
        confidence="high"
      />
    </div>
  );
}

function ObligationCard({
  obligation,
  onCreateAction,
  onExportDossier,
  onWorkflowAction,
  onUploadProof,
  proofFiles,
  onAuditFinding,
  bacsV2Summary,
  onNavigateIntake,
  isExpert,
  profileEntry,
}) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_qualifier;
  const Icon = cfg.icon;
  const overdue = isOverdue(obligation);
  const pctConforme =
    obligation.sites_concernes > 0
      ? Math.round((obligation.sites_conformes / obligation.sites_concernes) * 100)
      : 100;
  const files = proofFiles[obligation.id] || [];

  return (
    <Card className={`border-l-4 ${cfg.border}`}>
      <CardBody>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5`}>
              <Icon size={18} className={cfg.color} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-gray-900">{obligation.regulation}</h3>
                <Badge status={SEVERITY_BADGE[obligation.severity] || 'neutral'}>
                  {SEVERITY_LABELS[obligation.severity] || obligation.severity}
                </Badge>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>
                  {cfg.label}
                </span>
                {overdue && <Badge status="crit">En retard</Badge>}
                {/* V1.4: profile tags */}
                {profileEntry?.tags?.map((tag, i) => (
                  <span
                    key={i}
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      tag.color === 'green'
                        ? 'bg-green-100 text-green-700'
                        : tag.color === 'blue'
                          ? 'bg-blue-100 text-blue-700'
                          : tag.color === 'amber'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-gray-100 text-gray-500'
                    }`}
                    title={tag.tooltip}
                    data-testid="profile-tag"
                  >
                    {tag.label}
                  </span>
                ))}
                {profileEntry?.reliability && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded ${
                      profileEntry.reliability === 'declared'
                        ? 'bg-blue-50 text-blue-500'
                        : profileEntry.reliability === 'detected'
                          ? 'bg-gray-50 text-gray-400'
                          : 'bg-amber-50 text-amber-500'
                    }`}
                    title={
                      profileEntry.reliability === 'declared'
                        ? 'Ajusté selon vos réponses'
                        : profileEntry.reliability === 'detected'
                          ? 'Calculé depuis vos données patrimoine'
                          : 'Information insuffisante — qualification recommandée'
                    }
                    data-testid="reliability-badge"
                  >
                    {profileEntry.reliability === 'declared'
                      ? 'Déclaré'
                      : profileEntry.reliability === 'detected'
                        ? 'Détecté'
                        : 'À confirmer'}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mt-1">{obligation.description}</p>
            </div>
          </div>
          <button
            onClick={() => {
              setExpanded(!expanded);
              track('obligation_toggle', { code: obligation.code, expanded: !expanded });
            }}
            className="p-1 hover:bg-gray-100 rounded transition ml-2"
          >
            {expanded ? (
              <ChevronUp size={18} className="text-gray-400" />
            ) : (
              <ChevronDown size={18} className="text-gray-400" />
            )}
          </button>
        </div>

        <div className="flex items-center gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-500">Sites concernés : </span>
            <span className="font-medium text-gray-800">{obligation.sites_concernes}</span>
          </div>
          <div>
            <span className="text-gray-500">Conformes : </span>
            <span className="font-medium text-green-700">
              {obligation.sites_conformes}/{obligation.sites_concernes}
            </span>
            <span className="text-gray-400 ml-1">({pctConforme}%)</span>
          </div>
          {obligation.echeance &&
            (() => {
              const dl = formatDeadline(obligation.echeance, obligation.statut);
              return (
                <div className="flex items-center gap-1">
                  <Clock size={14} className={dl.overdue ? 'text-red-500' : 'text-gray-400'} />
                  <span className={`font-medium ${dl.overdue ? 'text-red-600' : 'text-gray-800'}`}>
                    {dl.text}
                  </span>
                </div>
              );
            })()}
        </div>

        {obligation.code === 'bacs' && bacsV2Summary && (
          <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${
                bacsV2Summary.applicable
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {bacsV2Summary.applicable ? 'Assujetti BACS' : 'Non assujetti'}
            </span>
            {bacsV2Summary.threshold_kw && (
              <span className="text-gray-600">
                Seuil: {bacsV2Summary.threshold_kw >= 290 ? '\u2265290 kW' : '\u226570 kW'}
                {bacsV2Summary.putile_kw ? ` (Putile: ${bacsV2Summary.putile_kw} kW)` : ''}
              </span>
            )}
            {bacsV2Summary.deadline && (
              <span
                className={`flex items-center gap-1 ${
                  new Date(bacsV2Summary.deadline) < new Date()
                    ? 'text-red-600 font-semibold'
                    : 'text-gray-600'
                }`}
              >
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

        {obligation.code === 'bacs' && !bacsV2Summary && onNavigateIntake && (
          <div className="mt-2 p-3 bg-blue-50 rounded-lg flex items-center gap-3">
            <AlertTriangle size={16} className="text-blue-600 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-700">Données BACS incomplètes</p>
              <p className="text-xs text-blue-600">
                Complétez les données pour déterminer l'applicabilité et l'échéance.
              </p>
            </div>
            <Button size="sm" variant="secondary" onClick={onNavigateIntake}>
              Compléter données BACS
            </Button>
          </div>
        )}

        {obligation.code === 'decret_tertiaire_operat' && (
          <div className="mt-2 p-3 bg-emerald-50 rounded-lg flex items-center gap-3">
            <Building2 size={16} className="text-emerald-600 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-700">Module OPERAT</p>
              <p className="text-xs text-emerald-600">
                Gérez vos EFA, contrôlez la qualité des données et préparez vos déclarations.
              </p>
            </div>
            <Button size="sm" variant="secondary" onClick={() => navigate('/conformite/tertiaire')}>
              <ArrowRight size={14} className="mr-1" /> Ouvrir OPERAT
            </Button>
          </div>
        )}

        <div className="mt-3">
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${pctConforme}%` }}
            />
          </div>
        </div>

        {obligation.statut !== 'conforme' && !expanded && (
          <div className="mt-3 flex items-center gap-2">
            <Button onClick={() => onCreateAction(obligation)} size="sm" variant="secondary">
              <Plus size={14} /> Créer action
            </Button>
            {onExportDossier && (
              <Button onClick={() => onExportDossier(obligation)} size="sm" variant="secondary">
                <Printer size={14} /> Dossier
              </Button>
            )}
          </div>
        )}

        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs font-semibold text-blue-600 uppercase mb-1">
                  Pourquoi concerné
                </p>
                <p className="text-sm text-gray-700">{obligation.pourquoi}</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs font-semibold text-amber-600 uppercase mb-1">
                  Ce qu'il faut faire
                </p>
                <p className="text-sm text-gray-700">{obligation.quoi_faire}</p>
              </div>
            </div>

            {/* A5 — Base légale */}
            {(() => {
              const mainRuleId = obligation.findings?.[0]?.rule_id;
              const legalRef = mainRuleId && RULE_LEGAL_REFS[mainRuleId];
              if (!legalRef) return null;
              return (
                <div className="flex items-start gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <Scale size={14} className="text-slate-500 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-600 uppercase mb-0.5">
                      Base légale
                    </p>
                    <p className="text-sm text-gray-700">{legalRef.ref}</p>
                    {legalRef.url && (
                      <a
                        href={legalRef.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline flex items-center gap-1 mt-1"
                      >
                        <ExternalLink size={10} /> Source officielle
                      </a>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* A3 — Vos options */}
            {(() => {
              const mainRuleId = obligation.findings?.[0]?.rule_id;
              const opts = mainRuleId && RULE_OPTIONS[mainRuleId];
              if (!opts || !opts.options?.length) return null;
              return (
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb size={14} className="text-emerald-600" />
                    <p className="text-xs font-semibold text-emerald-700 uppercase">Vos options</p>
                  </div>
                  <ul className="space-y-1">
                    {opts.options.map((opt, i) => (
                      <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                        <span className="text-emerald-500 mt-1 shrink-0">•</span>
                        {opt}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })()}

            {/* A6 — Pénalités sourcées (si penalties dans les findings) */}
            {(() => {
              const findingsWithPenalty = (obligation.findings || []).filter(
                (f) => f.estimated_penalty_eur > 0
              );
              if (findingsWithPenalty.length === 0) return null;
              const totalPenalty = findingsWithPenalty.reduce(
                (s, f) => s + (f.estimated_penalty_eur || 0),
                0
              );
              return (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Coins size={14} className="text-red-600" />
                    <p className="text-xs font-semibold text-red-700 uppercase">
                      Risque financier estimé
                    </p>
                    <span className="text-sm font-bold text-red-700 ml-auto">
                      {fmtEur(totalPenalty)}
                    </span>
                  </div>
                  {findingsWithPenalty.map((f) => (
                    <div key={f.id} className="flex items-center gap-3 text-xs text-gray-700 mt-1">
                      <span className="font-medium truncate flex-1">{f.site_nom}</span>
                      <span className="text-red-600 font-semibold">
                        {fmtEur(f.estimated_penalty_eur)}
                      </span>
                      {f.penalty_source && (
                        <span className="text-gray-500 italic">({f.penalty_source})</span>
                      )}
                      {f.penalty_basis && <span className="text-gray-400">{f.penalty_basis}</span>}
                    </div>
                  ))}
                  <p className="text-[10px] text-gray-400 mt-2 italic">
                    Estimation indicative — le montant réel dépend du contexte réglementaire et de
                    l'instruction administrative.
                  </p>
                </div>
              );
            })()}

            {/* A5 — Preuves attendues */}
            {(() => {
              const mainRuleId = obligation.findings?.[0]?.rule_id;
              const proofs = mainRuleId && RULE_EXPECTED_PROOFS[mainRuleId];
              if (!proofs?.length) return null;
              return (
                <div className="p-3 bg-indigo-50/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield size={14} className="text-indigo-500" />
                    <p className="text-xs font-semibold text-indigo-600 uppercase">
                      Preuves attendues
                    </p>
                  </div>
                  <ul className="space-y-0.5">
                    {proofs.map((p, i) => (
                      <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                        <FileText size={10} className="shrink-0 mt-0.5 text-indigo-400" />
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })()}

            {obligation.findings &&
              obligation.findings.length > 0 &&
              (() => {
                const actionableFindings = obligation.findings.filter(
                  (f) => f.status === 'NOK' || f.status === 'UNKNOWN'
                );
                if (!actionableFindings.length) return null;
                return (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      Constats par site ({actionableFindings.length} non conforme
                      {actionableFindings.length !== 1 ? 's' : ''} / {obligation.findings.length})
                    </p>
                    <div className="rounded-lg border border-gray-200 divide-y divide-gray-100">
                      {actionableFindings.map((f) => (
                        <div
                          key={f.id}
                          className="flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-gray-50 transition-colors"
                        >
                          <span
                            className={`w-2 h-2 rounded-full shrink-0 ${f.status === 'NOK' ? 'bg-red-500' : 'bg-amber-500'}`}
                          />
                          <span className="text-gray-700 font-medium truncate flex-1">
                            {f.site_nom}
                          </span>
                          <span className="text-xs text-gray-500 hidden sm:inline">
                            {RULE_LABELS[f.rule_id]?.title_fr || f.regulation || 'Non conforme'}
                          </span>
                          {f.estimated_penalty_eur > 0 && (
                            <span className="text-xs text-red-600 font-medium flex items-center gap-1 shrink-0">
                              <Coins size={11} />
                              {fmtEur(f.estimated_penalty_eur)}
                            </span>
                          )}
                          {isExpert && (
                            <span className="text-[10px] text-gray-400 font-mono">{f.rule_id}</span>
                          )}
                          <button
                            onClick={() => onAuditFinding(f.id)}
                            className="text-xs text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50 font-medium flex items-center gap-1 px-2 py-1 rounded transition-colors"
                            title="Voir les détails"
                          >
                            <Eye size={12} /> Détails
                          </button>
                          {isExpert ? (
                            <>
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
                            </>
                          ) : (
                            <span
                              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                                f.status === 'NOK'
                                  ? 'bg-red-50 text-red-700'
                                  : 'bg-amber-50 text-amber-700'
                              }`}
                            >
                              {f.status === 'NOK'
                                ? STATUT_LABELS.non_conforme
                                : STATUT_LABELS.a_qualifier}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

            {/* A4 — Audit trail mode expert */}
            {isExpert && obligation.findings?.length > 0 && (
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 mb-2">
                  <Info size={14} className="text-gray-500" />
                  <p className="text-xs font-semibold text-gray-600 uppercase">
                    Mode expert — Détails de l'évaluation
                  </p>
                </div>
                {obligation.findings
                  .filter((f) => f.inputs_json || f.params_json || f.engine_version)
                  .slice(0, 3)
                  .map((f) => (
                    <div
                      key={f.id}
                      className="mb-2 p-2 bg-white rounded border border-gray-100 text-xs"
                    >
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-medium text-gray-700">{f.site_nom}</span>
                        <span className="font-mono text-gray-400">{f.rule_id}</span>
                        {f.engine_version && (
                          <span className="text-gray-400">v{f.engine_version}</span>
                        )}
                      </div>
                      {f.inputs_json && (
                        <div className="mb-1">
                          <p className="text-[10px] text-gray-500 font-semibold mb-0.5">
                            Données d'entrée
                          </p>
                          <table className="w-full text-[11px]">
                            <tbody>
                              {Object.entries(
                                typeof f.inputs_json === 'string'
                                  ? JSON.parse(f.inputs_json)
                                  : f.inputs_json
                              ).map(([k, v]) => (
                                <tr key={k} className="border-b border-gray-50">
                                  <td className="py-0.5 pr-3 text-gray-500 whitespace-nowrap">
                                    {k}
                                  </td>
                                  <td className="py-0.5 text-gray-700 font-medium">
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                      {f.params_json && (
                        <div>
                          <p className="text-[10px] text-gray-500 font-semibold mb-0.5">
                            Paramètres / seuils appliqués
                          </p>
                          <table className="w-full text-[11px]">
                            <tbody>
                              {Object.entries(
                                typeof f.params_json === 'string'
                                  ? JSON.parse(f.params_json)
                                  : f.params_json
                              ).map(([k, v]) => (
                                <tr key={k} className="border-b border-gray-50">
                                  <td className="py-0.5 pr-3 text-gray-500 whitespace-nowrap">
                                    {k}
                                  </td>
                                  <td className="py-0.5 text-gray-700 font-medium">
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}

            <div className="p-3 bg-indigo-50/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-indigo-600 uppercase">Joindre preuve</p>
              </div>
              {files.length > 0 && (
                <div className="space-y-1 mb-2">
                  {files.map((f, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-sm text-gray-700 bg-white px-2 py-1.5 rounded"
                    >
                      <FileText size={14} className="text-indigo-500 shrink-0" />
                      <span className="truncate">{f.name}</span>
                      <span className="text-xs text-gray-400 ml-auto whitespace-nowrap">
                        {f.date}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <label className="inline-flex items-center gap-2 cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 transition font-medium">
                <Upload size={14} />
                Ajouter un fichier
                <input
                  type="file"
                  className="sr-only"
                  onChange={(e) => {
                    if (e.target.files[0]) onUploadProof(obligation.id, e.target.files[0]);
                    e.target.value = '';
                  }}
                />
              </label>
            </div>

            {obligation.statut !== 'conforme' && (
              <Button onClick={() => onCreateAction(obligation)} size="sm">
                <Plus size={14} /> Créer une action
              </Button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function ObligationsTab({
  score,
  emptyReason,
  statusFilter,
  setStatusFilter,
  searchQuery,
  setSearchQuery,
  sortedObligations,
  overdueCount,
  handleCreateFromObligation,
  handleWorkflowAction,
  handleUploadProof,
  proofFiles,
  setAuditFindingId,
  bacsV2Summary,
  scopedSites,
  navigate,
  isExpert,
  setDossierSource,
  profileTags,
  onNavigateIntake: _onNavigateIntake,
}) {
  return (
    <>
      {/* Score + summary */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="col-span-2">
          <CardBody>
            <ScoreGauge
              pct={score.pct}
              isEmpty={!!emptyReason && emptyReason !== 'ALL_COMPLIANT'}
            />
            <TrustBadge
              source="RegOps"
              period={`périmètre : ${scopedSites.length} sites`}
              confidence="medium"
              className="mt-2"
            />
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
          </CardBody>
        </Card>
        <Card
          className={`cursor-pointer transition hover:shadow-md ${statusFilter === 'a_risque' ? 'ring-2 ring-amber-400' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'a_risque' ? null : 'a_risque')}
        >
          <CardBody className="bg-amber-50">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={16} className="text-amber-600" />
              <p className="text-xs text-gray-500 font-medium">À qualifier</p>
            </div>
            <p className="text-2xl font-bold text-amber-700">{score.a_risque}</p>
          </CardBody>
        </Card>
      </div>

      {/* Step 21: KPI contextual messages */}
      <div className="flex flex-col gap-1" data-testid="kpi-messages-conformite">
        {(() => {
          const msg = getKpiMessage('conformite', score.pct, {
            totalSites: score.total,
            sitesAtRisk: score.a_risque,
            sitesNonConformes: score.non_conformes,
          });
          if (!msg) return null;
          return (
            <p
              className={`text-xs px-1 ${
                msg.severity === 'crit'
                  ? 'text-red-600'
                  : msg.severity === 'warn'
                    ? 'text-amber-600'
                    : 'text-gray-500'
              }`}
              data-testid="kpi-message-conformite-tab"
            >
              {isExpert ? msg.expert : msg.simple}
            </p>
          );
        })()}
        {(() => {
          const msg = getKpiMessage('risque', score.total_impact_eur || 0, {
            sitesAtRisk: score.a_risque,
          });
          if (!msg) return null;
          return (
            <p
              className={`text-xs px-1 ${
                msg.severity === 'crit'
                  ? 'text-red-600'
                  : msg.severity === 'warn'
                    ? 'text-amber-600'
                    : 'text-gray-500'
              }`}
              data-testid="kpi-message-risque-tab"
            >
              {isExpert ? msg.expert : msg.simple}
            </p>
          );
        })()}
      </div>

      {/* Filters */}
      {sortedObligations.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          {statusFilter && (
            <button
              onClick={() => setStatusFilter(null)}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              Effacer filtre <span className="text-gray-400">×</span>
            </button>
          )}
          <div className="relative flex-1 max-w-xs">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:ring-1 focus:ring-blue-300 focus:border-blue-300"
              placeholder="Rechercher obligation…"
            />
          </div>
        </div>
      )}

      {/* Overdue alert */}
      {overdueCount > 0 && !statusFilter && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle size={16} className="text-red-600 shrink-0" />
          <p className="text-sm text-red-800 font-medium">
            {overdueCount} obligation{overdueCount > 1 ? 's' : ''} en retard — échéance dépassée
          </p>
        </div>
      )}

      {/* Obligation list */}
      <div className="space-y-3">
        {sortedObligations.length === 0 ? (
          <EmptyState
            icon={CheckCircle}
            title={
              emptyReason
                ? emptyReason === 'ALL_COMPLIANT'
                  ? 'Tout est conforme !'
                  : 'Aucune obligation'
                : 'Aucune obligation trouvée'
            }
            text={
              emptyReason
                ? emptyReason === 'ALL_COMPLIANT'
                  ? 'Toutes les obligations sont respectées. Continuez à scanner régulièrement pour maintenir votre conformité.'
                  : "Lancez une évaluation pour détecter les obligations. Pourquoi c'est important : les non-conformités non détectées exposent l'organisation à des sanctions et pénalités financières."
                : 'Aucun résultat pour cette recherche.'
            }
            ctaLabel={
              emptyReason && emptyReason !== 'ALL_COMPLIANT' ? 'Scanner la conformité' : undefined
            }
            onCta={
              emptyReason && emptyReason !== 'ALL_COMPLIANT'
                ? () => navigate('/conformite')
                : undefined
            }
          />
        ) : (
          sortedObligations.map((obligation) => (
            <ObligationCard
              key={obligation.id}
              obligation={obligation}
              onCreateAction={handleCreateFromObligation}
              onExportDossier={setDossierSource ? (obl) => setDossierSource(obl) : null}
              onWorkflowAction={handleWorkflowAction}
              onUploadProof={handleUploadProof}
              proofFiles={proofFiles}
              onAuditFinding={setAuditFindingId}
              bacsV2Summary={obligation.code === 'bacs' ? bacsV2Summary : null}
              onNavigateIntake={
                obligation.code === 'bacs'
                  ? () => {
                      navigate(`/intake/${scopedSites[0]?.id}`);
                    }
                  : null
              }
              isExpert={isExpert}
              profileEntry={profileTags?.get(obligation.id || obligation.code)}
            />
          ))
        )}
      </div>

      {/* KB Obligations */}
      <KBObligationsSection scopedSites={scopedSites} />
    </>
  );
}
