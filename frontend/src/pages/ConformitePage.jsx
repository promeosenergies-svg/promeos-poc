/**
 * PROMEOS - Conformite (/conformite) V9
 * OPS-grade: real API data, workflow actions (ack/resolve/false_positive).
 * Replaces mock obligations with live ComplianceFinding data.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ShieldCheck, AlertTriangle, CheckCircle, Clock, FileText,
  ChevronDown, ChevronUp, Plus, Upload, User, Calendar,
  BookOpen, ExternalLink, Zap, RotateCcw, RefreshCw,
  UserCheck, CheckCircle2, XCircle, X, Eye,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge, PageShell, Progress, Drawer } from '../ui';
import { useToast } from '../ui/ToastProvider';
import CreateActionModal from '../components/CreateActionModal';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { track } from '../services/tracker';
import {
  applyKB,
  getComplianceSummary,
  getComplianceSites,
  patchComplianceFinding,
  recomputeComplianceRules,
  getDataQuality,
  getFindingDetail,
} from '../services/api';

const REG_LABELS = {
  decret_tertiaire_operat: 'Decret Tertiaire',
  bacs: 'BACS (GTB/GTC)',
  aper: 'Loi APER (ENR)',
};

const REG_DESCRIPTIONS = {
  decret_tertiaire_operat: 'Reduire la consommation energetique des batiments tertiaires > 1000 m2',
  bacs: "Systemes d'automatisation et de controle des batiments (GTB/GTC)",
  aper: "Installation d'energies renouvelables sur parkings > 1500 m2",
};

const SEVERITY_BADGE = {
  critical: 'crit', high: 'warn', medium: 'info', low: 'neutral',
};

const STATUT_CONFIG = {
  non_conforme: { label: 'Non conforme', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle },
  a_risque: { label: 'A risque', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', icon: Clock },
  conforme: { label: 'Conforme', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle },
};

const WORKFLOW_CONFIG = {
  open: { label: 'A traiter', color: 'bg-red-50 text-red-700' },
  ack: { label: 'En cours', color: 'bg-amber-50 text-amber-700' },
  resolved: { label: 'Resolu', color: 'bg-green-50 text-green-700' },
  false_positive: { label: 'Faux positif', color: 'bg-gray-100 text-gray-500' },
};

function isOverdue(obligation) {
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

function ScoreGauge({ pct }) {
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
        <p className="text-xs text-gray-500 mt-1">Score de conformite global</p>
        <p className="text-xs text-gray-400 mt-0.5">Score = sites conformes / sites evalues (pondere par criticite)</p>
      </div>
    </div>
  );
}

const KB_SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function KBObligationsSection({ scopedSites }) {
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
          <p className="text-sm text-gray-400">Analyse reglementaire KB en cours...</p>
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
          Obligations detectees par la KB ({items.length})
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
                  <Badge status={SEVERITY_BADGE[item.severity] || 'neutral'}>{item.severity}</Badge>
                  {item.confidence && (
                    <Badge status={item.confidence === 'high' ? 'ok' : 'neutral'}>{item.confidence}</Badge>
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
                    <p className="text-xs font-semibold text-gray-500 mb-1">Sources reglementaires</p>
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
                  <span>KB ID: {item.id}</span>
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
              <p className="text-xs font-semibold text-amber-700">Donnees manquantes pour une analyse complete</p>
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

      <TrustBadge source="PROMEOS KB" period="Analyse reglementaire automatique" confidence="high" />
    </div>
  );
}

/**
 * Transform API sitesData (from /compliance/sites) into obligation-like objects
 * grouped by regulation, for display in ObligationCard.
 */
function sitesToObligations(sitesData, summary) {
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
        obl.statut = 'a_risque';
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
    proof_status: obl.statut === 'conforme' ? 'ok' : obl.statut === 'a_risque' ? 'in_progress' : 'missing',
    pourquoi: `${obl._site_ids_all.size} site(s) concerne(s) par ${obl.regulation}`,
    quoi_faire: obl.findings.filter(f => f.actions?.length).flatMap(f => f.actions).filter((v, i, a) => a.indexOf(v) === i).join('. ') || 'Evaluer la conformite',
    preuve: 'Attestation ou rapport de conformite',
    impact_eur: 0,
  }));
}

