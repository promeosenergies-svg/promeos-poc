/**
 * AnomaliesPage — V65
 * Action Center cross-sites : liste agrégée des anomalies du scope courant.
 * Route : /anomalies
 *
 * Data : Promise.all sur scopedSites.slice(0, 20) via getPatrimoineAnomalies.
 * KPIs : total anomalies | critiques | risque € estimé.
 * Filtres : framework, severity, site, recherche texte.
 * Tri : impact € DESC puis priority_score DESC.
 * CTAs : "Ouvrir site" (→ /patrimoine avec drawer) + "Créer action" (AnomalyActionModal).
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Search, X, Euro, ChevronRight, Building2, Upload,
} from 'lucide-react';
import { PageShell, EmptyState, Tooltip } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { getPatrimoineAnomalies } from '../services/api';
import {
  getAnomalyAction,
  ACTION_STATUS_LABEL,
  ACTION_STATUS_COLOR,
} from '../services/anomalyActions';
import AnomalyActionModal from '../components/AnomalyActionModal';

/* ── Constantes ── */

const MAX_SITES = 20;

const SEV_LABEL   = { CRITICAL: 'Critique', HIGH: 'Élevé', MEDIUM: 'Moyen', LOW: 'Faible' };
const SEV_COLOR   = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH:     'bg-orange-100 text-orange-700',
  MEDIUM:   'bg-amber-100 text-amber-700',
  LOW:      'bg-blue-100 text-blue-700',
};
const FW_LABEL  = { DECRET_TERTIAIRE: 'Décret Tertiaire', FACTURATION: 'Facturation', BACS: 'BACS' };
const FW_COLOR  = {
  DECRET_TERTIAIRE: 'bg-purple-50 text-purple-700',
  FACTURATION:      'bg-blue-50 text-blue-700',
  BACS:             'bg-teal-50 text-teal-700',
};

function fmtEur(n) {
  if (!n || n <= 0) return '—';
  if (n >= 1_000_000) return `~${(n / 1_000_000).toFixed(1)} M€`;
  if (n >= 1_000)     return `~${Math.round(n / 1_000)} k€`;
  return `~${Math.round(n)} €`;
}

/* ── Page ── */

