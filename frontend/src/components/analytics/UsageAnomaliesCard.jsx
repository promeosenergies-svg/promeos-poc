/**
 * UsageAnomaliesCard — Anomalies detectees par usage.
 *
 * Display-only. Donnees de GET /api/analytics/sites/{id}/usage-anomalies.
 * Chaque anomalie = un usage concerne + gain estime + action recommandee.
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, TrendingDown, Zap } from 'lucide-react';
import { getUsageAnomalies } from '../../services/api';

const SEVERITY_STYLE = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: 'text-red-600',
    text: 'text-red-800',
  },
  high: { bg: 'bg-red-50', border: 'border-red-200', icon: 'text-red-500', text: 'text-red-700' },
  medium: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: 'text-amber-500',
    text: 'text-amber-700',
  },
  low: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'text-blue-500',
    text: 'text-blue-700',
  },
};

export default function UsageAnomaliesCard({ siteId, preloadedData }) {
  const [data, setData] = useState(preloadedData || null);
  const [loading, setLoading] = useState(!preloadedData);

  useEffect(() => {
    if (preloadedData) {
      setData(preloadedData);
      setLoading(false);
      return;
    }
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getUsageAnomalies(siteId)
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
  }, [siteId, preloadedData]);

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-400 animate-pulse">
        Analyse des anomalies en cours...
      </div>
    );
  }

  if (!data || !data.anomalies?.length) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" />
          <h3 className="text-base font-semibold text-gray-900">Anomalies par usage</h3>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-700">
            {data.n_anomalies} detectee{data.n_anomalies > 1 ? 's' : ''}
          </span>
        </div>
        {data.total_gain_eur_an > 0 && (
          <div className="flex items-center gap-1 text-sm font-semibold text-green-700">
            <TrendingDown size={14} />
            {Math.round(data.total_gain_eur_an).toLocaleString('fr-FR')} &euro;/an recuperables
          </div>
        )}
      </div>

      {/* Liste des anomalies */}
      <div className="space-y-3">
        {data.anomalies.map((a, i) => {
          const style = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.medium;
          return (
            <div
              key={`${a.usage_code}-${a.anomaly_type}-${i}`}
              className={`rounded-lg border p-3 ${style.bg} ${style.border}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Zap size={12} className={style.icon} />
                    <span className={`text-sm font-medium ${style.text}`}>{a.message}</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">{a.detail}</p>
                  <p className="text-xs text-gray-500 mt-1.5 italic">{a.action}</p>
                </div>
                {a.gain_eur_an > 0 && (
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-bold text-green-700">
                      {Math.round(a.gain_eur_an).toLocaleString('fr-FR')} &euro;/an
                    </div>
                    {a.gain_kwh_an > 0 && (
                      <div className="text-[10px] text-gray-500">
                        {Math.round(a.gain_kwh_an).toLocaleString('fr-FR')} kWh
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
