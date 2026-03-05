/**
 * PROMEOS — HPHCPanel (extracted from ConsumptionExplorerPage)
 * HP/HC breakdown: ratio bar, KPI grid, opportunity card, 7x24 heatmap, schedule windows.
 */
import { useState, useCallback, useEffect } from 'react';
import { Clock } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState, TrustBadge } from '../../ui';
import { SkeletonCard } from '../../ui';
import { track } from '../../services/tracker';
import { getHPHCBreakdownV2, getActiveTOUSchedule } from '../../services/api';
import HeatmapChart from './HeatmapChart';
import { CONFIDENCE_BADGE } from './constants';

export default function HPHCPanel({ siteId, days, toast, initialBreakdown }) {
  const [breakdown, setBreakdown] = useState(initialBreakdown || null);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);

  // Re-sync when motor provides updated breakdown (e.g., days changed)
  useEffect(() => {
    if (initialBreakdown) {
      setBreakdown(initialBreakdown);
    }
  }, [initialBreakdown]);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      // Only fetch breakdown if not provided by motor; always fetch schedule
      const [bd, s] = await Promise.all([
        initialBreakdown ? Promise.resolve(initialBreakdown) : getHPHCBreakdownV2(siteId, days),
        getActiveTOUSchedule(siteId),
      ]);
      setBreakdown(bd);
      setSchedule(s);
      track('hphc_loaded', { site_id: siteId, days });
    } catch (e) {
      toast?.('Erreur chargement HP/HC', 'error');
    } finally {
      setLoading(false);
    }
  }, [siteId, days, initialBreakdown, toast]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <SkeletonCard rows={4} />;

  const conf = CONFIDENCE_BADGE[breakdown?.confidence] || CONFIDENCE_BADGE.low;
  const hpPct = breakdown ? Math.round(breakdown.hp_ratio * 100) : 0;
  const hcPct = 100 - hpPct;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Ratio HP / HC</h3>
          {breakdown && (
            <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
          )}
        </div>
      </div>

      {breakdown && breakdown.total_kwh > 0 ? (
        <>
          {/* HP/HC bar */}
          <Card>
            <CardBody>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-600">
                  Calendrier : {breakdown.calendar_name || schedule?.name || 'Par defaut'}
                </span>
                {schedule?.source && <Badge variant="info">{schedule.source}</Badge>}
              </div>
              <div className="w-full h-8 rounded-full overflow-hidden flex">
                <div
                  className="bg-red-400 flex items-center justify-center"
                  style={{ width: `${hpPct}%` }}
                >
                  <span className="text-xs font-bold text-white">{hpPct}% HP</span>
                </div>
                <div
                  className="bg-blue-400 flex items-center justify-center"
                  style={{ width: `${hcPct}%` }}
                >
                  <span className="text-xs font-bold text-white">{hcPct}% HC</span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* KPI grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">HP</p>
                <p className="text-lg font-bold text-red-600">
                  {breakdown.hp_kwh.toLocaleString('fr-FR')} kWh
                </p>
                <p className="text-xs text-gray-400">
                  {breakdown.hp_cost_eur.toLocaleString('fr-FR')} EUR
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">HC</p>
                <p className="text-lg font-bold text-blue-600">
                  {breakdown.hc_kwh.toLocaleString('fr-FR')} kWh
                </p>
                <p className="text-xs text-gray-400">
                  {breakdown.hc_cost_eur.toLocaleString('fr-FR')} EUR
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Total</p>
                <p className="text-lg font-bold text-gray-800">
                  {breakdown.total_kwh.toLocaleString('fr-FR')} kWh
                </p>
                <p className="text-xs text-gray-400">
                  {breakdown.total_cost_eur.toLocaleString('fr-FR')} EUR
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Prix HP/HC</p>
                <p className="text-sm font-semibold text-gray-700">
                  {breakdown.opportunity?.price_hp || '—'} /{' '}
                  {breakdown.opportunity?.price_hc || '—'} EUR/kWh
                </p>
              </CardBody>
            </Card>
          </div>

          {/* Opportunity card */}
          {breakdown.opportunity?.savings_eur > 0 && (
            <Card className="bg-green-50 border-green-200">
              <CardBody className="py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-green-700">
                      Opportunité de report HP → HC
                    </p>
                    <p className="text-sm text-green-800 mt-0.5">
                      ~{breakdown.opportunity.shiftable_kwh.toLocaleString('fr-FR')} kWh reportables
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-700">
                      {breakdown.opportunity.savings_eur} EUR
                    </p>
                    <p className="text-xs text-green-600">économies potentielles</p>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Heatmap 7x24 */}
          {breakdown.heatmap?.length > 0 && (
            <Card>
              <CardBody>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  Carte thermique HP/HC (7j x 24h)
                </h4>
                <HeatmapChart data={breakdown.heatmap} />
              </CardBody>
            </Card>
          )}

          {/* Schedule windows */}
          {schedule?.windows?.length > 0 && (
            <Card>
              <CardBody>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Plages horaires</h4>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-1.5">Jours</th>
                      <th className="text-left px-3 py-1.5">Debut</th>
                      <th className="text-left px-3 py-1.5">Fin</th>
                      <th className="text-left px-3 py-1.5">Periode</th>
                      <th className="text-right px-3 py-1.5">Prix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.windows.map((w, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-3 py-1.5">{(w.day_types || []).join(', ')}</td>
                        <td className="px-3 py-1.5">{w.start}</td>
                        <td className="px-3 py-1.5">{w.end}</td>
                        <td className="px-3 py-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${w.period === 'HP' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}
                          >
                            {w.period}
                          </span>
                        </td>
                        <td className="px-3 py-1.5 text-right">
                          {w.price_eur_kwh ? `${w.price_eur_kwh} EUR` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>
          )}
        </>
      ) : (
        <EmptyState
          icon={Clock}
          title="Aucune donnée HP/HC"
          text="Importez des relevés électricité pour voir la répartition HP/HC."
        />
      )}
    </div>
  );
}
