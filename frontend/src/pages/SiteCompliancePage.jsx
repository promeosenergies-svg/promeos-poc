/**
 * PROMEOS - Site Compliance V68+V69 (/compliance/sites/:siteId)
 * 3 tabs: Obligations, Preuves, Plan d'action.
 * V69: Plan tab = cockpit "travaux + aides + preuves + suivi M&V"
 *   - Packages S/M/L with "Créer dossier CEE" CTA
 *   - Kanban Dossier CEE (devis → engagement → travaux → pv_photos → mv → versement)
 *   - Widget M&V minimal (baseline, alerts)
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  Upload,
  Plus,
  ArrowLeft,
  FileCheck,
  ClipboardList,
  Building,
  Zap,
  Sun,
  ArrowRight,
  Package,
  Activity,
  Hammer,
  Banknote,
} from 'lucide-react';
import {
  getSiteComplianceSummary,
  getActionsList,
  getSiteWorkPackages,
  createWorkPackage,
  getMvSummary,
} from '../services/api';
import { toPatrimoine, toConsoImport, toBillIntel, toCompliancePipeline } from '../services/routes';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { fmtDateFR, fmtKwh } from '../utils/format';

const REG_CONFIG = {
  tertiaire_operat: { label: 'Décret Tertiaire', icon: Building, color: 'bg-blue-600' },
  bacs: { label: 'BACS (GTB/GTC)', icon: Zap, color: 'bg-purple-600' },
  aper: { label: 'Loi APER (ENR)', icon: Sun, color: 'bg-amber-600' },
};

const GATE_BADGE = {
  BLOCKED: { label: 'Bloqué', cls: 'bg-red-100 text-red-700' },
  WARNING: { label: 'Incomplet', cls: 'bg-amber-100 text-amber-700' },
  OK: { label: 'Prêt', cls: 'bg-green-100 text-green-700' },
};

const STATUT_BADGE = {
  conforme: { label: 'Conforme', cls: 'bg-green-100 text-green-700' },
  a_risque: { label: 'À risque', cls: 'bg-amber-100 text-amber-700' },
  non_conforme: { label: 'Non conforme', cls: 'bg-red-100 text-red-700' },
  derogation: { label: 'Dérogation', cls: 'bg-blue-100 text-blue-700' },
  exempted: { label: 'Dérogation approuvée', cls: 'bg-blue-100 text-blue-700' },
};

const CTA_NAVIGATE = {
  patrimoine: (siteId) => toPatrimoine({ site_id: siteId }),
  consommation: () => toConsoImport(),
  conformite: (siteId) => `/compliance/sites/${siteId}`,
  billing: (siteId) => toBillIntel({ site_id: siteId }),
};

const SIZE_BADGE = {
  S: { label: 'S', cls: 'bg-green-100 text-green-700' },
  M: { label: 'M', cls: 'bg-amber-100 text-amber-700' },
  L: { label: 'L', cls: 'bg-red-100 text-red-700' },
};

/* CEE_STATUS_BADGE, CEE_STEPS, CEE_STEP_LABELS — masqué V1.2, prévu évolution future */

