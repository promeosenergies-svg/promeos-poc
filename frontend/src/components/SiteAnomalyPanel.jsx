/**
 * SiteAnomalyPanel — V65
 * Panneau enrichi pour l'onglet Anomalies du SiteDrawer.
 * Remplace PatrimoineHealthCard dans le contexte drawer :
 *   - Toutes les anomalies (pas seulement top 3)
 *   - Filtres rapides : Tous / Critiques / Facturation / Décret Tertiaire / BACS
 *   - Statut action (localStorage) + bouton "Créer action"
 *   - Tri par priority_score DESC
 */
import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, ShieldCheck, AlertCircle, Info, Euro, RefreshCw } from 'lucide-react';
import { getPatrimoineAnomalies } from '../services/api';
import { fmtEur } from '../utils/format';
import { useActionDrawer } from '../contexts/ActionDrawerContext';

/* ── Constantes locales ── */

const SEVERITY_CONFIG = {
  CRITICAL: {
    label: 'Critique',
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: AlertCircle,
    dot: 'bg-red-500',
  },
  HIGH: {
    label: 'Élevé',
    color: 'text-orange-700',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    icon: AlertTriangle,
    dot: 'bg-orange-400',
  },
  MEDIUM: {
    label: 'Moyen',
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: AlertTriangle,
    dot: 'bg-amber-400',
  },
  LOW: {
    label: 'Faible',
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: Info,
    dot: 'bg-blue-400',
  },
};

const FRAMEWORK_CHIP = {
  DECRET_TERTIAIRE: { label: 'Décret Tertiaire', color: 'bg-purple-100 text-purple-700' },
  FACTURATION: { label: 'Facturation', color: 'bg-blue-100 text-blue-700' },
  BACS: { label: 'BACS', color: 'bg-teal-100 text-teal-700' },
  NONE: null,
};

const QUICK_FILTERS = [
  { key: 'all', label: 'Tous' },
  { key: 'CRITICAL', label: 'Critiques' },
  { key: 'FACTURATION', label: 'Facturation' },
  { key: 'DECRET_TERTIAIRE', label: 'Décret Tertiaire' },
  { key: 'BACS', label: 'BACS' },
];

/* ── Sous-composants ── */

