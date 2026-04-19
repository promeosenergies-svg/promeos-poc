/**
 * PROMEOS - Compliance Pipeline V68 (/compliance/pipeline)
 * Portfolio view: 3 KPIs, top 10 blockers, deadlines 30/90/180, untrusted sites, site table.
 * Every missing item has a CTA linking to Patrimoine/Timeline/Shadow Billing.
 *
 * ─── Lot 6 Phase 5 (refonte Sol) ──────────────────────────────────────
 * Le hero Sol `CompliancePipelineSol` est injecté au sommet du rendu
 * happy path ci-dessous. Le body legacy (3 KPIs cards + top_blockers
 * + deadlines + untrusted_sites + sites table) est wrapped
 * `{false && (…)}` pour préserver le rollback intégral (code vivant
 * référence — un simple `true &&` suffit à restaurer). Les early
 * returns (loading/error/empty) restent actifs pour les états
 * dégradés pré-data ; Sol hero prend la main dès que `data` est chargé.
 *
 * Violations source-guards INTENTIONNELLEMENT hors scope (legacy wrap) :
 *   - `s.completeness_pct >= 80/50` (line ~310-315) — seuillage gate
 *   - `s.reg_risk >= 60/30` (line ~324-328) — seuillage risque visuel
 *   - `s.trust_score` display raw (line ~266) — affichage brut
 *
 * Ces patterns sont tolérés dans le legacy parce que le bloc est dead
 * code post-Sol. Les source-guards P5.0 scopent uniquement les
 * nouveaux paths `CompliancePipelineSol.jsx` + `compliance-pipeline/`.
 *
 * Scope switcher limitation : l'endpoint backend
 * `/api/compliance/portfolio/summary` n'accepte pas de `site_id` —
 * le hero reste ORG-level même sur `useScope` site. Gap documenté
 * Demande 4 de `docs/backlog/BACKLOG_P5_AUDIT_SME_API.md`.
 * ─────────────────────────────────────────────────────────────────────
 */
import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle,
  Database,
  ChevronRight,
  XCircle,
  AlertOctagon,
  ArrowRight,
  Building,
} from 'lucide-react';
import { getPortfolioComplianceSummary } from '../services/api';
import { toSiteCompliance, toPatrimoine, toConsoImport, toBillIntel } from '../services/routes';
import { useToast } from '../ui/ToastProvider';
import ErrorState from '../ui/ErrorState';
import { useScope } from '../contexts/ScopeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import CompliancePipelineSol from './CompliancePipelineSol';

const GATE_BADGE = {
  BLOCKED: { label: 'Bloqué', color: 'bg-red-100 text-red-700', icon: XCircle },
  WARNING: { label: 'Incomplet', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
  OK: { label: 'Prêt', color: 'bg-green-100 text-green-700', icon: CheckCircle },
};

const CTA_ROUTES = {
  patrimoine: (siteId) => toPatrimoine({ site_id: siteId }),
  consommation: () => toConsoImport(),
  conformite: (siteId) => toSiteCompliance(siteId),
  billing: (siteId) => toBillIntel({ site_id: siteId }),
};

function GateBadge({ status }) {
  const cfg = GATE_BADGE[status] || GATE_BADGE.OK;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}
    >
      <Icon size={12} />
      {cfg.label}
    </span>
  );
}

