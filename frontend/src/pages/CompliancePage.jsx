/**
 * @deprecated LEGACY — NE PLUS UTILISER.
 * Cette page est remplacée par ConformitePage.jsx (V92+).
 * La route /compliance redirige automatiquement vers /conformite (voir App.jsx).
 * Ce fichier est conservé temporairement pour référence mais n'est plus importé.
 * Suppression prévue au prochain sprint de nettoyage.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Filter,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import {
  getComplianceSummary,
  getComplianceSites,
  recomputeComplianceRules,
} from '../services/api';
import { useToast } from '../ui/ToastProvider';

const STATUS_CONFIG = {
  OK: { label: 'Conforme', color: 'text-green-700 bg-green-100', icon: ShieldCheck },
  NOK: { label: 'Non conforme', color: 'text-red-700 bg-red-100', icon: XCircle },
  UNKNOWN: { label: 'Inconnu', color: 'text-gray-600 bg-gray-100', icon: HelpCircle },
  OUT_OF_SCOPE: { label: 'Non concerne', color: 'text-blue-600 bg-blue-50', icon: null },
};

const SEVERITY_CONFIG = {
  critical: { label: 'Critique', color: 'bg-red-600 text-white' },
  high: { label: 'Eleve', color: 'bg-orange-500 text-white' },
  medium: { label: 'Moyen', color: 'bg-amber-400 text-gray-900' },
  low: { label: 'Faible', color: 'bg-gray-300 text-gray-700' },
};

const REG_LABELS = {
  decret_tertiaire_operat: 'Decret Tertiaire',
  bacs: 'BACS (GTB/GTC)',
  aper: 'Loi APER (ENR)',
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.UNKNOWN;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}
    >
      {cfg.icon && <cfg.icon size={12} />}
      {cfg.label}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const cfg = SEVERITY_CONFIG[severity];
  if (!cfg) return null;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
  );
}

function SummaryCards({ summary }) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
        <p className="text-xs text-gray-500 mb-1">Sites evalues</p>
        <p className="text-2xl font-bold text-gray-900">{summary.total_sites}</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
        <p className="text-xs text-gray-500 mb-1">Conformes</p>
        <p className="text-2xl font-bold text-green-600">{summary.sites_ok}</p>
        <p className="text-xs text-gray-400">{summary.pct_ok}%</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
        <p className="text-xs text-gray-500 mb-1">Non conformes</p>
        <p className="text-2xl font-bold text-red-600">{summary.sites_nok}</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-gray-400">
        <p className="text-xs text-gray-500 mb-1">A evaluer</p>
        <p className="text-2xl font-bold text-gray-500">{summary.sites_unknown}</p>
      </div>
    </div>
  );
}

function TopActions({ actions }) {
  if (!actions || actions.length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <AlertTriangle size={16} className="text-amber-500" />
        Actions prioritaires
      </h3>
      <div className="space-y-2">
        {actions.map((a, i) => (
          <div key={i} className="flex items-center gap-3 p-2 rounded bg-gray-50">
            <span className="text-sm font-bold text-gray-400 w-6">{i + 1}</span>
            <SeverityBadge severity={a.severity} />
            <span className="text-sm text-gray-700 flex-1">{a.action}</span>
            <span className="text-xs text-gray-400">
              {REG_LABELS[a.regulation] || a.regulation}
            </span>
            <span className="text-xs text-gray-400">
              {a.nb_sites} site{a.nb_sites > 1 ? 's' : ''}
            </span>
            {a.deadline && (
              <span className="text-xs text-red-500 font-medium">Ech. {a.deadline}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SiteRow({ site }) {
  const [expanded, setExpanded] = useState(false);
  const worstStatus = site.findings.reduce((worst, f) => {
    if (f.status === 'NOK') return 'NOK';
    if (f.status === 'UNKNOWN' && worst !== 'NOK') return 'UNKNOWN';
    return worst;
  }, 'OK');

  const nokCount = site.findings.filter((f) => f.status === 'NOK').length;

  return (
    <div className="border border-gray-200 rounded-lg mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 transition text-left"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <StatusBadge status={worstStatus} />
        <span className="text-sm font-medium text-gray-900 flex-1">{site.site_nom}</span>
        <span className="text-xs text-gray-400">{site.site_type}</span>
        <span className="text-xs text-gray-500">
          {site.findings.length} regles
          {nokCount > 0 && <span className="text-red-500 ml-1">({nokCount} NOK)</span>}
        </span>
      </button>
      {expanded && (
        <div className="px-4 pb-3 border-t border-gray-100">
          <table className="w-full text-sm mt-2">
            <thead>
              <tr className="text-xs text-gray-400 border-b">
                <th className="text-left py-1">Regle</th>
                <th className="text-left py-1">Regulation</th>
                <th className="text-left py-1">Statut</th>
                <th className="text-left py-1">Severite</th>
                <th className="text-left py-1">Echeance</th>
                <th className="text-left py-1">Explication</th>
              </tr>
            </thead>
            <tbody>
              {site.findings.map((f, i) => (
                <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-1.5 font-mono text-xs">{f.rule_id}</td>
                  <td className="py-1.5 text-xs">{REG_LABELS[f.regulation] || f.regulation}</td>
                  <td className="py-1.5">
                    <StatusBadge status={f.status} />
                  </td>
                  <td className="py-1.5">
                    {f.severity && <SeverityBadge severity={f.severity} />}
                  </td>
                  <td className="py-1.5 text-xs text-gray-500">{f.deadline || '-'}</td>
                  <td className="py-1.5 text-xs text-gray-600 max-w-xs truncate">{f.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {site.findings.some((f) => f.actions && f.actions.length > 0) && (
            <div className="mt-2 p-2 bg-amber-50 rounded">
              <p className="text-xs font-semibold text-amber-700 mb-1">Actions recommandees:</p>
              <ul className="space-y-0.5">
                {site.findings
                  .filter((f) => f.actions && f.actions.length > 0)
                  .flatMap((f) => f.actions)
                  .filter((v, i, a) => a.indexOf(v) === i)
                  .map((action, i) => (
                    <li key={i} className="text-xs text-amber-800">
                      • {action}
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CompliancePage() {
  const { toast } = useToast();
  const [summary, setSummary] = useState(null);
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [filterReg, setFilterReg] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');

  const loadData = () => {
    setLoading(true);
    const params = {};
    if (filterReg) params.regulation = filterReg;
    if (filterStatus) params.status = filterStatus;
    if (filterSeverity) params.severity = filterSeverity;

    Promise.all([getComplianceSummary(), getComplianceSites(params)])
      .then(([s, st]) => {
        setSummary(s);
        setSites(st);
      })
      .catch(() => toast('Erreur lors du chargement de la conformité', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterReg, filterStatus, filterSeverity]);

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      await recomputeComplianceRules();
      loadData();
    } catch {
      toast('Erreur lors du recalcul des regles', 'error');
    } finally {
      setRecomputing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldCheck size={24} className="text-blue-600" />
            Conformité réglementaire
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Évaluation multi-sites — Décret Tertiaire, BACS, Loi APER
          </p>
        </div>
        <button
          onClick={handleRecompute}
          disabled={recomputing}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
        >
          <RefreshCw size={16} className={recomputing ? 'animate-spin' : ''} />
          {recomputing ? 'Évaluation...' : 'Réévaluer'}
        </button>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-lg" />
            ))}
          </div>
          <div className="h-40 bg-gray-200 rounded-lg" />
        </div>
      ) : (
        <>
          <SummaryCards summary={summary} />
          <TopActions actions={summary?.top_actions} />

          {/* Filters */}
          <div className="flex items-center gap-3 mb-4">
            <Filter size={14} className="text-gray-400" />
            <select
              value={filterReg}
              onChange={(e) => setFilterReg(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="">Toutes reglementations</option>
              <option value="decret_tertiaire_operat">Decret Tertiaire</option>
              <option value="bacs">BACS</option>
              <option value="aper">APER</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="">Tous statuts</option>
              <option value="OK">Conforme</option>
              <option value="NOK">Non conforme</option>
              <option value="UNKNOWN">Inconnu</option>
            </select>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="">Toutes severites</option>
              <option value="critical">Critique</option>
              <option value="high">Eleve</option>
              <option value="medium">Moyen</option>
              <option value="low">Faible</option>
            </select>
          </div>

          {/* Sites table */}
          <div className="space-y-1">
            {sites.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                <ShieldCheck size={40} className="mx-auto mb-3 text-gray-300" />
                <p>Aucun constat.</p>
                <p className="text-sm mt-1">
                  Cliquez « Réévaluer » pour lancer l'évaluation ou{' '}
                  <Link to="/import" className="text-blue-600 hover:underline">
                    importez des sites
                  </Link>
                  .
                </p>
              </div>
            ) : (
              sites.map((site) => <SiteRow key={site.site_id} site={site} />)
            )}
          </div>
        </>
      )}
    </div>
  );
}