function ScoreGauge({ score }) {
  const barColor = score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-amber-400' : 'bg-red-500';
  const textColor =
    score >= 80 ? 'text-green-700' : score >= 50 ? 'text-amber-700' : 'text-red-700';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">Score de complétude</span>
        <span className={`text-sm font-bold ${textColor}`}>{score} / 100</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function fmtEurRisk(eur) {
  if (!eur || eur <= 0) return null;
  return fmtEur(eur);
}

/* ── Composant principal ── */

/**
 * @param {{ siteId: number, orgId: number|null }} props
 */
export default function SiteAnomalyPanel({ siteId, orgId: _orgId }) {
  const { openActionDrawer } = useActionDrawer();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');

  const fetchAnomalies = useCallback(() => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    getPatrimoineAnomalies(siteId)
      .then(setData)
      .catch(() => setError('Impossible de charger les anomalies.'))
      .finally(() => setLoading(false));
  }, [siteId]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  /* ── États de chargement ── */

  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        <div className="h-4 bg-gray-100 rounded w-2/3" />
        <div className="h-2 bg-gray-100 rounded" />
        <div className="h-16 bg-gray-50 rounded-lg border" />
        <div className="h-16 bg-gray-50 rounded-lg border" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6 text-gray-400">
        <AlertTriangle size={22} className="mx-auto mb-1 text-amber-400" />
        <p className="text-xs text-gray-500">{error}</p>
        <button
          onClick={fetchAnomalies}
          className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          <RefreshCw size={11} /> Réessayer
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { anomalies, completude_score, nb_anomalies, total_estimated_risk_eur } = data;

  /* ── Tri : priority_score DESC ── */
  const sortedAnomalies = [...anomalies].sort(
    (a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0)
  );

  /* ── Filtre rapide ── */
  const filteredAnomalies = sortedAnomalies.filter((a) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'CRITICAL') return a.severity === 'CRITICAL';
    return a.regulatory_impact?.framework === activeFilter;
  });

  /* ── État vide ── */
  if (nb_anomalies === 0) {
    return (
      <div className="space-y-3">
        <ScoreGauge score={completude_score} />
        <div className="text-center py-6">
          <ShieldCheck size={28} className="mx-auto mb-2 text-green-400" />
          <p className="text-sm font-medium text-gray-700">Patrimoine complet</p>
          <p className="text-xs text-gray-400">Aucune anomalie détectée sur ce site.</p>
        </div>
      </div>
    );
  }

  const totalRiskFmt = fmtEurRisk(total_estimated_risk_eur);

  return (
    <div className="space-y-3">
      {/* Score */}
      <ScoreGauge score={completude_score} />

      {/* Résumé + risque total */}
      <div className="flex items-center justify-between flex-wrap gap-1">
        <div className="flex items-center gap-1.5 text-xs text-gray-600">
          <AlertTriangle size={13} className="text-amber-500 flex-shrink-0" />
          <span>
            <span className="font-semibold">{nb_anomalies}</span> anomalie
            {nb_anomalies > 1 ? 's' : ''} détectée{nb_anomalies > 1 ? 's' : ''}
          </span>
        </div>
        {totalRiskFmt && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-red-600 bg-red-50 border border-red-100 rounded px-2 py-0.5">
            <Euro size={10} /> Risque estimé {totalRiskFmt}
          </span>
        )}
      </div>

      {/* Filtres rapides */}
      <div className="flex items-center gap-1 flex-wrap">
        {QUICK_FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition whitespace-nowrap ${
              activeFilter === f.key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f.label}
            {f.key === 'all' && (
              <span className="ml-1 text-[10px] opacity-70">({nb_anomalies})</span>
            )}
          </button>
        ))}
      </div>

      {/* Liste anomalies */}
      <div className="space-y-2">
        {filteredAnomalies.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-3">
            Aucune anomalie ne correspond à ce filtre.
          </p>
        ) : (
          filteredAnomalies.map((anom, idx) => {
            const cfg = SEVERITY_CONFIG[anom.severity] || SEVERITY_CONFIG.LOW;
            const framework = anom.regulatory_impact?.framework;
            const fwCfg = framework ? FRAMEWORK_CHIP[framework] : null;
            const impact = anom.business_impact?.estimated_risk_eur;
            const impactFmt = fmtEurRisk(impact);

            return (
              <div
                key={`${anom.code}-${idx}`}
                className={`rounded-lg border p-2.5 ${cfg.bg} ${cfg.border}`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${cfg.dot}`} />
                  <div className="flex-1 min-w-0">
                    {/* Titre + chips */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span
                        className={`text-[10px] font-semibold uppercase tracking-wide ${cfg.color}`}
                      >
                        {cfg.label}
                      </span>
                      {fwCfg && (
                        <span
                          className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${fwCfg.color}`}
                        >
                          {fwCfg.label}
                        </span>
                      )}
                      <span className="text-xs font-medium text-gray-800 truncate">
                        {anom.title_fr}
                      </span>
                    </div>

                    {/* Détail */}
                    <p className="text-[11px] text-gray-600 mt-0.5 leading-snug">
                      {anom.detail_fr}
                    </p>

                    {/* Fix hint */}
                    {anom.fix_hint_fr && (
                      <p className="text-[10px] text-gray-500 mt-0.5 italic">{anom.fix_hint_fr}</p>
                    )}

                    {/* Risque € + score + statut action */}
                    <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                      {impactFmt && (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-gray-500 bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5">
                          <Euro size={9} /> {impactFmt}
                        </span>
                      )}
                      {anom.priority_score != null && (
                        <span className="text-[9px] text-gray-400">
                          score {anom.priority_score}
                        </span>
                      )}
                    </div>

                    {/* CTA Créer action */}
                    <div className="mt-1.5">
                      <button
                        type="button"
                        onClick={() =>
                          openActionDrawer({
                            prefill: { titre: anom.title_fr, type: 'anomalie' },
                            siteId,
                            sourceType: 'anomaly',
                            sourceId: anom.code,
                            idempotencyKey: `anomaly:${siteId}:${anom.code}`,
                          })
                        }
                        className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 hover:underline transition"
                      >
                        Créer action
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Action Drawer — managed by ActionDrawerContext */}
    </div>
  );
}
