/**
 * RecommendationsCard — Recommandations auto-générées depuis les KPIs.
 *
 * Affiche la liste triée par ICE score décroissant.
 * Bouton "Regénérer" → POST /api/usages/recommendations/generate/{id}?persist=true
 */

import { useState, useEffect, useCallback } from 'react';
import { Lightbulb, RefreshCw, AlertTriangle } from 'lucide-react';
import { Card, CardBody, CardHeader, FindingCard } from '../../ui';
import { generateRecommendations } from '../../services/api/enedis';

// Map ICE score 0-10 → FindingCard confidence prop 0-1
// L'ICE est un composite (Impact × Confidence × Ease). En affichant l'ICE comme
// confidence dans le badge FindingCard, on perd la granularité I/C/E individuelle
// mais on garde un indicateur de fiabilité globale. Le détail ICE complet reste
// accessible via RecommendationDetail modal.
const iceToConfidence = (ice) =>
  typeof ice === 'number' ? Math.min(1, Math.max(0, ice / 10)) : null;

// Severity CSS classes conservées uniquement pour RecommendationDetail modal
// (wrapper background). La liste utilise FindingCard qui gère son propre rendu.
const DETAIL_SEVERITY_BG = {
  low: 'bg-gray-50',
  medium: 'bg-yellow-50',
  high: 'bg-orange-50',
  critical: 'bg-red-50',
};

function IceBadge({ score }) {
  const color =
    score >= 7.5
      ? 'bg-green-100 text-green-700'
      : score >= 5.5
        ? 'bg-yellow-100 text-yellow-700'
        : 'bg-gray-100 text-gray-700';
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-mono font-semibold px-2 py-0.5 rounded ${color}`}
    >
      ICE {score?.toFixed(1) || '—'}
    </span>
  );
}

function RecommendationDetail({ reco, onClose }) {
  const sev = reco.triggered_by?.severity || 'medium';
  const bg = DETAIL_SEVERITY_BG[sev] || DETAIL_SEVERITY_BG.medium;
  const sevLabel = { low: 'Info', medium: 'Moyenne', high: 'Élevée', critical: 'Critique' }[sev];
  return (
    <div
      className="fixed inset-0 bg-black/30 z-50 flex items-end md:items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-xs font-semibold text-gray-500">
                  Priorité #{reco.priority_rank}
                </span>
                <IceBadge score={reco.ice_score} />
                <span className={`text-xs px-2 py-0.5 rounded-full ${bg}`}>{sevLabel}</span>
              </div>
              <h3 className="text-base font-semibold text-gray-800">{reco.title}</h3>
              <p className="text-xs text-gray-500 mt-0.5 font-mono">{reco.code}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
              aria-label="Fermer"
            >
              ×
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* Anomalie déclencheuse */}
          {reco.triggered_by && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle size={14} className="text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-amber-800">
                    Anomalie détectée : {reco.triggered_by.code}
                  </p>
                  <p className="text-xs text-amber-700 mt-1">{reco.triggered_by.explanation}</p>
                </div>
              </div>
            </div>
          )}

          {/* Description */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Recommandation</div>
            <p className="text-sm text-gray-700">{reco.description}</p>
          </div>

          {/* ICE breakdown */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Scoring ICE</div>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500">Impact</div>
                <div className="text-lg font-bold text-gray-800">{reco.impact_score}/10</div>
              </div>
              <div className="text-center bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500">Confiance</div>
                <div className="text-lg font-bold text-gray-800">{reco.confidence_score}/10</div>
              </div>
              <div className="text-center bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500">Facilité</div>
                <div className="text-lg font-bold text-gray-800">{reco.ease_score}/10</div>
              </div>
            </div>
          </div>

          {/* Savings */}
          {(reco.estimated_savings_eur_year > 0 || reco.estimated_savings_kwh_year > 0) && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="text-xs font-semibold text-green-800 uppercase mb-1">
                Économie estimée
              </div>
              <div className="flex items-baseline gap-4">
                {reco.estimated_savings_eur_year > 0 && (
                  <div>
                    <span className="text-2xl font-bold text-green-700">
                      {reco.estimated_savings_eur_year.toLocaleString('fr-FR')}
                    </span>
                    <span className="text-sm text-green-700 ml-1">€/an</span>
                  </div>
                )}
                {reco.estimated_savings_kwh_year > 0 && (
                  <div className="text-sm text-green-700">
                    {Math.round(reco.estimated_savings_kwh_year).toLocaleString('fr-FR')} kWh/an
                  </div>
                )}
                {reco.estimated_savings_pct > 0 && (
                  <div className="text-sm text-green-700">({reco.estimated_savings_pct}%)</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RecommendationsCard({ siteId }) {
  const [recos, setRecos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedReco, setSelectedReco] = useState(null);

  const fetchRecos = useCallback(
    async (persist = false) => {
      setError(null);
      try {
        const data = await generateRecommendations(siteId, persist);
        setRecos(data.recommendations || []);
      } catch (e) {
        setError(e?.response?.data?.detail || 'Génération impossible');
      }
    },
    [siteId]
  );

  useEffect(() => {
    let stale = false;
    setLoading(true);
    // Premier chargement : non-persistant pour aperçu rapide
    fetchRecos(false).finally(() => {
      if (!stale) setLoading(false);
    });
    return () => {
      stale = true;
    };
  }, [fetchRecos]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchRecos(true); // Persistance en DB lors du refresh manuel
    setRefreshing(false);
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lightbulb size={16} className="text-yellow-500" />
              <h3 className="text-sm font-semibold text-gray-700">
                Recommandations
                {recos.length > 0 && (
                  <span className="ml-2 text-xs text-gray-500 font-normal">({recos.length})</span>
                )}
              </h3>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
              {refreshing ? 'Regénère…' : 'Regénérer'}
            </button>
          </div>
        </CardHeader>
        <CardBody>
          {loading ? (
            <div className="space-y-2">
              <div className="h-16 bg-gray-100 rounded animate-pulse" />
              <div className="h-16 bg-gray-100 rounded animate-pulse" />
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-sm text-gray-500 py-4">
              <AlertTriangle size={16} className="text-gray-400" />
              {error}
            </div>
          ) : recos.length === 0 ? (
            <div className="text-center py-6">
              <Lightbulb size={24} className="mx-auto text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">Aucune recommandation active</p>
              <p className="text-xs text-gray-400 mt-1">
                Les KPIs du site sont dans la norme. Lancez une regénération pour actualiser.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {recos.map((reco) => (
                <FindingCard
                  key={reco.code}
                  compact
                  priority={reco.priority_rank}
                  severity={reco.triggered_by?.severity || 'medium'}
                  category="consumption"
                  title={reco.title}
                  description={reco.description}
                  confidence={iceToConfidence(reco.ice_score)}
                  impact={{
                    eur: reco.estimated_savings_eur_year,
                    kwh: reco.estimated_savings_kwh_year,
                  }}
                  onClick={() => setSelectedReco(reco)}
                />
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {selectedReco && (
        <RecommendationDetail reco={selectedReco} onClose={() => setSelectedReco(null)} />
      )}
    </>
  );
}
