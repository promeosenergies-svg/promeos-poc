/**
 * PatrimoinePortfolioHealthBar — V61
 * Bandeau cockpit en-tête de /patrimoine.
 *
 * V60 : risque global, framework dominant, top sites à risque.
 * V61 enrichissements :
 *   A. Breakdown santé : % sains (score ≥ 85) · warning · critical
 *   B. Top 3 frameworks dominants avec compte d'anomalies — "Décret Tertiaire (8)"
 *   C. Trend (↑/↓/—) vs snapshot précédent — null-safe (affiche "—" si pas d'historique)
 *
 * Props:
 *   onSiteClick(site_id) — ouvre SiteDrawer sur onglet Anomalies
 *
 * États :
 *   loading  → skeleton
 *   error    → message + retry
 *   sites_count === 0 → bandeau "0 €" + CTA "Charger la démo" → /import
 *   nominal  → cockpit complet
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Euro,
  ChevronRight,
  RefreshCw,
  Upload,
  Loader2,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { getPatrimoinePortfolioSummary, seedDemoPack, clearApiCache } from '../services/api';
import { fmtEur } from '../utils/format';
import { useScope } from '../contexts/ScopeContext';

/* ── Constantes ──────────────────────────────────────────────────────────── */

const FRAMEWORK_LABEL = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  FACTURATION: 'Facturation',
  BACS: 'BACS',
};

const FRAMEWORK_CHIP_COLOR = {
  DECRET_TERTIAIRE: 'bg-purple-50 text-purple-700 border-purple-100',
  FACTURATION: 'bg-blue-50 text-blue-700 border-blue-100',
  BACS: 'bg-teal-50 text-teal-700 border-teal-100',
};

/* ── Utilitaires ──────────────────────────────────────────────────────────── */

function fmtRisk(eur) {
  if (!eur || eur <= 0) return '0 €';
  return fmtEur(eur);
}

/* ── Sous-composants ─────────────────────────────────────────────────────── */

