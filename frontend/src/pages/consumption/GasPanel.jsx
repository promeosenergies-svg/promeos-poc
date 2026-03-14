/**
 * PROMEOS — GasPanel (extracted from ConsumptionExplorerPage)
 * Gas consumption summary: KPI cards, base/heating decomposition,
 * DJU scatter, raw vs normalized chart, alerts.
 */
import { useState, useCallback, useEffect } from 'react';
import { Flame, AlertTriangle } from 'lucide-react';
import {
  ComposedChart,
  Bar,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardBody, Badge, Button, TrustBadge } from '../../ui';
import { SkeletonCard } from '../../ui';
import { track } from '../../services/tracker';
import { getGasSummary, getGasWeatherNormalized } from '../../services/api';
import { fmtKwh } from '../../utils/format';
import { CONFIDENCE_BADGE } from './constants';

const SEVERITY_STYLE = {
  high: 'bg-red-50 border-red-200 text-red-700',
  medium: 'bg-amber-50 border-amber-200 text-amber-700',
  low: 'bg-gray-50 border-gray-200 text-gray-700',
};

export default function GasPanel({
  siteId,
  days,
  onGenerateDemo,
  toast,
  initialGas,
  initialWeather,
}) {
  const [gas, setGas] = useState(initialGas || null);
  const [weather, setWeather] = useState(initialWeather || null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [g, w] = await Promise.all([
        getGasSummary(siteId, days),
        getGasWeatherNormalized(siteId, days).catch(() => null),
      ]);
      setGas(g);
      setWeather(w);
      track('gas_loaded', { site_id: siteId, days });
    } catch (e) {
      toast?.('Erreur chargement gaz', 'error');
    } finally {
      setLoading(false);
    }
  }, [siteId, days, toast]);

  // Skip initial fetch if motor already provided data
  useEffect(() => {
    if (!initialGas) load();
  }, [load, initialGas]);

  if (loading) return <SkeletonCard rows={4} />;
  if (!gas || gas.readings_count === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-orange-50 flex items-center justify-center mb-4">
          <Flame size={28} className="text-orange-400" />
        </div>
        <h3 className="text-base font-semibold text-gray-700 mb-1">Aucun compteur gaz</h3>
        <p className="text-sm text-gray-500 max-w-xs mb-4">
          Ajoutez un compteur gaz et importez des relevés pour voir le résumé.
        </p>
        {onGenerateDemo && (
          <Button size="sm" variant="outline" onClick={onGenerateDemo}>
            <Flame size={12} className="mr-1.5 text-orange-500" />
            Générer conso démo Gaz
          </Button>
        )}
      </div>
    );
  }

  const conf = CONFIDENCE_BADGE[gas.confidence] || CONFIDENCE_BADGE.low;
  const model = weather?.model;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Consommation Gaz</h3>
          <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-xl font-bold text-gray-800">{fmtKwh(gas.total_kwh)} PCS</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Moy. journaliere</p>
            <p className="text-xl font-bold text-gray-800">{fmtKwh(gas.avg_daily_kwh)} PCS</p>
          </CardBody>
        </Card>
        {model && (
          <>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Base (talon)</p>
                <p className="text-xl font-bold text-amber-600">{model.base_kwh_day} kWh/j</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Sensibilite R²</p>
                <p
                  className={`text-xl font-bold ${model.r_squared > 0.7 ? 'text-green-600' : model.r_squared > 0.4 ? 'text-amber-600' : 'text-gray-600'}`}
                >
                  {model.r_squared}
                </p>
              </CardBody>
            </Card>
          </>
        )}
      </div>

      {/* Decomposition bar */}
      {weather?.decomposition && (
        <Card>
          <CardBody className="py-3">
            <p className="text-xs font-semibold text-gray-600 mb-2">
              Decomposition base / chauffage
            </p>
            <div className="w-full h-6 rounded-full overflow-hidden flex">
              <div
                className="bg-amber-400 flex items-center justify-center"
                style={{ width: `${weather.decomposition.base_pct}%` }}
              >
                <span className="text-[10px] font-bold text-white">
                  {weather.decomposition.base_pct}% Base
                </span>
              </div>
              <div
                className="bg-orange-500 flex items-center justify-center"
                style={{ width: `${weather.decomposition.heating_pct}%` }}
              >
                <span className="text-[10px] font-bold text-white">
                  {weather.decomposition.heating_pct}% Chauffage
                </span>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* DJU scatter chart */}
      {weather?.dju_data?.length > 0 && (
        <Card>
          <CardBody>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Sensibilite climatique (DJU vs Conso)
            </h4>
            <ResponsiveContainer width="100%" height={250}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="dju"
                  name="DJU"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'DJU',
                    position: 'insideBottom',
                    offset: -5,
                    style: { fontSize: 11 },
                  }}
                />
                <YAxis
                  dataKey="kwh"
                  name="kWh"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'kWh/j',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 11 },
                  }}
                />
                <Tooltip formatter={(v, name) => [`${v}`, name === 'dju' ? 'DJU' : 'kWh/j']} />
                <Scatter data={weather.dju_data} fill="#f59e0b" name="Conso journaliere" />
              </ScatterChart>
            </ResponsiveContainer>
            {model && (
              <p className="text-xs text-gray-500 mt-1 text-center">
                Modele : kWh = {model.slope} × DJU + {model.intercept} (R² = {model.r_squared})
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Raw + normalized chart */}
      {weather?.dju_data?.length > 0 && (
        <Card>
          <CardBody>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Conso brute vs corrigee meteo
            </h4>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={weather.dju_data.slice(-60)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 9 }}
                  angle={-45}
                  textAnchor="end"
                  height={50}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'kWh',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 11 },
                  }}
                />
                <Tooltip />
                <Bar dataKey="kwh" fill="#f59e0b" name="Brut (kWh)" opacity={0.7} />
                <Line
                  dataKey="normalized_kwh"
                  stroke="#3b82f6"
                  name="Corrige meteo"
                  dot={false}
                  strokeWidth={2}
                />
                <Legend />
              </ComposedChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Alerts */}
      {weather?.alerts?.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-700">Alertes gaz</h4>
          {weather.alerts.map((alert, i) => (
            <Card
              key={i}
              className={`border ${SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.low}`}
            >
              <CardBody className="py-2.5 flex items-center gap-3">
                <AlertTriangle size={16} className="shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-semibold">{alert.type.replace(/_/g, ' ')}</p>
                  <p className="text-xs mt-0.5">{alert.message}</p>
                </div>
                <Badge status={alert.severity === 'high' ? 'crit' : 'warn'}>{alert.severity}</Badge>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
