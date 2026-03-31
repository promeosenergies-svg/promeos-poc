import { useState, useEffect } from 'react';
import { getSiteIntelligence } from '../services/api';
import Badge from '../ui/Badge';
import { SkeletonCard } from '../ui/Skeleton';
import EmptyState from '../ui/EmptyState';
import { AlertTriangle, Lightbulb, TrendingDown, Brain } from 'lucide-react';

const severityBadge = (sev) => {
  const map = { critical: 'crit', high: 'crit', medium: 'warn', low: 'info' };
  return map[sev] || 'neutral';
};

export default function SiteIntelligencePanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getSiteIntelligence(siteId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading) return <SkeletonCard />;

  if (!data || data.status === 'no_meters') {
    return (
      <EmptyState
        variant="unconfigured"
        title="Analyse en attente"
        text="Ce site n'a pas encore de compteurs. L'intelligence KB sera disponible apres l'import de donnees."
      />
    );
  }

  if (data.status === 'pending_analysis') {
    return (
      <EmptyState
        variant="partial"
        title="Analyse en cours"
        text="Les donnees sont presentes mais l'analyse KB n'a pas encore ete executee."
      />
    );
  }

  const { archetype, anomalies = [], recommendations = [], summary = {} } = data;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-indigo-500" />
          <h3 className="font-semibold text-gray-800 text-sm">Intelligence energetique</h3>
        </div>
        {archetype && (
          <span className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded-full font-medium">
            {archetype.title} — {Math.round((archetype.match_score || 0) * 100)}%
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* KPI row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-amber-50 rounded-lg text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            </div>
            <p className="text-2xl font-bold text-amber-700">{summary.total_anomalies || 0}</p>
            <p className="text-xs text-gray-500">Anomalies</p>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-blue-700">{summary.total_recommendations || 0}</p>
            <p className="text-xs text-gray-500">Recommandations</p>
          </div>
          <div className="p-3 bg-green-50 rounded-lg text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingDown className="w-3.5 h-3.5 text-green-600" />
            </div>
            <p className="text-2xl font-bold text-green-700">
              {summary.potential_savings_eur_year > 0
                ? `${Math.round(summary.potential_savings_eur_year).toLocaleString('fr-FR')} \u20ac`
                : '\u2014'}
            </p>
            <p className="text-xs text-gray-500">Economies/an</p>
          </div>
        </div>

        {/* Top anomalies */}
        {anomalies.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Anomalies prioritaires
            </p>
            <div className="space-y-1.5">
              {anomalies.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  className="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:bg-gray-50"
                >
                  <Badge status={severityBadge(a.severity)}>{a.severity}</Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{a.title}</p>
                  </div>
                  {a.deviation_pct != null && (
                    <span className="text-xs text-gray-400">
                      {a.deviation_pct > 0 ? '+' : ''}
                      {a.deviation_pct}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top recommendations */}
        {recommendations.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Recommandations
            </p>
            <div className="space-y-1.5">
              {recommendations.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  className="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:bg-gray-50"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{r.title}</p>
                    {r.estimated_savings_eur_year > 0 && (
                      <p className="text-xs text-green-600">
                        ~{Math.round(r.estimated_savings_eur_year).toLocaleString('fr-FR')}{' '}
                        \u20ac/an
                      </p>
                    )}
                  </div>
                  {r.ice_score != null && (
                    <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-medium">
                      ICE {r.ice_score.toFixed(2)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