function Badge({ cfg }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.cls}`}
    >
      {cfg.label}
    </span>
  );
}

/* ── Tab: Obligations ────────────────── */
function ObligationsTab({ data, navigate }) {
  const { applicability, readiness, snapshot, deadlines } = data;

  return (
    <div className="space-y-4" data-section="tab-obligations">
      {/* Readiness Gate */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-3 mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Data Readiness Gate</h3>
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium ${GATE_BADGE[readiness.gate_status]?.cls || 'bg-gray-100'}`}
          >
            {GATE_BADGE[readiness.gate_status]?.label || readiness.gate_status}
          </span>
          <span className="text-xs text-gray-400 ml-auto">
            Complétude: {readiness.completeness_pct}%
          </span>
        </div>
        {readiness.missing.length > 0 && (
          <div className="space-y-1.5">
            {readiness.missing
              .filter((m) => m.level === 'blocking')
              .map((m, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded bg-red-50 text-sm">
                  <XCircle size={14} className="text-red-500 shrink-0" />
                  <span className="text-red-700 flex-1">{m.cta_label}</span>
                  <span className="text-xs text-gray-400">{m.regulation}</span>
                  <button
                    onClick={() =>
                      navigate(CTA_NAVIGATE[m.cta_target]?.(data.site_id) || '/patrimoine')
                    }
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                  >
                    Corriger <ArrowRight size={12} />
                  </button>
                </div>
              ))}
            {readiness.missing
              .filter((m) => m.level === 'recommended')
              .map((m, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded bg-amber-50 text-sm">
                  <AlertTriangle size={14} className="text-amber-500 shrink-0" />
                  <span className="text-amber-700 flex-1">{m.cta_label}</span>
                  <span className="text-xs text-gray-400">{m.regulation}</span>
                </div>
              ))}
          </div>
        )}
        {readiness.missing.length === 0 && (
          <p className="text-sm text-green-600 flex items-center gap-2">
            <CheckCircle size={14} /> Toutes les données requises sont renseignées.
          </p>
        )}
      </div>

      {/* Per-regulation cards */}
      {Object.entries(REG_CONFIG).map(([regKey, cfg]) => {
        const app = applicability[regKey];
        const Icon = cfg.icon;
        const deadlineItems = [
          ...(deadlines.d30 || []),
          ...(deadlines.d90 || []),
          ...(deadlines.d180 || []),
        ].filter((d) => d.regulation === regKey || d.regulation === regKey.replace('_operat', ''));

        return (
          <div key={regKey} className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-8 h-8 rounded-lg ${cfg.color} flex items-center justify-center`}>
                <Icon size={16} className="text-white" />
              </div>
              <h3 className="text-sm font-semibold text-gray-900">{cfg.label}</h3>
              {app && (
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    app.applicable === true
                      ? 'bg-blue-100 text-blue-700'
                      : app.applicable === false
                        ? 'bg-gray-100 text-gray-500'
                        : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {app.applicable === true
                    ? 'Applicable'
                    : app.applicable === false
                      ? 'Non applicable'
                      : 'Incertain'}
                </span>
              )}
              {regKey === 'tertiaire_operat' && snapshot.statut_decret_tertiaire && (
                <Badge
                  cfg={
                    STATUT_BADGE[snapshot.statut_decret_tertiaire] || {
                      label: snapshot.statut_decret_tertiaire,
                      cls: 'bg-gray-100',
                    }
                  }
                />
              )}
              {regKey === 'bacs' && snapshot.statut_bacs && (
                <Badge
                  cfg={
                    STATUT_BADGE[snapshot.statut_bacs] || {
                      label: snapshot.statut_bacs,
                      cls: 'bg-gray-100',
                    }
                  }
                />
              )}
            </div>
            {app && <p className="text-xs text-gray-500 mb-2">{app.reason}</p>}
            {app?.missing_fields?.length > 0 && (
              <div className="space-y-1 mt-2">
                {app.missing_fields.map((f, i) => (
                  <p key={i} className="text-xs text-red-500">
                    Champ manquant: {f}
                  </p>
                ))}
              </div>
            )}
            {deadlineItems.length > 0 && (
              <div className="mt-2 space-y-1">
                {deadlineItems.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                    <Clock
                      size={12}
                      className={d.days_remaining <= 30 ? 'text-red-500' : 'text-amber-500'}
                    />
                    <span>{d.description}</span>
                    <span className="ml-auto font-medium">
                      {d.deadline} ({d.days_remaining}j)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Tab: Preuves ────────────────── */
function PreuvesTab({ data }) {
  const { evidences_count, readiness } = data;

  const proofMissing = readiness.missing.filter((m) => m.field.startsWith('has_bacs_'));

  return (
    <div className="space-y-4" data-section="tab-preuves">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <FileCheck size={16} className="text-blue-500" />
          Preuves & Documents ({evidences_count})
        </h3>
        {evidences_count === 0 && proofMissing.length === 0 && (
          <p className="text-sm text-gray-500">Aucune preuve enregistrée pour ce site.</p>
        )}
        {proofMissing.length > 0 && (
          <div className="space-y-2 mt-2">
            {proofMissing.map((m, i) => (
              <div key={i} className="flex items-center gap-2 p-2 rounded bg-amber-50">
                <Upload size={14} className="text-amber-500" />
                <span className="text-sm text-amber-700 flex-1">{m.cta_label}</span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    m.level === 'blocking'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {m.level === 'blocking' ? 'Requis' : 'Recommandé'}
                </span>
              </div>
            ))}
          </div>
        )}
        {evidences_count > 0 && (
          <p className="text-sm text-green-600 flex items-center gap-2 mt-2">
            <CheckCircle size={14} /> {evidences_count} preuve(s) enregistrée(s).
          </p>
        )}
      </div>
    </div>
  );
}

/* KanbanCee — masqué V1.2, prévu évolution future CEE */

/* ── V69: Widget M&V ────────────────── */
function MvWidget({ siteId }) {
  const [mv, setMv] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMvSummary(siteId)
      .then(setMv)
      .catch(() => setMv(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading) return <div className="bg-white rounded-lg shadow p-4 animate-pulse h-32" />;
  if (!mv) return null;

  const deltaColor =
    mv.delta_pct > 10 ? 'text-red-600' : mv.delta_pct < -5 ? 'text-green-600' : 'text-gray-700';

  return (
    <div className="bg-white rounded-lg shadow p-4" data-section="mv-widget">
      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <Activity size={16} className="text-indigo-500" />
        M&V — Mesure & Vérification
      </h4>
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center">
          <p className="text-xs text-gray-500">Baseline</p>
          <p className="text-sm font-bold text-gray-900">{fmtKwh(mv.baseline_kwh_month)}/m</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500">Actuel</p>
          <p className="text-sm font-bold text-gray-900">{fmtKwh(mv.current_kwh_month)}/m</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500">Delta</p>
          <p className={`text-sm font-bold ${deltaColor}`}>
            {mv.delta_pct > 0 ? '+' : ''}
            {mv.delta_pct}%
          </p>
        </div>
      </div>
      {mv.alerts.length > 0 && (
        <div className="space-y-1.5">
          {mv.alerts.map((a, i) => (
            <div
              key={i}
              className={`flex items-center gap-2 p-2 rounded text-xs ${
                a.severity === 'high' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              <AlertTriangle size={12} className="shrink-0" />
              <span>{a.message}</span>
            </div>
          ))}
        </div>
      )}
      {mv.alerts.length === 0 && (
        <p className="text-xs text-green-600 flex items-center gap-1">
          <CheckCircle size={12} /> Pas d'alerte M&V.
        </p>
      )}
    </div>
  );
}

