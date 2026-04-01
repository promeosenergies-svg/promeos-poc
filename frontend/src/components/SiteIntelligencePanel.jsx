import { useState, useEffect } from 'react';
import { getSiteIntelligence, createAction } from '../services/api';
import { buildKbRecoActionPayload, buildKbRecoActionDeepLink } from '../models/kbRecoActionModel';
import Badge from '../ui/Badge';
import { SkeletonCard } from '../ui/Skeleton';
import EmptyState from '../ui/EmptyState';
import { AlertTriangle, Lightbulb, TrendingDown, Brain } from 'lucide-react';

const severityBadge = (sev) => {
  const map = { critical: 'crit', high: 'crit', medium: 'warn', low: 'info' };
  return map[sev] || 'neutral';
};

export default function SiteIntelligencePanel({ siteId, site }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [createdActions, setCreatedActions] = useState({});
  const [creatingAction, setCreatingAction] = useState(null);
  const [bulkInProgress, setBulkInProgress] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getSiteIntelligence(siteId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  const handleCreateAction = async (reco) => {
    const status = createdActions[reco.recommendation_code];
    if (status && status !== 'error') return;
    setCreatingAction(reco.recommendation_code);
    try {
      const topSeverity = data?.anomalies?.[0]?.severity || 'medium';
      const payload = buildKbRecoActionPayload({
        orgId: data?.org_id || site?.org_id,
        siteId,
        siteName: data?.site_name || site?.nom || `Site ${siteId}`,
        reco,
        topSeverity,
      });
      const result = await createAction(payload);
      setCreatedActions((prev) => ({
        ...prev,
        [reco.recommendation_code]: result.status || 'created',
      }));
    } catch {
      setCreatedActions((prev) => ({ ...prev, [reco.recommendation_code]: 'error' }));
    } finally {
      setCreatingAction(null);
    }
  };

  const handlePlanAll = async () => {
    if (bulkInProgress) return;
    const pending = recommendations.filter((r) => {
      const st = createdActions[r.recommendation_code];
      return !st || st === 'error';
    });
    if (pending.length === 0) return;
    setBulkInProgress(true);
    for (const reco of pending) {
      await handleCreateAction(reco);
    }
    setBulkInProgress(false);
  };

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

        {/* Top recommendations with CTA */}
        {recommendations.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Recommandations
              </p>
              <div className="flex items-center gap-3">
                {recommendations.length > 1 && (
                  <button
                    onClick={handlePlanAll}
                    disabled={
                      bulkInProgress ||
                      recommendations.every((r) => {
                        const st = createdActions[r.recommendation_code];
                        return st && st !== 'error';
                      })
                    }
                    className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100 disabled:opacity-50"
                  >
                    {bulkInProgress ? 'Planification\u2026' : 'Planifier tout'}
                  </button>
                )}
                <a
                  href={buildKbRecoActionDeepLink(siteId)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Voir les actions &rarr;
                </a>
              </div>
            </div>
            <div className="space-y-1.5">
              {recommendations.slice(0, 5).map((r) => {
                const actionStatus = createdActions[r.recommendation_code];
                const isCreating = creatingAction === r.recommendation_code;

                return (
                  <div
                    key={r.id}
                    className="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:bg-gray-50"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{r.title}</p>
                      {r.estimated_savings_eur_year > 0 && (
                        <p className="text-xs text-green-600">
                          ~{Math.round(r.estimated_savings_eur_year).toLocaleString('fr-FR')}{' '}
                          {'\u20ac'}/an
                        </p>
                      )}
                    </div>
                    {r.ice_score != null && (
                      <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-medium shrink-0">
                        ICE {r.ice_score.toFixed(2)}
                      </span>
                    )}
                    {actionStatus === 'created' || actionStatus === 'existing' ? (
                      <span className="text-xs px-2 py-1 bg-green-50 text-green-700 rounded shrink-0">
                        {'\u2713'} Action
                      </span>
                    ) : actionStatus === 'error' ? (
                      <button
                        onClick={() => handleCreateAction(r)}
                        className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100 shrink-0"
                      >
                        Reessayer
                      </button>
                    ) : (
                      <button
                        onClick={() => handleCreateAction(r)}
                        disabled={isCreating}
                        className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 disabled:opacity-50 shrink-0"
                      >
                        {isCreating ? 'Creation\u2026' : '+ Action'}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
