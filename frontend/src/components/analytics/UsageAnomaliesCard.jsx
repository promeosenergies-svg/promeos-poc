/**
 * UsageAnomaliesCard — Anomalies detectees par usage.
 *
 * Display-only. Donnees de GET /api/analytics/sites/{id}/usage-anomalies.
 * Chaque anomalie = un usage concerne + gain estime + action recommandee.
 *
 * Sprint CX UX migration (3/66) : rendu des anomalies unifié via <FindingCard>.
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, TrendingDown } from 'lucide-react';
import { FindingCard } from '../../ui';
import { getUsageAnomalies } from '../../services/api';

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

      {/* Liste des anomalies via FindingCard unifié */}
      <div className="space-y-3">
        {data.anomalies.map((a, i) => (
          <FindingCard
            key={`${a.usage_code}-${a.anomaly_type}-${i}`}
            compact
            severity={a.severity || 'medium'}
            category="consumption"
            title={a.message}
            description={a.action ? `${a.detail} — ${a.action}` : a.detail}
            impact={{
              eur: a.gain_eur_an,
              kwh: a.gain_kwh_an,
            }}
          />
        ))}
      </div>
    </div>
  );
}