/** Chip framework avec compteur optionnel — "Décret Tertiaire (8)" */
function FrameworkPill({ framework, count }) {
  const label = FRAMEWORK_LABEL[framework] || framework;
  const color = FRAMEWORK_CHIP_COLOR[framework] || 'bg-gray-50 text-gray-600 border-gray-100';
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded border shrink-0 ${color}`}
    >
      {label}
      {count != null && (
        <span className="font-normal opacity-70 normal-case tracking-normal">({count})</span>
      )}
    </span>
  );
}

/**
 * Indicateur de tendance — null-safe.
 * direction : "up" = risque en hausse (rouge) | "down" = baisse (vert) | "stable" | null → "—"
 */
function TrendBadge({ trend }) {
  if (!trend || trend.direction == null) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[11px] text-gray-300">
        <Minus size={11} /> Tendance
      </span>
    );
  }
  if (trend.direction === 'up') {
    return (
      <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-red-500">
        <TrendingUp size={12} /> Hausse
      </span>
    );
  }
  if (trend.direction === 'down') {
    return (
      <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-green-600">
        <TrendingDown size={12} /> Baisse
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-[11px] text-gray-400">
      <Minus size={11} /> Stable
    </span>
  );
}

/** Barre de santé — healthy (vert) / warning (amber) / critical (rouge) */
function HealthBar({ sites_health, sites_count }) {
  const healthy = sites_health?.healthy ?? 0;
  const warning = sites_health?.warning ?? 0;
  const critical = sites_health?.critical ?? 0;
  const pct = sites_health?.healthy_pct ?? 0;

  const pctH = sites_count > 0 ? Math.round((healthy / sites_count) * 100) : 0;
  const pctW = sites_count > 0 ? Math.round((warning / sites_count) * 100) : 0;
  const pctC = sites_count > 0 ? Math.round((critical / sites_count) * 100) : 0;

  return (
    <div className="flex items-center gap-2">
      <ShieldCheck size={14} className="text-green-500 shrink-0" />
      <div className="flex items-center gap-1.5">
        <span className="text-sm font-bold text-green-600">{pct}%</span>
        <span className="text-xs text-gray-500">sains</span>
      </div>
      {/* Mini progress bar */}
      <div className="flex h-1.5 w-16 rounded-full overflow-hidden bg-gray-100">
        {pctH > 0 && <div className="bg-green-400 h-full" style={{ width: `${pctH}%` }} />}
        {pctW > 0 && <div className="bg-amber-400 h-full" style={{ width: `${pctW}%` }} />}
        {pctC > 0 && <div className="bg-red-400 h-full" style={{ width: `${pctC}%` }} />}
      </div>
      <span className="text-[10px] text-gray-400">
        {healthy}✓ · {warning}⚠ · {critical}✗
      </span>
    </div>
  );
}

/* ── Composant principal ─────────────────────────────────────────────────── */

/**
 * orgId — org_id courant passé par la page parente (Patrimoine.jsx via useScope).
 * Le fetch n'est déclenché que lorsque orgId est non-null, ce qui évite la
 * condition de course React (les useEffect enfants s'exécutent avant les parents).
 */
export default function PatrimoinePortfolioHealthBar({ onSiteClick, orgId = null }) {
  const navigate = useNavigate();
  const { applyDemoScope } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [seeding, setSeeding] = useState(false);

  const fetchSummary = () => {
    // [DIAG V63] Vérifie que orgId et X-Org-Id sont cohérents au moment du fetch.
    // À retirer après validation E2E.
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[PortfolioHealthBar] fetchSummary fired', {
        orgId,
        timestamp: new Date().toISOString(),
      });
    }
    setLoading(true);
    setError(null);
    getPatrimoinePortfolioSummary()
      .then((result) => {
        if (process.env.NODE_ENV !== 'production') {
          console.debug('[PortfolioHealthBar] fetchSummary success', {
            sites_count: result?.sites_count,
            scope_org_id: result?.scope?.org_id,
          });
        }
        setData(result);
      })
      .catch((err) => {
        if (process.env.NODE_ENV !== 'production') {
          console.warn('[PortfolioHealthBar] fetchSummary error', { err, orgId });
        }
        setError('Impossible de charger le résumé portfolio.');
      })
      .finally(() => setLoading(false));
  };

  // Dépend de orgId : ne fetch que quand l'org est résolu, et refetch si elle change.
  useEffect(() => {
    if (!orgId) return;
    let stale = false;
    setLoading(true);
    setError(null);
    getPatrimoinePortfolioSummary()
      .then((result) => {
        if (!stale) setData(result);
      })
      .catch(() => {
        if (!stale) setError('Impossible de charger le résumé portfolio.');
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [orgId]);

  /* ── États ── */

  // orgId pas encore résolu (ScopeContext en cours d'init) → skeleton discret
  if (!orgId) {
    return <div className="animate-pulse bg-gray-50 border border-gray-100 rounded-xl p-4 h-16" />;
  }

  if (loading) {
    return <div className="animate-pulse bg-gray-50 border border-gray-100 rounded-xl p-4 h-16" />;
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-50 border border-gray-100 rounded-xl px-4 py-3">
        <AlertTriangle size={14} className="text-amber-400 shrink-0" />
        <span>{error}</span>
        <button
          onClick={fetchSummary}
          className="ml-auto flex items-center gap-1 text-blue-600 hover:underline"
        >
          <RefreshCw size={11} /> Réessayer
        </button>
      </div>
    );
  }

  if (!data) return null;

  // Direct seed HELIOS — called when button clicked
  const handleSeedHelios = async () => {
    setSeeding(true);
    try {
      const res = await seedDemoPack('helios', 'S', true);
      clearApiCache();
      if (res.org_id) {
        applyDemoScope({
          orgId: res.org_id,
          orgNom: res.org_nom,
          defaultSiteId: res.default_site_id,
          defaultSiteName: res.default_site_name,
        });
      }
      // Navigate to same page to refresh all components with new data
      navigate(0);
    } catch {
      setError('Échec du chargement. Essayez via la page Import.');
      setSeeding(false);
    }
  };

  // Cas critique : aucune org / aucun site après reset
  if (data.sites_count === 0) {
    return (
      <div className="flex items-center justify-between bg-gray-50 border border-dashed border-gray-200 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <AlertTriangle size={15} className="text-amber-400 shrink-0" />
          <span>
            Aucun site chargé — risque global : <strong className="text-gray-700">0 €</strong>
          </span>
        </div>
        <button
          onClick={handleSeedHelios}
          disabled={seeding}
          className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5 hover:bg-blue-100 transition disabled:opacity-50"
        >
          {seeding ? (
            <>
              <Loader2 size={12} className="animate-spin" /> Chargement...
            </>
          ) : (
            <>
              <Upload size={12} /> Charger la démo
            </>
          )}
        </button>
      </div>
    );
  }

  /* ── Vue cockpit nominale ── */

  const {
    total_estimated_risk_eur,
    sites_count,
    sites_at_risk,
    sites_health,
    framework_breakdown,
    top_sites,
    trend,
  } = data;

  // Top 3 frameworks dominants (déjà triés risk_eur DESC par le backend)
  const top3Fw = (framework_breakdown ?? []).slice(0, 3);

  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 space-y-2.5">
      {/* ── Ligne 1 : métriques clés ── */}
      <div className="flex items-center gap-4 flex-wrap">
        {/* Risque global */}
        <div className="flex items-center gap-1.5">
          <Euro size={14} className="text-red-500 shrink-0" />
          <span className="text-sm text-gray-600">Risque global :</span>
          <span className="text-sm font-bold text-red-600">
            {fmtRisk(total_estimated_risk_eur)}
          </span>
        </div>

        {/* Santé des données (V61) */}
        <HealthBar sites_health={sites_health} sites_count={sites_count} />

        {/* Trend (V61) — null-safe */}
        <TrendBadge trend={trend} />

        {/* Sites critiques (si > 0) */}
        {(sites_at_risk?.critical ?? 0) + (sites_at_risk?.high ?? 0) > 0 && (
          <div className="flex items-center gap-1 ml-auto">
            <AlertTriangle size={13} className="text-orange-500 shrink-0" />
            <span className="text-xs font-semibold text-orange-600">
              {(sites_at_risk.critical ?? 0) + (sites_at_risk.high ?? 0)} site
              {(sites_at_risk.critical ?? 0) + (sites_at_risk.high ?? 0) > 1 ? 's' : ''} critiques
            </span>
          </div>
        )}
      </div>

      {/* ── Ligne 2 : frameworks dominants top 3 (V61 — avec comptes) ── */}
      {top3Fw.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mr-1">
            Frameworks :
          </span>
          {top3Fw.map((fw) => (
            <FrameworkPill key={fw.framework} framework={fw.framework} count={fw.anomalies_count} />
          ))}
        </div>
      )}

      {/* ── Top sites à risque ── */}
      {top_sites.length > 0 && (
        <div className="border-t border-gray-100 pt-2.5 space-y-1.5">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
            Top sites à risque
          </p>
          {top_sites.map((s) => (
            <div key={s.site_id} className="flex items-center gap-2 min-w-0">
              <span className="font-medium text-gray-800 text-sm truncate flex-1 min-w-0">
                {s.site_nom}
              </span>
              {s.top_framework && <FrameworkPill framework={s.top_framework} />}
              <span className="text-xs font-semibold text-red-600 shrink-0">
                {fmtRisk(s.risk_eur)}
              </span>
              <button
                onClick={() => onSiteClick?.(s.site_id)}
                className="shrink-0 flex items-center gap-0.5 text-[11px] font-semibold text-blue-600 hover:underline"
              >
                Voir anomalies <ChevronRight size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
