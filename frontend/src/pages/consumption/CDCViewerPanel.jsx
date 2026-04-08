/**
 * PROMEOS — CDCViewerPanel (EMS Tier 1)
 * Visualisation courbe de charge (CDC) avec classification TURPE.
 * Recharts ComposedChart : Area (kW) + ReferenceLine par PS.
 */
import { useState, useEffect, useMemo } from 'react';
import {
  ComposedChart,
  Area,
  ReferenceLine,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Zap, Loader2, AlertTriangle } from 'lucide-react';
import { getEmsCdc } from '../../services/api/ems';

// Couleurs TURPE par poste tarifaire
const SLOT_COLORS = {
  Pointe: '#ef4444',
  HPH: '#f97316',
  HCH: '#eab308',
  HPE: '#22c55e',
  HCE: '#14b8a6',
  HP: '#f97316',
  HC: '#14b8a6',
  Base: '#9ca3af',
};

const SLOT_ORDER = ['Pointe', 'HPH', 'HCH', 'HPE', 'HCE', 'HP', 'HC', 'Base'];

function SlotLegend({ slots }) {
  return (
    <div className="flex flex-wrap gap-3 text-xs">
      {SLOT_ORDER.filter((s) => slots.has(s)).map((slot) => (
        <span key={slot} className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: SLOT_COLORS[slot] }} />
          {slot}
        </span>
      ))}
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-700">{new Date(point.t).toLocaleString('fr-FR')}</p>
      <p className="text-gray-600 mt-1">
        Puissance : <span className="font-semibold">{point.kw?.toFixed(1) ?? '—'} kW</span>
      </p>
      <p className="mt-0.5">
        Poste :{' '}
        <span className="font-medium" style={{ color: SLOT_COLORS[point.slot] || '#6b7280' }}>
          {point.slot}
        </span>
      </p>
      {point.quality && <p className="text-gray-400 mt-0.5">Qualité : {point.quality}</p>}
    </div>
  );
}

export default function CDCViewerPanel({ meterId, dateFrom, dateTo }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!meterId || !dateFrom || !dateTo) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getEmsCdc(meterId, dateFrom, dateTo)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Erreur chargement CDC');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [meterId, dateFrom, dateTo]);

  // Préparer les données pour Recharts
  const chartData = useMemo(() => {
    if (!data?.points?.length) return [];
    return data.points.map((p) => ({
      ...p,
      ts: new Date(p.t).getTime(),
      fill: SLOT_COLORS[p.slot] || '#9ca3af',
    }));
  }, [data]);

  const usedSlots = useMemo(() => {
    if (!data?.points) return new Set();
    return new Set(data.points.map((p) => p.slot));
  }, [data]);

  // PS reference lines
  const psLines = useMemo(() => {
    if (!data?.ps) return [];
    return Object.entries(data.ps).map(([poste, kva]) => ({
      poste,
      kva,
      color: SLOT_COLORS[poste] || '#6b7280',
    }));
  }, [data]);

  if (!meterId) {
    return (
      <div className="text-center py-8">
        <Zap size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">
          Sélectionnez un compteur pour afficher la courbe de charge.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-gray-500">Chargement CDC...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <AlertTriangle size={24} className="mx-auto text-red-400 mb-2" />
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="text-center py-8">
        <Zap size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">Aucune donnée CDC sur cette période.</p>
        {data?.meta?.source && (
          <p className="text-xs text-gray-400 mt-1">Source : {data.meta.source}</p>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <Zap size={16} className="text-blue-600" />
          Courbe de charge
        </h3>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>FTA : {data?.meta?.fta_code || '—'}</span>
          <span>{data?.meta?.count || 0} points</span>
          <span>Source : {data?.meta?.source || '—'}</span>
        </div>
      </div>

      <SlotLegend slots={usedSlots} />

      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="ts"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(ts) =>
              new Date(ts).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
            }
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            label={{
              value: 'kW',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#9ca3af' },
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="kw"
            stroke="#3b82f6"
            fill="#93c5fd"
            fillOpacity={0.3}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          {/* PS reference lines */}
          {psLines.map(({ poste, kva, color }) => (
            <ReferenceLine
              key={poste}
              y={kva}
              stroke={color}
              strokeDasharray="6 3"
              strokeWidth={1.5}
              label={{
                value: `PS ${poste} ${kva} kVA`,
                position: 'insideTopRight',
                fill: color,
                fontSize: 10,
              }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
