/**
 * PatrimoinePortfolioHealthBar — V60
 * Bandeau cockpit en-tête de /patrimoine : risque global, framework dominant, top sites.
 *
 * Props:
 *   onSiteClick(site_id) — callback pour ouvrir le SiteDrawer sur onglet Anomalies
 *
 * États gérés :
 *   - loading   : skeleton
 *   - error     : message + retry
 *   - sites_count === 0 : bandeau "0 €" + CTA "Charger HELIOS" → /import
 *   - nominal   : risque global, sites critiques, framework dominant, top sites
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Euro, ChevronRight, RefreshCw, Upload } from 'lucide-react';
import { getPatrimoinePortfolioSummary } from '../services/api';

/* ── Constantes ──────────────────────────────────────────────────────────── */

const FRAMEWORK_LABEL = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  FACTURATION:      'Facturation',
  BACS:             'BACS',
};

const FRAMEWORK_CHIP_COLOR = {
  DECRET_TERTIAIRE: 'bg-purple-50 text-purple-700 border-purple-100',
  FACTURATION:      'bg-blue-50 text-blue-700 border-blue-100',
  BACS:             'bg-teal-50 text-teal-700 border-teal-100',
};

function fmtRisk(eur) {
  if (!eur || eur <= 0) return '0 €';
  if (eur >= 1_000_000) return `~${(eur / 1_000_000).toFixed(1)} M€`;
  if (eur >= 1_000) return `~${(eur / 1_000).toFixed(0)} k€`;
  return `~${Math.round(eur)} €`;
}

function FrameworkPill({ framework }) {
  const label = FRAMEWORK_LABEL[framework] || framework;
  const color = FRAMEWORK_CHIP_COLOR[framework] || 'bg-gray-50 text-gray-600 border-gray-100';
  return (
    <span className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded border ${color} shrink-0`}>
      {label}
    </span>
  );
}

/* ── Composant principal ─────────────────────────────────────────────────── */

export default function PatrimoinePortfolioHealthBar({ onSiteClick }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSummary = () => {
    setLoading(true);
    setError(null);
    getPatrimoinePortfolioSummary()
      .then(setData)
      .catch(() => setError('Impossible de charger le résumé portfolio.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSummary(); }, []);

  /* ── États ── */

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-50 border border-gray-100 rounded-xl p-4 h-16" />
    );
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

  // Cas critique : aucune org / aucun site après reset
  if (data.sites_count === 0) {
    return (
      <div className="flex items-center justify-between bg-gray-50 border border-dashed border-gray-200 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <AlertTriangle size={15} className="text-amber-400 shrink-0" />
          <span>
            Aucun site chargé — risque global :{' '}
            <strong className="text-gray-700">0 €</strong>
          </span>
        </div>
        <button
          onClick={() => navigate('/import')}
          className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5 hover:bg-blue-100 transition"
        >
          <Upload size={12} /> Charger HELIOS
        </button>
      </div>
    );
  }

  /* ── Vue nominale ── */

  const { total_estimated_risk_eur, sites_at_risk, framework_breakdown, top_sites } = data;
  const dominantFw = framework_breakdown[0] ?? null;
  const totalAtRisk = (sites_at_risk?.critical ?? 0) + (sites_at_risk?.high ?? 0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 space-y-2.5">

      {/* ── Ligne d'indicateurs ── */}
      <div className="flex items-center gap-4 flex-wrap">

        {/* Risque global */}
        <div className="flex items-center gap-1.5">
          <Euro size={14} className="text-red-500 shrink-0" />
          <span className="text-sm text-gray-600">Risque global estimé :</span>
          <span className="text-sm font-bold text-red-600">{fmtRisk(total_estimated_risk_eur)}</span>
        </div>

        {/* Sites critiques / élevés */}
        {totalAtRisk > 0 && (
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={13} className="text-orange-500 shrink-0" />
            <span className="text-sm text-gray-600">Sites critiques :</span>
            <span className="text-sm font-semibold text-orange-600">{totalAtRisk}</span>
          </div>
        )}

        {/* Framework dominant */}
        {dominantFw && (
          <div className="flex items-center gap-1.5 ml-auto">
            <FrameworkPill framework={dominantFw.framework} />
            <span className="text-xs text-gray-400">dominant</span>
          </div>
        )}
      </div>

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
