/**
 * PatrimoineHealthCard — V59
 * Affiche le score de complétude patrimoine + top anomalies enrichies V59.
 *
 * V59 enrichissements :
 *   - Tri par priority_score DESC (au lieu de sévérité)
 *   - Chip framework réglementaire (Décret Tertiaire / Facturation / BACS)
 *   - Risque estimé € + niveau de confiance
 *   - total_estimated_risk_eur du site
 *
 * Usage : <PatrimoineHealthCard siteId={site.id} />
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, ShieldCheck, AlertCircle, Info,
  ArrowRight, RefreshCw, Euro,
} from 'lucide-react';
import { getPatrimoineAnomalies } from '../services/api';

/* ── Constantes ──────────────────────────────────────────────────────────── */

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
  FACTURATION:      { label: 'Facturation',       color: 'bg-blue-100 text-blue-700'   },
  BACS:             { label: 'BACS',               color: 'bg-teal-100 text-teal-700'   },
  NONE:             null,
};

function scoreColor(score) {
  if (score >= 80) return 'bg-green-500';
  if (score >= 50) return 'bg-amber-400';
  return 'bg-red-500';
}
function scoreTextColor(score) {
  if (score >= 80) return 'text-green-700';
  if (score >= 50) return 'text-amber-700';
  return 'text-red-700';
}

function fmtEurRisk(eur) {
  if (!eur || eur <= 0) return null;
  if (eur >= 1000) return `~${(eur / 1000).toFixed(0)} k€`;
  return `~${eur.toFixed(0)} €`;
}

function fmtConfidence(confidence) {
  if (confidence == null) return null;
  return `${Math.round(confidence * 100)} %`;
}

/* ── Sous-composants ─────────────────────────────────────────────────────── */

function ScoreGauge({ score }) {
  const barColor = scoreColor(score);
  const textColor = scoreTextColor(score);
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

function FrameworkChip({ framework }) {
  const cfg = FRAMEWORK_CHIP[framework];
  if (!cfg) return null;
  return (
    <span className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function RiskBadge({ businessImpact }) {
  if (!businessImpact) return null;
  const { estimated_risk_eur, confidence } = businessImpact;
  const eur = fmtEurRisk(estimated_risk_eur);
  if (!eur) return null;
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-gray-500 bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5">
      <Euro size={9} />
      <span>{eur}</span>
      {confidence != null && (
        <span className="text-gray-400 ml-0.5">conf. {fmtConfidence(confidence)}</span>
      )}
    </span>
  );
}

function AnomalyRow({ anomaly, onCtaClick }) {
  const cfg = SEVERITY_CONFIG[anomaly.severity] || SEVERITY_CONFIG.LOW;
  const framework = anomaly.regulatory_impact?.framework;

  return (
    <div className={`rounded-lg border p-2.5 ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-start gap-2">
        <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${cfg.dot}`} />
        <div className="flex-1 min-w-0">
          {/* Titre + chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={`text-[10px] font-semibold uppercase tracking-wide ${cfg.color}`}>
              {cfg.label}
            </span>
            {framework && <FrameworkChip framework={framework} />}
            <span className="text-xs font-medium text-gray-800 truncate">{anomaly.title_fr}</span>
          </div>

          {/* Détail */}
          <p className="text-[11px] text-gray-600 mt-0.5 leading-snug">{anomaly.detail_fr}</p>

          {/* Fix hint */}
          {anomaly.fix_hint_fr && (
            <p className="text-[10px] text-gray-500 mt-0.5 italic">{anomaly.fix_hint_fr}</p>
          )}

          {/* Risque € + confiance */}
          <div className="mt-1 flex items-center gap-1.5 flex-wrap">
            <RiskBadge businessImpact={anomaly.business_impact} />
            {anomaly.priority_score != null && (
              <span className="text-[9px] text-gray-400">
                score {anomaly.priority_score}
              </span>
            )}
          </div>

          {/* CTA */}
          {anomaly.cta && (
            <button
              onClick={() => onCtaClick(anomaly.cta.to)}
              className={`mt-1.5 inline-flex items-center gap-1 text-[11px] font-semibold ${cfg.color} hover:underline`}
            >
              {anomaly.cta.label} <ArrowRight size={11} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Composant principal ─────────────────────────────────────────────────── */

export default function PatrimoineHealthCard({ siteId }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAnomalies = () => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    getPatrimoineAnomalies(siteId)
      .then(setData)
      .catch(() => setError('Impossible de charger les anomalies.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAnomalies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

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

  // Top 3 par priority_score (déjà trié DESC par le backend V59)
  const topAnomalies = anomalies.slice(0, 3);

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
            {nb_anomalies > 3 ? ` — top 3 prioritaires` : ''}
          </span>
        </div>
        {totalRiskFmt && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-red-600 bg-red-50 border border-red-100 rounded px-2 py-0.5">
            <Euro size={10} /> Risque estimé {totalRiskFmt}
          </span>
        )}
      </div>

      {/* Top anomalies (triées par priority_score) */}
      <div className="space-y-2">
        {topAnomalies.map((anom, idx) => (
          <AnomalyRow
            key={`${anom.code}-${idx}`}
            anomaly={anom}
            onCtaClick={(to) => navigate(to)}
          />
        ))}
      </div>
    </div>
  );
}
