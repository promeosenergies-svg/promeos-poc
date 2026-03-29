/**
 * Vue portefeuille flex — ranking quick wins par site.
 */
import { useState, useEffect } from 'react';
import { getFlexPortfolio } from '../../services/api';

export default function FlexPortfolioSummary() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFlexPortfolio()
      .then((r) => setData(r))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-pulse h-24 bg-gray-50 rounded-lg" />;
  if (!data || data.total_sites === 0) return null;

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Potentiel flex portefeuille</h3>
        <div className="flex gap-3 text-xs text-gray-500">
          <span>{data.total_sites} sites</span>
          <span>{Math.round(data.total_potential_kw ?? 0)} kW total</span>
          <span>Score moy. {Math.round(data.avg_flex_score ?? 0)}/100</span>
        </div>
      </div>

      <div className="space-y-1.5">
        {(data.rankings || []).slice(0, 5).map((r, i) => (
          <div key={r.site_id} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-gray-400 w-4">{i + 1}.</span>
              <span className="font-medium text-gray-700">{r.site_name}</span>
              <span className="text-gray-400">({r.asset_count} assets)</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-600">{Math.round(r.potential_kw ?? 0)} kW</span>
              <span
                className={`font-medium ${(r.flex_score ?? 0) >= 50 ? 'text-green-700' : 'text-gray-500'}`}
              >
                {Math.round(r.flex_score ?? 0)}/100
              </span>
              <span className="text-gray-400">{r.confidence}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
