/**
 * PROMEOS — ReprogCompareCard
 * Affiche la comparaison avant/après reprogrammation HC pour un site.
 * Montre l'impact sur les plages HP/HC et l'estimation financière.
 */
import { ArrowRight, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';
import { Card, CardBody, Badge } from '../ui';
import { fmtKwh, fmtEur } from '../utils/format';

const PERIOD_LABELS = {
  HPH: 'HP Hiver',
  HCH: 'HC Hiver',
  HPB: 'HP Été',
  HCB: 'HC Été',
  HP: 'HP',
  HC: 'HC',
};

const PERIOD_COLORS = {
  HPH: 'text-red-700',
  HCH: 'text-blue-700',
  HPB: 'text-orange-600',
  HCB: 'text-cyan-600',
};

export default function ReprogCompareCard({ reprogData }) {
  if (!reprogData) return null;

  const { prm, old_schedule_name, new_schedule_name, date_effective, is_seasonal, impact } =
    reprogData;

  if (!impact) return null;

  const deltaEur = impact.delta_cost_eur || 0;
  const isGain = deltaEur < 0;
  const DeltaIcon = isGain ? TrendingDown : TrendingUp;
  const deltaColor = isGain ? 'text-green-700' : 'text-red-700';
  const deltaBg = isGain ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200';

  return (
    <Card className={deltaBg}>
      <CardBody className="py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-500" />
            <h4 className="text-sm font-semibold text-gray-800">
              Reprogrammation HC — PRM ...{prm?.slice(-4)}
            </h4>
            {is_seasonal && <Badge variant="warning">Saisonnalisé</Badge>}
          </div>
          {date_effective && (
            <span className="text-xs text-gray-500">Effectif : {date_effective}</span>
          )}
        </div>

        {/* Avant → Après */}
        <div className="flex items-center gap-3 mb-4 text-sm">
          <div className="flex-1 bg-white rounded p-2 border">
            <p className="text-xs text-gray-500 mb-1">Avant</p>
            <p className="font-medium text-gray-700">{old_schedule_name || 'Standard'}</p>
            {impact.old_windows_summary && (
              <p className="text-xs text-gray-400 mt-0.5">{impact.old_windows_summary}</p>
            )}
          </div>
          <ArrowRight size={16} className="text-gray-400 flex-shrink-0" />
          <div className="flex-1 bg-white rounded p-2 border">
            <p className="text-xs text-gray-500 mb-1">Après</p>
            <p className="font-medium text-gray-700">{new_schedule_name || 'Reprog'}</p>
            {impact.new_windows_summary && (
              <p className="text-xs text-gray-400 mt-0.5">{impact.new_windows_summary}</p>
            )}
          </div>
        </div>

        {/* Impact financier */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            {impact.shifted_hours && (
              <p className="text-xs text-gray-600">{impact.shifted_hours}h décalées par jour</p>
            )}
            {impact.kwh_shifted && (
              <p className="text-xs text-gray-600">~{fmtKwh(impact.kwh_shifted)} impactés / an</p>
            )}
          </div>
          <div className="text-right">
            <div className={`flex items-center gap-1 ${deltaColor}`}>
              <DeltaIcon size={16} />
              <span className="text-lg font-bold">
                {isGain ? '-' : '+'}
                {fmtEur(Math.abs(deltaEur))}
              </span>
              <span className="text-xs">/an</span>
            </div>
            <p className={`text-xs ${isGain ? 'text-green-600' : 'text-red-600'}`}>
              {isGain ? 'Économie estimée' : 'Surcoût estimé'}
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
