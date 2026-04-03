/**
 * FlexScoreCard — Score de flexibilite par usage du site
 *
 * REGLE : zero calcul metier. Display-only.
 * Toutes les valeurs viennent de GET /api/flex/score/sites/{id}
 */

import React, { useState, useEffect } from 'react';
import { getFlexScore } from '../../services/api';

const SCORE_TIERS = [
  { min: 0.8, badge: 'text-green-700 bg-green-50 border-green-200', bar: 'bg-green-500' },
  { min: 0.6, badge: 'text-blue-700 bg-blue-50 border-blue-200', bar: 'bg-blue-500' },
  { min: 0.4, badge: 'text-amber-700 bg-amber-50 border-amber-200', bar: 'bg-amber-500' },
  { min: 0, badge: 'text-gray-500 bg-gray-50 border-gray-200', bar: 'bg-gray-400' },
];

const scoreTier = (score) => SCORE_TIERS.find((t) => score >= t.min) || SCORE_TIERS[3];

const MECANISME_LABELS = {
  NEBCO: 'NEBCO',
  NEBCO_ANTICIPATION: 'NEBCO Anticip.',
  NEBCO_REPORT: 'NEBCO Report',
  NEBCO_VIA_UPS: 'NEBCO via UPS',
  HP_HC: 'HP/HC',
  DYNAMIQUE: 'Tarif dynamique',
  FLEX_LOCALE: 'Flex locale Enedis',
  RESERVE_COMP: 'Reserve compl.',
  RESERVE_RAPIDE: 'Reserve rapide',
  RESERVE_RAPIDE_PARTIEL: 'Reserve partielle',
  RESERVE_RAPIDE_BATTERIES: 'Reserve batteries',
  AOFD: 'AOFD',
  AFFRR: 'aFRR',
  AFFRR_VARIATEUR: 'aFRR variateur',
  AFFRR_BATTERIES: 'aFRR batteries',
  TEMPO: 'Tempo',
  CAPACITE: 'Capacite',
};

export default function FlexScoreCard({ siteId, onPlanifier }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getFlexScore(siteId)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch(() => {
        if (!stale) setData(null);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  if (loading) {
    return (
      <div className="p-4 text-sm text-gray-400 animate-pulse">Chargement score flexibilite...</div>
    );
  }
  if (!data || data.score_global_site === undefined) return null;

  const scoreGlobal = data.score_global_site;
  const tier = scoreTier(scoreGlobal);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">Score de Flexibilite</h3>
        <div className={`px-3 py-1 rounded-full text-lg font-bold border ${tier.badge}`}>
          {Math.round(scoreGlobal * 100)}/100
        </div>
      </div>

      {/* Flags transversaux */}
      <div className="flex flex-wrap gap-2">
        {data.nebco_eligible_direct && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            NEBCO eligible direct
          </span>
        )}
        {data.signal_prix_negatifs && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Valorisable prix negatifs
          </span>
        )}
        {data.potentiel_heures_solaires && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            Heures solaires 11h-14h
          </span>
        )}
      </div>

      {/* Seuils de signal */}
      {data.seuils_alerte && (
        <p className="text-xs text-gray-500">
          Signaux actifs si prix spot &le; {data.seuils_alerte.prix_negatif_eur_mwh}&nbsp;&euro;/MWh{' '}
          ou &ge; {data.seuils_alerte.prix_positif_eur_mwh}&nbsp;&euro;/MWh &middot; France 2025 :{' '}
          {data.heures_negatives_france_2025}h prix negatifs
        </p>
      )}

      {/* Top usages */}
      {data.top_usages?.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700">
            Usages detectes ({data.n_usages_evalues})
          </div>
          {data.top_usages.map((usage, i) => {
            const usageTier = scoreTier(usage.score);
            return (
              <div key={usage.code} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-4">{i + 1}</span>
                    <span className="text-gray-800">{usage.label}</span>
                    {usage.nogo_nebco && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700">
                        No-go NEBCO
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-mono text-gray-600">
                    {Math.round(usage.score * 100)}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${usageTier.bar}`}
                    style={{ width: `${Math.round(usage.score * 100)}%` }}
                  />
                </div>
                <div className="flex flex-wrap gap-1">
                  {usage.mecanismes.map((m) => (
                    <span
                      key={m}
                      className="inline-flex px-1.5 py-0.5 rounded text-[10px] bg-gray-100 text-gray-600"
                    >
                      {MECANISME_LABELS[m] || m}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Mecanismes accessibles */}
      {data.mecanismes_accessibles?.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-sm font-medium text-gray-700">Mecanismes accessibles</div>
          <div className="flex flex-wrap gap-1.5">
            {data.mecanismes_accessibles.map((m) => (
              <span
                key={m}
                className="inline-flex px-2 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100"
              >
                {MECANISME_LABELS[m] || m}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* CTA Centre d'action — visible si score >= 0.6 et callback fourni */}
      {onPlanifier && scoreGlobal >= 0.6 && data.top_usages?.length > 0 && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <span className="text-xs text-gray-500">
            Potentiel identifie sur {data.n_usages_evalues} usages
          </span>
          <button
            className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
            onClick={() => onPlanifier(data.top_usages[0]?.code || 'FLEX_GENERAL')}
          >
            Optimiser la flexibilite
          </button>
        </div>
      )}
    </div>
  );
}