export default function AnomaliesPage() {
  const navigate = useNavigate();
  const { scopedSites, scope, sitesLoading } = useScope();

  const [anomalies, setAnomalies] = useState([]);  // flat [{...anomaly, site_id, site_nom}]
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const fetchIdRef                = useRef(0);

  // Filtres
  const [filterFw,   setFilterFw]   = useState('');
  const [filterSev,  setFilterSev]  = useState('');
  const [filterSite, setFilterSite] = useState('');
  const [search,     setSearch]     = useState('');

  // Modale action
  const [actionModal, setActionModal] = useState(null); // { code, title, siteId }
  const [actionTick,  setActionTick]  = useState(0);

  /* ── Fetch anomalies ── */
  useEffect(() => {
    if (scopedSites.length === 0) {
      setAnomalies([]);
      setLoading(false);
      return;
    }
    const sitesToFetch = scopedSites.slice(0, MAX_SITES);
    const fetchId = ++fetchIdRef.current;
    setLoading(true);
    setError(null);

    Promise.all(
      sitesToFetch.map(site =>
        getPatrimoineAnomalies(site.id)
          .then(data => ({ site, data, ok: true }))
          .catch(() => ({ site, data: null, ok: false }))
      )
    ).then(results => {
      if (fetchIdRef.current !== fetchId) return;
      const flat = results.flatMap(({ site, data, ok }) => {
        if (!ok || !data) return [];
        return (data.anomalies ?? []).map(a => ({
          ...a,
          site_id:  site.id,
          site_nom: site.nom,
        }));
      });
      setAnomalies(flat);
      setLoading(false);
    }).catch(() => {
      if (fetchIdRef.current !== fetchId) return;
      setError('Impossible de charger les anomalies du parc.');
      setLoading(false);
    });
  }, [scopedSites]);

  /* ── KPIs ── */
  const kpis = useMemo(() => {
    const total     = anomalies.length;
    const critiques = anomalies.filter(a => a.severity === 'CRITICAL').length;
    const risque    = anomalies.reduce((s, a) => s + (a.business_impact?.estimated_risk_eur ?? 0), 0);
    return { total, critiques, risque };
  }, [anomalies]);

  /* ── Filtrage + tri ── */
  const filtered = useMemo(() => {
    let r = [...anomalies];
    if (filterFw)   r = r.filter(a => a.regulatory_impact?.framework === filterFw);
    if (filterSev)  r = r.filter(a => a.severity === filterSev);
    if (filterSite) r = r.filter(a => String(a.site_id) === filterSite);
    if (search) {
      const q = search.toLowerCase();
      r = r.filter(a =>
        a.title_fr?.toLowerCase().includes(q) ||
        a.site_nom?.toLowerCase().includes(q)
      );
    }
    // Tri : impact € DESC puis priority_score DESC
    r.sort((a, b) => {
      const ra = a.business_impact?.estimated_risk_eur ?? 0;
      const rb = b.business_impact?.estimated_risk_eur ?? 0;
      if (rb !== ra) return rb - ra;
      return (b.priority_score ?? 0) - (a.priority_score ?? 0);
    });
    return r;
  }, [anomalies, filterFw, filterSev, filterSite, search]);

  /* ── Helpers ── */
  const hasFilters = filterFw || filterSev || filterSite || search;

  function resetFilters() {
    setFilterFw(''); setFilterSev(''); setFilterSite(''); setSearch('');
  }

  function openSite(siteId) {
    navigate('/patrimoine', { state: { openSiteId: siteId, openTab: 'anomalies' } });
  }

  /* ── Rendu ── */

  if (sitesLoading) {
    return (
      <PageShell icon={AlertTriangle} title="Action Center" subtitle="Chargement...">
        <div className="space-y-2 animate-pulse">
          {[...Array(4)].map((_, i) => <div key={i} className="h-14 bg-gray-100 rounded-lg" />)}
        </div>
      </PageShell>
    );
  }

  if (scopedSites.length === 0) {
    return (
      <PageShell icon={AlertTriangle} title="Action Center" subtitle="Aucun site dans le scope">
        <EmptyState
          icon={Building2}
          title="Aucun site dans le scope"
          text="Importez votre patrimoine ou chargez les données de démonstration HELIOS pour voir les anomalies."
          ctaLabel="Importer mon patrimoine"
          onCta={() => navigate('/import')}
          actions={
            <button onClick={() => navigate('/import')} className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-4 py-2 hover:bg-blue-100 transition">
              <Upload size={14} /> Charger HELIOS
            </button>
          }
        />
      </PageShell>
    );
  }

  const subtitle = loading
    ? 'Chargement des anomalies...'
    : `${kpis.total} anomalie${kpis.total > 1 ? 's' : ''} · ${kpis.critiques} critique${kpis.critiques > 1 ? 's' : ''} · ${fmtEur(kpis.risque)} de risque estimé`;

  return (
    <PageShell icon={AlertTriangle} title="Action Center" subtitle={subtitle}>
      <div className="space-y-4">

        {/* ── KPI row ── */}
        <div className="grid grid-cols-3 gap-3">
          <KpiCard icon={AlertTriangle} color="bg-blue-600"  label="Anomalies totales" value={kpis.total}    loading={loading} />
          <KpiCard icon={AlertTriangle} color="bg-red-600"   label="Critiques"         value={kpis.critiques} loading={loading} />
          <KpiCard icon={Euro}          color="bg-amber-600" label="Risque estimé"     value={fmtEur(kpis.risque)} loading={loading} />
        </div>

        {/* ── Toolbar ── */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Recherche texte */}
          <div className="relative flex-1 min-w-[180px] max-w-sm">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher une anomalie ou un site..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            />
          </div>

          {/* Framework */}
          <QuickSelect
            value={filterFw}
            onChange={setFilterFw}
            options={[
              { value: '',                 label: 'Framework'        },
              { value: 'DECRET_TERTIAIRE', label: 'Décret Tertiaire' },
              { value: 'FACTURATION',      label: 'Facturation'      },
              { value: 'BACS',             label: 'BACS'             },
            ]}
          />

          {/* Sévérité */}
          <QuickSelect
            value={filterSev}
            onChange={setFilterSev}
            options={[
              { value: '',         label: 'Sévérité' },
              { value: 'CRITICAL', label: 'Critique' },
              { value: 'HIGH',     label: 'Élevé'    },
              { value: 'MEDIUM',   label: 'Moyen'    },
              { value: 'LOW',      label: 'Faible'   },
            ]}
          />

          {/* Site */}
          <QuickSelect
            value={filterSite}
            onChange={setFilterSite}
            options={[
              { value: '', label: 'Tous les sites' },
              ...scopedSites.slice(0, MAX_SITES).map(s => ({ value: String(s.id), label: s.nom })),
            ]}
          />

          {/* Reset */}
          {hasFilters && (
            <button onClick={resetFilters} className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition">
              <X size={12} /> Réinitialiser
            </button>
          )}
        </div>

        {/* ── Erreur ── */}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-2">
            <AlertTriangle size={13} className="shrink-0" /> {error}
          </div>
        )}

        {/* ── Liste anomalies ── */}
        {loading ? (
          <div className="space-y-2 animate-pulse">
            {[...Array(5)].map((_, i) => <div key={i} className="h-14 bg-gray-100 rounded-lg" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-10 text-gray-400">
            <Search size={28} className="mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-600">Aucune anomalie ne correspond</p>
            {hasFilters && (
              <button onClick={resetFilters} className="mt-2 text-xs text-blue-600 hover:underline">
                Réinitialiser les filtres
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-1.5">
            {filtered.map((anom, idx) => {
              // actionTick forces re-read after modal save
              void actionTick;
              const currentAction = getAnomalyAction(scope.orgId, anom.site_id, anom.code);
              const statusLabel   = currentAction ? ACTION_STATUS_LABEL[currentAction.status] : null;
              const statusColor   = currentAction ? ACTION_STATUS_COLOR[currentAction.status]  : null;
              const impactFmt     = fmtEur(anom.business_impact?.estimated_risk_eur);

              return (
                <div
                  key={`${anom.site_id}-${anom.code}-${idx}`}
                  className="flex items-start gap-3 px-3 py-2.5 bg-white border border-gray-100 rounded-lg hover:border-gray-200 transition"
                >
                  {/* Infos anomalie */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Site */}
                      <span className="text-[10px] font-medium text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 shrink-0">
                        {anom.site_nom}
                      </span>
                      {/* Severity */}
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${SEV_COLOR[anom.severity] ?? 'bg-gray-100 text-gray-600'}`}>
                        {SEV_LABEL[anom.severity] ?? anom.severity}
                      </span>
                      {/* Framework */}
                      {anom.regulatory_impact?.framework && anom.regulatory_impact.framework !== 'NONE' && (
                        <span className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0 ${FW_COLOR[anom.regulatory_impact.framework] ?? 'bg-gray-50 text-gray-600'}`}>
                          {FW_LABEL[anom.regulatory_impact.framework] ?? anom.regulatory_impact.framework}
                        </span>
                      )}
                      {/* Titre */}
                      <span className="text-sm font-medium text-gray-800 truncate">{anom.title_fr}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      {impactFmt !== '—' && (
                        <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
                          <Euro size={9} /> {impactFmt}
                        </span>
                      )}
                      {statusLabel && (
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${statusColor}`}>
                          {statusLabel}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* CTAs */}
                  <div className="flex items-center gap-1 shrink-0">
                    <Tooltip text="Ouvrir la fiche site (onglet Anomalies)">
                      <button
                        type="button"
                        onClick={() => openSite(anom.site_id)}
                        className="flex items-center gap-1 text-[11px] font-medium text-blue-600 bg-blue-50 border border-blue-100 rounded px-2 py-1 hover:bg-blue-100 transition"
                      >
                        Ouvrir site <ChevronRight size={11} />
                      </button>
                    </Tooltip>
                    <Tooltip text="Créer ou modifier l'action locale">
                      <button
                        type="button"
                        onClick={() => setActionModal({ code: anom.code, title: anom.title_fr, siteId: anom.site_id })}
                        className="text-[11px] font-medium text-gray-600 bg-gray-100 border border-gray-200 rounded px-2 py-1 hover:bg-gray-200 transition"
                      >
                        Créer action
                      </button>
                    </Tooltip>
                  </div>
                </div>
              );
            })}

            <p className="text-[11px] text-gray-400 text-center pt-1">
              {filtered.length} résultat{filtered.length > 1 ? 's' : ''}
              {scopedSites.length > MAX_SITES && ` · ${MAX_SITES} sites analysés sur ${scopedSites.length}`}
            </p>
          </div>
        )}

      </div>

      {/* Modale action */}
      {actionModal && (
        <AnomalyActionModal
          open={!!actionModal}
          onClose={() => {
            setActionModal(null);
            setActionTick(t => t + 1);
          }}
          orgId={scope.orgId}
          siteId={actionModal.siteId}
          anomalyCode={actionModal.code}
          anomalyTitle={actionModal.title}
        />
      )}
    </PageShell>
  );
}

/* ── Sous-composants ── */

function KpiCard({ icon: Icon, color, label, value, loading }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-3 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon size={16} className="text-white" />
      </div>
      <div>
        <p className="text-[11px] text-gray-400 font-medium">{label}</p>
        {loading
          ? <div className="h-5 w-12 bg-gray-100 rounded animate-pulse mt-0.5" />
          : <p className="text-lg font-bold text-gray-900 leading-tight">{value}</p>
        }
      </div>
    </div>
  );
}

function QuickSelect({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={`text-xs px-2.5 py-1.5 rounded-lg border bg-white cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        value ? 'border-blue-300 text-blue-700 font-medium' : 'border-gray-200 text-gray-600'
      }`}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}