/* ── Tab: Plan d'action V69 ────────────────── */
function PlanTab({ siteId, siteName: _siteName, navigate, onCreateAction, toast }) {
  const [actions, setActions] = useState([]);
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewPkg, setShowNewPkg] = useState(false);
  const [newPkg, setNewPkg] = useState({
    label: '',
    size: 'M',
    capex_eur: '',
    savings_eur_year: '',
  });
  const [creating, setCreating] = useState(false);

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([
      getActionsList({ site_id: siteId, source_type: 'compliance' }).catch(() => []),
      getSiteWorkPackages(siteId).catch(() => []),
    ])
      .then(([acts, pkgs]) => {
        setActions(Array.isArray(acts) ? acts : []);
        setPackages(Array.isArray(pkgs) ? pkgs : []);
      })
      .finally(() => setLoading(false));
  }, [siteId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleCreatePackage = async () => {
    if (!newPkg.label.trim()) return;
    setCreating(true);
    try {
      await createWorkPackage(siteId, {
        label: newPkg.label,
        size: newPkg.size,
        capex_eur: newPkg.capex_eur ? parseFloat(newPkg.capex_eur) : null,
        savings_eur_year: newPkg.savings_eur_year ? parseFloat(newPkg.savings_eur_year) : null,
      });
      toast('Package créé', 'success');
      setShowNewPkg(false);
      setNewPkg({ label: '', size: 'M', capex_eur: '', savings_eur_year: '' });
      reload();
    } catch {
      toast('Erreur lors de la création', 'error');
    } finally {
      setCreating(false);
    }
  };

  /* handleCreateDossier — masqué V1.2, prévu évolution future CEE */

  const STATUS_PILL = {
    open: 'bg-gray-100 text-gray-700',
    in_progress: 'bg-amber-100 text-amber-700',
    done: 'bg-green-100 text-green-700',
    blocked: 'bg-red-100 text-red-700',
  };

  return (
    <div className="space-y-4" data-section="tab-plan">
      {/* V69: Work Packages S/M/L */}
      <div className="bg-white rounded-lg shadow p-4" data-section="work-packages">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Package size={16} className="text-indigo-500" />
            Packages travaux ({packages.length})
          </h3>
          <button
            onClick={() => setShowNewPkg(!showNewPkg)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition"
            data-testid="cta-add-package"
          >
            <Plus size={14} /> Ajouter package
          </button>
        </div>

        {/* New package form */}
        {showNewPkg && (
          <div className="border border-indigo-200 rounded-lg p-3 mb-3 bg-indigo-50 space-y-2">
            <input
              value={newPkg.label}
              onChange={(e) => setNewPkg((p) => ({ ...p, label: e.target.value }))}
              placeholder="Nom du lot (ex: Isolation combles)"
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
              data-testid="pkg-label-input"
            />
            <div className="flex gap-2">
              <select
                value={newPkg.size}
                onChange={(e) => setNewPkg((p) => ({ ...p, size: e.target.value }))}
                className="px-2 py-1.5 text-sm border border-gray-300 rounded"
                data-testid="pkg-size-select"
              >
                <option value="S">S (simple)</option>
                <option value="M">M (moyen)</option>
                <option value="L">L (complexe)</option>
              </select>
              <input
                value={newPkg.capex_eur}
                onChange={(e) => setNewPkg((p) => ({ ...p, capex_eur: e.target.value }))}
                placeholder="CAPEX (EUR)"
                type="number"
                className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded"
              />
              <input
                value={newPkg.savings_eur_year}
                onChange={(e) => setNewPkg((p) => ({ ...p, savings_eur_year: e.target.value }))}
                placeholder="Économies/an (EUR)"
                type="number"
                className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowNewPkg(false)}
                className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700"
              >
                Annuler
              </button>
              <button
                onClick={handleCreatePackage}
                disabled={creating || !newPkg.label.trim()}
                className="px-3 py-1 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
                data-testid="pkg-submit"
              >
                Créer
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded" />
            ))}
          </div>
        ) : packages.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">Aucun package de travaux.</p>
        ) : (
          <div className="space-y-3">
            {packages.map((wp) => (
              <div key={wp.id} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Badge cfg={SIZE_BADGE[wp.size] || SIZE_BADGE.M} />
                  <span className="text-sm font-medium text-gray-900 flex-1">{wp.label}</span>
                </div>
                <div className="flex gap-4 text-xs text-gray-500 mb-2">
                  {wp.capex_eur != null && (
                    <span className="flex items-center gap-1">
                      <Banknote size={12} /> CAPEX: {wp.capex_eur.toLocaleString('fr-FR')} €
                    </span>
                  )}
                  {wp.savings_eur_year != null && (
                    <span className="flex items-center gap-1">
                      <Hammer size={12} /> Éco: {wp.savings_eur_year.toLocaleString('fr-FR')} €/an
                    </span>
                  )}
                  {wp.payback_years != null && <span>Payback: {wp.payback_years} ans</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* V69: Widget M&V */}
      <MvWidget siteId={siteId} />

      {/* Actions list (from V68) */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <ClipboardList size={16} className="text-blue-500" />
            Actions conformité ({actions.length})
          </h3>
          <button
            onClick={onCreateAction}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition"
            data-testid="cta-creer-action-plan"
          >
            <Plus size={14} /> Créer action
          </button>
        </div>
        {loading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-gray-200 rounded" />
            ))}
          </div>
        ) : actions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <ClipboardList size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucune action conformité pour ce site.</p>
            <button
              onClick={onCreateAction}
              className="mt-2 text-sm text-blue-600 hover:underline"
              data-testid="cta-creer-action-empty"
            >
              Créer la première action
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {actions.map((a) => (
              <div
                key={a.id}
                className="flex items-center gap-3 p-2 rounded border border-gray-200 hover:bg-gray-50"
              >
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_PILL[a.status] || STATUS_PILL.open}`}
                >
                  {a.status}
                </span>
                <span className="text-sm text-gray-900 flex-1 truncate">{a.title}</span>
                {a.due_date && (
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock size={12} /> {fmtDateFR(a.due_date)}
                  </span>
                )}
                <button
                  onClick={() => navigate(`/actions/${a.id}`)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  <ArrowRight size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ────────────────── */
export default function SiteCompliancePage() {
  const { siteId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { sitesLoading } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('obligations');
  const { openActionDrawer } = useActionDrawer();

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getSiteComplianceSummary(siteId)
      .then(setData)
      .catch(() => toast('Erreur lors du chargement de la conformité site', 'error'))
      .finally(() => setLoading(false));
  }, [siteId, toast]);

  if (loading || sitesLoading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-60 bg-gray-200 rounded-lg" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8 text-center text-gray-500">
        <p>Site introuvable.</p>
        <Link to={toCompliancePipeline()} className="text-blue-600 hover:underline text-sm">
          Retour au pipeline
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: 'obligations', label: 'Obligations', icon: ShieldCheck },
    { id: 'preuves', label: 'Preuves', icon: FileCheck },
    { id: 'plan', label: "Plan d'action", icon: ClipboardList },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-8" data-section="site-compliance">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(toCompliancePipeline())}
          className="text-gray-400 hover:text-gray-600"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">{data.site_nom}</h1>
          <p className="text-sm text-gray-500">
            Conformité — {data.obligations_count} obligation{data.obligations_count > 1 ? 's' : ''},{' '}
            {data.findings_count} constat{data.findings_count > 1 ? 's' : ''},{' '}
            {data.evidences_count} preuve{data.evidences_count > 1 ? 's' : ''}
          </p>
        </div>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${GATE_BADGE[data.readiness.gate_status]?.cls || 'bg-gray-100'}`}
        >
          {GATE_BADGE[data.readiness.gate_status]?.label || 'N/A'}
        </span>
      </div>

      {/* Scores strip */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <p className="text-xs text-gray-500">Risque régl.</p>
          <p
            className={`text-lg font-bold ${data.scores.reg_risk >= 60 ? 'text-red-600' : data.scores.reg_risk >= 30 ? 'text-amber-600' : 'text-green-600'}`}
          >
            {data.scores.reg_risk}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <p className="text-xs text-gray-500">Risque preuve</p>
          <p
            className={`text-lg font-bold ${data.scores.evidence_risk >= 60 ? 'text-red-600' : data.scores.evidence_risk >= 30 ? 'text-amber-600' : 'text-green-600'}`}
          >
            {data.scores.evidence_risk}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <p className="text-xs text-gray-500">Opportunité</p>
          <p className="text-lg font-bold text-gray-900">
            {data.scores.financial_opportunity_eur > 0
              ? `${data.scores.financial_opportunity_eur.toLocaleString('fr-FR')} €`
              : '-'}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <p className="text-xs text-gray-500">Confiance donnée</p>
          <p
            className={`text-lg font-bold ${data.data_trust.trust_score >= 70 ? 'text-green-600' : data.data_trust.trust_score >= 40 ? 'text-amber-600' : 'text-red-600'}`}
          >
            {data.data_trust.trust_score}%
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-4">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
              activeTab === id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'obligations' && <ObligationsTab data={data} navigate={navigate} />}
      {activeTab === 'preuves' && <PreuvesTab data={data} />}
      {activeTab === 'plan' && (
        <PlanTab
          siteId={siteId}
          siteName={data.site_nom}
          navigate={navigate}
          onCreateAction={() =>
            openActionDrawer({
              prefill: { type: 'conformite' },
              siteId: parseInt(siteId),
              sourceType: 'compliance',
            })
          }
          toast={toast}
        />
      )}

      {/* Action creation handled by ActionDrawerContext */}
    </div>
  );
}