function ObligationCard({ obligation, onCreateAction, onWorkflowAction, onUploadProof, proofFiles, onAuditFinding }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_risque;
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
            <span className="text-xs font-semibold text-red-700">En retard — echeance depassee ({obligation.echeance})</span>
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
                <Badge status={SEVERITY_BADGE[obligation.severity] || 'neutral'}>{obligation.severity}</Badge>
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
            <span className="text-gray-500">Sites concernes : </span>
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
              <span className="text-gray-500">Echeance : </span>
              <span className={`font-medium ${overdue ? 'text-red-600' : 'text-gray-800'}`}>{obligation.echeance}</span>
            </div>
          )}
        </div>

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
              <Plus size={14} /> Creer action
            </Button>
          </div>
        )}

        {/* Expanded detail */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Pourquoi concerne</p>
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
                <div className="space-y-1.5">
                  {obligation.findings.filter(f => f.status === 'NOK' || f.status === 'UNKNOWN').map((f) => (
                    <div key={f.id} className="flex items-center gap-3 p-2 rounded bg-gray-50 text-sm">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${f.status === 'NOK' ? 'bg-red-500' : 'bg-amber-500'}`} />
                      <span className="text-gray-700 font-medium truncate flex-1">{f.site_nom}</span>
                      <span className="text-xs text-gray-400 font-mono">{f.rule_id}</span>
                      <button
                        onClick={() => onAuditFinding(f.id)}
                        className="text-xs text-indigo-500 hover:text-indigo-700 font-medium flex items-center gap-1"
                        title="Voir audit"
                      >
                        <Eye size={12} /> Audit
                      </button>
                      <WorkflowBadge status={f.insight_status} />
                      {f.insight_status === 'open' && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'ack')}
                          className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                        >
                          <UserCheck size={12} /> Prendre en charge
                        </button>
                      )}
                      {f.insight_status === 'ack' && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'resolved')}
                          className="text-xs text-green-600 hover:text-green-800 font-medium flex items-center gap-1"
                        >
                          <CheckCircle2 size={12} /> Resolu
                        </button>
                      )}
                      {(f.insight_status === 'open' || f.insight_status === 'ack') && (
                        <button
                          onClick={() => onWorkflowAction(f.id, 'false_positive')}
                          className="text-xs text-gray-400 hover:text-gray-600 font-medium flex items-center gap-1"
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
                <Plus size={14} /> Creer action conformite
              </Button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function FindingAuditDrawer({ findingId, onClose }) {
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

  if (!findingId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-white shadow-xl overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">Audit Finding</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-400">Chargement...</div>
        ) : !detail ? (
          <div className="p-6 text-center text-gray-400">Finding introuvable</div>
        ) : (
          <div className="p-6 space-y-5">
            {/* Identity */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Identite</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">Rule ID:</span> <span className="font-mono font-medium">{detail.rule_id}</span></div>
                <div><span className="text-gray-500">Regulation:</span> <span className="font-medium">{detail.regulation}</span></div>
                <div><span className="text-gray-500">Status:</span> <span className="font-medium">{detail.status}</span></div>
                <div><span className="text-gray-500">Severity:</span> <span className="font-medium">{detail.severity}</span></div>
                <div><span className="text-gray-500">Site:</span> <span className="font-medium">{detail.site_nom}</span></div>
                {detail.deadline && <div><span className="text-gray-500">Echeance:</span> <span className="font-medium">{detail.deadline}</span></div>}
              </div>
            </div>

            {/* Inputs */}
            {detail.inputs && Object.keys(detail.inputs).length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Inputs utilises</p>
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
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Parametres / seuils</p>
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
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Evidence / references</p>
                <div className="bg-green-50 rounded-lg p-3 text-sm text-gray-700">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(detail.evidence_refs, null, 2)}</pre>
                </div>
              </div>
            )}

            {/* Evidence text */}
            {detail.evidence && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Explication</p>
                <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{detail.evidence}</p>
              </div>
            )}

            {/* Metadata */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Metadata</p>
              <div className="text-xs text-gray-400 space-y-1">
                {detail.engine_version && <div>Engine version: <span className="font-mono">{detail.engine_version}</span></div>}
                {detail.created_at && <div>Computed at: {new Date(detail.created_at).toLocaleString('fr-FR')}</div>}
                {detail.updated_at && <div>Updated at: {new Date(detail.updated_at).toLocaleString('fr-FR')}</div>}
                <div>Workflow: {detail.insight_status}</div>
                {detail.owner && <div>Owner: {detail.owner}</div>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DataQualityGate({ siteId }) {
  const [dq, setDq] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    getDataQuality('site', siteId)
      .then(setDq)
      .catch(() => {});
  }, [siteId]);

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
                <span className="text-sm font-semibold text-gray-900">Qualite des donnees</span>
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
                <p className="text-xs font-semibold text-red-700 uppercase mb-1">Donnees critiques manquantes</p>
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
                <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Donnees optionnelles manquantes</p>
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

export default function ConformitePage() {
  const { org, scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [prefill, setPrefill] = useState(null);
  const [proofFiles, setProofFiles] = useState({});
  const [statusFilter, setStatusFilter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [sitesData, setSitesData] = useState([]);
  const [auditFindingId, setAuditFindingId] = useState(null);

  const loadData = useCallback(() => {
    setLoading(true);
    Promise.all([
      getComplianceSummary(),
      getComplianceSites(),
    ]).then(([s, st]) => {
      setSummary(s);
      setSitesData(st);
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

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

  const sortedObligations = useMemo(() => {
    let list = [...obligations];
    if (statusFilter) {
      list = list.filter(o => o.statut === statusFilter);
    }
    list.sort((a, b) => {
      const aOver = isOverdue(a) ? 0 : 1;
      const bOver = isOverdue(b) ? 0 : 1;
      if (aOver !== bOver) return aOver - bOver;
      const order = { non_conforme: 0, a_risque: 1, conforme: 2 };
      return (order[a.statut] ?? 9) - (order[b.statut] ?? 9);
    });
    return list;
  }, [obligations, statusFilter]);

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      await recomputeComplianceRules();
      loadData();
      track('conformite_recompute');
    } catch {
      // silent
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
      // silent
    }
  };

  function handleCreateFromObligation(obligation) {
    setPrefill({
      titre: `Mise en conformite ${obligation.regulation}`,
      type: 'conformite',
      priorite: obligation.severity === 'critical' ? 'critical' : obligation.severity === 'high' ? 'high' : 'medium',
      description: obligation.quoi_faire,
      obligation_code: obligation.code,
      impact_eur: obligation.impact_eur,
      site: `${obligation.sites_concernes} sites concernes`,
    });
    setShowCreate(true);
    track('conformite_create_action', { regulation: obligation.code });
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
      <PageShell icon={ShieldCheck} title="Conformite reglementaire" subtitle="Chargement...">
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="h-24 bg-gray-200 rounded-lg" />)}
          </div>
          <div className="h-40 bg-gray-200 rounded-lg" />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={ShieldCheck}
      title="Conformite reglementaire"
      subtitle={`${org.nom} · ${scopedSites.length} sites dans le perimetre`}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={handleRecompute} disabled={recomputing}>
            <RefreshCw size={14} className={recomputing ? 'animate-spin' : ''} />
            {recomputing ? 'Evaluation...' : 'Re-evaluer'}
          </Button>
          <Button onClick={() => { setPrefill(null); setShowCreate(true); }}>
            <Plus size={16} /> Creer action conformite
          </Button>
        </>
      }
    >

      {/* Score + summary */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="col-span-2">
          <CardBody>
            <ScoreGauge pct={score.pct} />
            <TrustBadge source="RegOps" period={`perimetre : ${scopedSites.length} sites`} confidence="medium" className="mt-2" />
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
              <p className="text-xs text-gray-500 font-medium">A evaluer</p>
            </div>
            <p className="text-2xl font-bold text-amber-700">{score.a_risque}</p>
            <p className="text-xs text-gray-500 mt-1">sites</p>
          </CardBody>
        </Card>
      </div>

      {/* Data Quality Gate */}
      {scopedSites.length > 0 && <DataQualityGate siteId={scopedSites[0]?.id} />}

      {/* Active filter indicator */}
      {statusFilter && (
        <div className="flex items-center gap-2">
          <Badge status={statusFilter === 'non_conforme' ? 'crit' : 'warn'}>
            Filtre : {statusFilter === 'non_conforme' ? 'Non conformes' : 'A risque'}
          </Badge>
          <button
            onClick={() => setStatusFilter(null)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition"
          >
            <RotateCcw size={12} /> Reinitialiser
          </button>
        </div>
      )}

      {/* Overdue alert */}
      {overdueCount > 0 && !statusFilter && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle size={16} className="text-red-600" />
          <span className="text-sm font-medium text-red-700">
            {overdueCount} obligation(s) en retard — echeance(s) depassee(s)
          </span>
        </div>
      )}

      {/* Obligations list */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          {statusFilter ? sortedObligations.length : score.total} reglementations evaluees
        </h3>
        {sortedObligations.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Aucune obligation detectee"
            text="Cliquez Re-evaluer pour lancer l'evaluation, ou ajoutez des sites a votre patrimoine."
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
              />
            ))}
          </div>
        )}
      </div>

      {/* KB Obligations (from knowledge base apply engine) */}
      <KBObligationsSection scopedSites={scopedSites} />

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
