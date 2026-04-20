/**
 * EnergySignatureCard — Signature énergétique multi-modèle (2P/3P/4P/5P).
 *
 * Affiche : scatter température vs kWh, fit line piecewise, classification
 * (heating/cooling/mixed/flat), R², Tb/Tc, coefficients.
 *
 * Source : GET /api/usages/energy-signature/{siteId}/advanced
 */

import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Thermometer, Snowflake, Flame, TrendingUp, AlertTriangle } from 'lucide-react';
import { Card, CardBody, CardHeader } from '../../ui';
import { getEnergySignatureAdvanced } from '../../services/api/enedis';
import { fmtNum } from '../../utils/format';

const LABEL_CONFIG = {
  heating_dominant: {
    label: 'Chauffage dominant',
    icon: Flame,
    color: 'text-orange-700 bg-orange-100',
  },
  cooling_dominant: {
    label: 'Climatisation dominante',
    icon: Snowflake,
    color: 'text-blue-700 bg-blue-100',
  },
  mixed: {
    label: 'Mixte (chauffage + clim)',
    icon: Thermometer,
    color: 'text-purple-700 bg-purple-100',
  },
  flat: {
    label: 'Plat (peu thermosensible)',
    icon: TrendingUp,
    color: 'text-gray-700 bg-gray-100',
  },
};

const QUALITY_COLORS = {
  excellent: 'text-green-700',
  bon: 'text-green-700',
  faible: 'text-red-700',
};

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      {d.date && <p className="text-gray-500">{d.date}</p>}
      <p className="text-gray-800 font-semibold">{d.temp}°C</p>
      <p className="text-gray-600">{fmtNum(d.kwh, 1)} kWh</p>
    </div>
  );
}

export default function EnergySignatureCard({ siteId, months = 12 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    setError(null);
    getEnergySignatureAdvanced(siteId, months)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch((e) => {
        if (!stale) setError(e?.response?.data?.detail || 'Signature indisponible');
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId, months]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-gray-700">Signature énergétique</h3>
        </CardHeader>
        <CardBody>
          <div className="animate-pulse h-48 bg-gray-100 rounded" />
        </CardBody>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-gray-700">Signature énergétique</h3>
        </CardHeader>
        <CardBody>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle size={16} className="text-gray-400" />
            {error || 'Aucune donnée'}
          </div>
        </CardBody>
      </Card>
    );
  }

  const model = data.model || {};
  const labelConfig = LABEL_CONFIG[model.label] || LABEL_CONFIG.flat;
  const LabelIcon = labelConfig.icon;

  const scatterData = (data.scatter_data || []).map((d) => ({
    temp: d.temp,
    kwh: d.kwh,
    date: d.date,
  }));
  const fitLine = (data.fit_line || []).map((d) => ({
    temp: d.T,
    predicted: d.predicted,
  }));
  const thermo = data.thermosensitivity || {};

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="text-sm font-semibold text-gray-700">Signature énergétique E = f(T°)</h3>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${labelConfig.color}`}
            >
              <LabelIcon size={12} />
              {labelConfig.label}
            </span>
            <span
              className={`text-xs font-mono ${QUALITY_COLORS[model.quality] || 'text-gray-500'}`}
            >
              R² = {fmtNum(model.r_squared, 3)}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {/* Chart */}
        <div className="h-56 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={scatterData} margin={{ top: 5, right: 15, left: 0, bottom: 15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="temp"
                type="number"
                domain={['auto', 'auto']}
                tick={{ fontSize: 10 }}
                label={{
                  value: 'Température (°C)',
                  position: 'insideBottom',
                  offset: -5,
                  fontSize: 11,
                }}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                label={{ value: 'kWh/jour', angle: -90, position: 'insideLeft', fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip />} />
              <Scatter data={scatterData} fill="#93c5fd" fillOpacity={0.6} />
              {fitLine.length > 0 && (
                <Line
                  data={fitLine}
                  dataKey="predicted"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-xs text-gray-500 uppercase">Baseload</div>
            <div className="font-semibold text-gray-800">
              {fmtNum(model.base_kwh_day, 0)}{' '}
              <span className="text-xs text-gray-500">kWh/j</span>
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Pente chauffage</div>
            <div className="font-semibold text-orange-700">
              {fmtNum(model.a_heating_kwh_per_c, 1)}{' '}
              <span className="text-xs text-gray-500">kWh/°C</span>
            </div>
            {model.t_heat_c != null && (
              <div className="text-xs text-gray-400">Tb = {model.t_heat_c}°C</div>
            )}
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Pente clim</div>
            <div className="font-semibold text-blue-700">
              {fmtNum(model.b_cooling_kwh_per_c, 1)}{' '}
              <span className="text-xs text-gray-500">kWh/°C</span>
            </div>
            {model.t_cool_c != null && (
              <div className="text-xs text-gray-400">Tc = {model.t_cool_c}°C</div>
            )}
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Part thermosens.</div>
            <div className="font-semibold text-gray-800">
              {fmtNum(thermo.part_thermo_pct, 0)}%
            </div>
          </div>
        </div>

        <div className="mt-3 text-xs text-gray-500">
          Modèle : <span className="font-mono text-gray-700">{model.type || '—'}</span> ·{' '}
          {data.period_days || 0} jours · source{' '}
          <span className="font-mono">{data.data_source || '—'}</span>
        </div>
      </CardBody>
    </Card>
  );
}