export default function CompliancePipelinePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { sitesLoading } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { openActionDrawer } = useActionDrawer();

  function fetchData() {
    setLoading(true);
    setError(null);
    getPortfolioComplianceSummary()
      .then(setData)
      .catch((err) => {
        setError(err?.message || 'Erreur lors du chargement du pipeline conformité');
        toast('Erreur lors du chargement du pipeline conformité', 'error');
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading || sitesLoading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-gray-200 rounded" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg" />
            ))}
          </div>
          <div className="h-60 bg-gray-200 rounded-lg" />
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <ShieldCheck size={24} className="text-blue-600" />
          Pipeline Conformité
        </h1>
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  if (!data || data.total_sites === 0) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <ShieldCheck size={24} className="text-blue-600" />
          Pipeline Conformité
        </h1>
        <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
          <Building size={48} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun site dans le portefeuille</p>
          <p className="text-sm mt-1">
            <Link to="/patrimoine" className="text-blue-600 hover:underline">
              Ajoutez des sites
            </Link>{' '}
            pour démarrer l'évaluation.
          </p>
        </div>
      </div>
    );
  }

  const { kpis, top_blockers, deadlines, untrusted_sites, sites } = data;
  const totalDeadlines = deadlines.d30.length + deadlines.d90.length + deadlines.d180.length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8" data-section="compliance-pipeline">
      {/* Lot 6 Phase 5 — CompliancePipelineSol hero Pattern B injecté top.
          Legacy body (3 KPIs cards + top_blockers + deadlines + untrusted +
          sites table) wrapped {false && (…)} ci-dessous pour rollback.
          Voir header top-of-file pour détails des violations tolérées. */}
      <CompliancePipelineSol
        summary={data}
        isLoading={false}
        error={null}
        onRowClick={(row) => navigate(toSiteCompliance(row.id))}
      />

      {false && (
      <>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldCheck size={24} className="text-blue-600" />
            Pipeline Conformité
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {data.total_sites} sites — Readiness Gate, obligations, échéances
          </p>
        </div>
        <button
          onClick={() =>
            openActionDrawer({ prefill: { type: 'conformite' }, sourceType: 'compliance' })
          }
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          data-testid="cta-creer-action"
        >
          Créer action
        </button>
      </div>

      {/* 3 KPIs */}
      <div className="grid grid-cols-3 gap-4 mb-6" data-section="pipeline-kpis">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
          <p className="text-xs text-gray-500 mb-1">Sites bloqués (gate)</p>
          <p className="text-2xl font-bold text-red-600">{kpis.data_blocked ?? 0}</p>
          <p className="text-xs text-gray-400 mt-0.5">Données manquantes critiques</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-amber-500">
          <p className="text-xs text-gray-500 mb-1">Sites incomplets</p>
          <p className="text-2xl font-bold text-amber-600">{kpis.data_warning ?? 0}</p>
          <p className="text-xs text-gray-400 mt-0.5">Données recommandées manquantes</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
          <p className="text-xs text-gray-500 mb-1">Sites prêts</p>
          <p className="text-2xl font-bold text-green-600">{kpis.data_ready ?? 0}</p>
          <p className="text-xs text-gray-400 mt-0.5">Évaluation complète possible</p>
        </div>
      </div>

      {/* Top 10 blockers */}
      {top_blockers.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-6" data-section="pipeline-blockers">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <AlertOctagon size={16} className="text-red-500" />
            Top blocages gate ({top_blockers.length})
          </h3>
          <div className="space-y-2">
            {top_blockers.map((b, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded bg-red-50">
                <span className="text-sm font-bold text-gray-400 w-6">{i + 1}</span>
                <span className="text-sm text-gray-700 flex-1 font-medium">{b.cta_label}</span>
                <span className="text-xs text-gray-400">{b.regulation}</span>
                <span className="text-xs bg-red-200 text-red-700 px-2 py-0.5 rounded font-medium">
                  {b.count} site{b.count > 1 ? 's' : ''}
                </span>
                <button
                  onClick={() => navigate(CTA_ROUTES[b.cta_target]?.() || '/patrimoine')}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                >
                  Corriger <ArrowRight size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deadlines 30/90/180 */}
      {totalDeadlines > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-6" data-section="pipeline-deadlines">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Clock size={16} className="text-amber-500" />
            Prochaines échéances ({totalDeadlines})
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                label: '30 jours',
                items: deadlines.d30,
                color: 'border-red-400',
                textColor: 'text-red-600',
              },
              {
                label: '90 jours',
                items: deadlines.d90,
                color: 'border-amber-400',
                textColor: 'text-amber-600',
              },
              {
                label: '180 jours',
                items: deadlines.d180,
                color: 'border-blue-400',
                textColor: 'text-blue-600',
              },
            ].map(({ label, items, color, textColor }) => (
              <div key={label} className={`border-l-2 ${color} pl-3`}>
                <p className={`text-xs font-semibold ${textColor} mb-2`}>
                  {label} ({items.length})
                </p>
                {items.length === 0 ? (
                  <p className="text-xs text-gray-400">Aucune</p>
                ) : (
                  <ul className="space-y-1.5">
                    {items.slice(0, 5).map((d, i) => (
                      <li key={i} className="text-xs text-gray-600">
                        <span className="font-medium">{d.site_nom}</span> — {d.regulation}
                        <span className="ml-1 text-gray-400">({d.days_remaining}j)</span>
                      </li>
                    ))}
                    {items.length > 5 && (
                      <li className="text-xs text-gray-400">+{items.length - 5} autres</li>
                    )}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Untrusted sites */}
      {untrusted_sites.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-6" data-section="pipeline-untrusted">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Database size={16} className="text-orange-500" />
            Données non fiables ({untrusted_sites.length} sites)
          </h3>
          <div className="space-y-2">
            {untrusted_sites.map((s) => (
              <div key={s.site_id} className="flex items-center gap-3 p-2 rounded bg-orange-50">
                <span className="text-sm font-medium text-gray-700 flex-1">{s.site_nom}</span>
                <span className="text-xs text-orange-600">Confiance: {s.trust_score}%</span>
                <span className="text-xs text-gray-400">{s.anomaly_count} anomalie(s)</span>
                <button
                  onClick={() => navigate(toBillIntel({ site_id: s.site_id }))}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                >
                  Voir factures <ArrowRight size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sites table */}
      <div
        className="bg-white rounded-lg shadow overflow-hidden"
        data-section="pipeline-sites-table"
      >
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Site</th>
              <th className="px-4 py-3 text-left">Gate</th>
              <th className="px-4 py-3 text-center">Complétude</th>
              <th className="px-4 py-3 text-center">Risque régl.</th>
              <th className="px-4 py-3 text-right">Opportunité (€)</th>
              <th className="px-4 py-3 text-center">Tertiaire</th>
              <th className="px-4 py-3 text-center">BACS</th>
              <th className="px-4 py-3 text-center">APER</th>
              <th className="px-4 py-3 text-center" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sites.map((s) => (
              <tr key={s.site_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{s.site_nom}</td>
                <td className="px-4 py-3">
                  <GateBadge status={s.gate_status} />
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="w-16 mx-auto bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        s.completeness_pct >= 80
                          ? 'bg-green-500'
                          : s.completeness_pct >= 50
                            ? 'bg-amber-500'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${s.completeness_pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400">{s.completeness_pct}%</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`text-xs font-bold ${
                      s.reg_risk >= 60
                        ? 'text-red-600'
                        : s.reg_risk >= 30
                          ? 'text-amber-600'
                          : 'text-green-600'
                    }`}
                  >
                    {s.reg_risk}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {s.financial_opportunity_eur > 0
                    ? `${s.financial_opportunity_eur.toLocaleString('fr-FR')} €`
                    : '-'}
                </td>
                {['tertiaire_operat', 'bacs', 'aper'].map((reg) => (
                  <td key={reg} className="px-4 py-3 text-center">
                    {s.applicability[reg] === true && (
                      <CheckCircle size={14} className="text-green-500 mx-auto" />
                    )}
                    {s.applicability[reg] === false && (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                    {s.applicability[reg] === null && (
                      <AlertTriangle size={14} className="text-amber-400 mx-auto" />
                    )}
                  </td>
                ))}
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => navigate(toSiteCompliance(s.site_id))}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Action creation handled by ActionDrawerContext */}
    </>
      )}
    </div>
  );
}
