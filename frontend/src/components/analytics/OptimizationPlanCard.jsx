/**
 * OptimizationPlanCard — Plan d'optimisation par usage avec ROI chiffre (etage 3).
 * Display-only. Donnees de GET /api/analytics/sites/{id}/optimization-plan.
 */

import { useState, useEffect } from 'react';
import { Target, ArrowDownCircle, Clock } from 'lucide-react';
import { getOptimizationPlan } from '../../services/api';

const COMPLEXITY_BADGE = {
  simple: { label: 'Quick win', bg: 'bg-green-100', text: 'text-green-700' },
  moderate: { label: 'Moyen terme', bg: 'bg-blue-100', text: 'text-blue-700' },
  complex: { label: 'Structurant', bg: 'bg-purple-100', text: 'text-purple-700' },
};

export default function OptimizationPlanCard({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getOptimizationPlan(siteId)
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
      <div className="p-6 text-sm text-gray-400 animate-pulse">
        Calcul du plan d'optimisation...
      </div>
    );
  }
  if (!data || !data.actions?.length) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-indigo-600" />
          <h3 className="text-base font-semibold text-gray-900">Plan d'optimisation</h3>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-100 text-indigo-700">
            {data.n_actions} action{data.n_actions > 1 ? 's' : ''}
          </span>
        </div>
        <div className="text-right text-xs">
          <div className="font-semibold text-green-700">
            <ArrowDownCircle size={12} className="inline mr-1" />
            {Math.round(data.total_gain_eur_an).toLocaleString('fr-FR')} &euro;/an
          </div>
          {data.avg_payback_months < 999 && (
            <div className="text-gray-500 flex items-center justify-end gap-1 mt-0.5">
              <Clock size={10} />
              Payback moyen {Math.round(data.avg_payback_months)} mois
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="space-y-2">
        {data.actions.map((a, i) => {
          const badge = COMPLEXITY_BADGE[a.complexity] || COMPLEXITY_BADGE.moderate;
          return (
            <div
              key={`${a.action_code}-${i}`}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.bg} ${badge.text}`}
                  >
                    {badge.label}
                  </span>
                  <span className="text-sm font-medium text-gray-800 truncate">
                    {a.action_title}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{a.action_detail}</p>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-gray-400">
                  <span>Usage : {a.usage_label}</span>
                  {a.anomaly_source && <span>Detecte via : {a.anomaly_source}</span>}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-sm font-bold text-green-700">
                  {Math.round(a.gain_eur_an).toLocaleString('fr-FR')} &euro;/an
                </div>
                {a.investment_eur > 0 && (
                  <div className="text-[10px] text-gray-500">
                    Invest : {Math.round(a.investment_eur).toLocaleString('fr-FR')} &euro;
                  </div>
                )}
                {a.payback_months < 999 && (
                  <div className="text-[10px] text-gray-400">Payback : {a.payback_months} mois</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Total investissement */}
      {data.total_investment_eur > 0 && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-xs">
          <span className="text-gray-500">
            Investissement total : {Math.round(data.total_investment_eur).toLocaleString('fr-FR')}{' '}
            &euro;
          </span>
          <span className="font-medium text-gray-700">
            ROI :{' '}
            {data.total_gain_eur_an > 0
              ? `${Math.round((data.total_investment_eur / data.total_gain_eur_an) * 12)} mois`
              : '—'}
          </span>
        </div>
      )}
    </div>
  );
}
