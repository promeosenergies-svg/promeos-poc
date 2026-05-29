/**
 * PROMEOS — LoadCurveChart (Sprint P1.S3a UI Courbe de charge).
 *
 * Chart courbe de charge consommant la série issue de
 * `/api/energy/loadcurve`. Affichage pur :
 * - Mapping `series[].kwh` ou `series[].kw_avg` selon `display`.
 * - Aucun calcul métier (pas d'agrégation, pas de quartile, pas de
 *   normalisation).
 * - Downsampling visuel uniquement si > MAX_POINTS — warning explicite,
 *   les valeurs métier ne sont jamais modifiées (on saute des points
 *   pour la lisibilité, on n'agrège pas).
 *
 * Props :
 * - series        : list de points { timestamp, kwh, kw_avg, quality_status }
 * - granularity   : '15min' | '30min' | 'hour' | 'day' | 'month' | 'year'
 * - display       : 'kwh' | 'kw'
 * - compare       : 'none' | 'n-1' | 'baseline'
 * - seriesCompare : list série compare (idem format)
 * - loading       : bool
 * - emptyState    : string
 * - warnings      : list de strings backend
 */
import { useMemo } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import { Activity, AlertTriangle } from 'lucide-react';
import { EmptyState, SkeletonCard } from '../index';

const MAX_POINTS = 1000;

/** Mapping pur série API → format Recharts. */
function buildChartData(series, seriesCompare, display) {
  if (!Array.isArray(series) || series.length === 0) return [];
  const field = display === 'kw' ? 'kw_avg' : 'kwh';
  const compareByTs = {};
  if (Array.isArray(seriesCompare)) {
    for (const c of seriesCompare) {
      compareByTs[c.timestamp] = c[field];
    }
  }
  return series.map((p) => ({
    timestamp: p.timestamp,
    value: p[field] ?? null,
    compare: compareByTs[p.timestamp] ?? null,
    quality_status: p.quality_status || 'measured',
  }));
}

/** Downsampling visuel pur : conserve 1 point sur N pour rester ≤ MAX_POINTS.
 *  Note : sampling cosmétique uniquement, les valeurs ne sont pas modifiées. */
function visualDownsample(data, max = MAX_POINTS) {
  if (!Array.isArray(data) || data.length <= max) return data;
  const step = Math.ceil(data.length / max);
  return data.filter((_, i) => i % step === 0);
}

const TICK_FMT = {
  '15min': (ts) =>
    new Date(ts).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }),
  '30min': (ts) =>
    new Date(ts).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }),
  hour: (ts) =>
    new Date(ts).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit' }),
  day: (ts) => new Date(ts).toLocaleString('fr-FR', { day: '2-digit', month: 'short' }),
  month: (ts) => new Date(ts).toLocaleString('fr-FR', { month: 'short', year: 'numeric' }),
  year: (ts) => new Date(ts).toLocaleString('fr-FR', { year: 'numeric' }),
};

const UNIT_LABEL = { kwh: 'kWh', kw: 'kW' };

function formatTooltipValue(v, unit) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} ${unit}`;
}

function ChartTooltip({ active, payload, label, granularity, display, compare }) {
  if (!active || !Array.isArray(payload) || payload.length === 0) return null;
  const point = payload[0]?.payload || {};
  const tsFmt = TICK_FMT[granularity] || TICK_FMT.hour;
  const unitLabel = UNIT_LABEL[display] || 'kWh';
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2.5 shadow-md text-xs space-y-1">
      <p className="font-semibold text-gray-800">{tsFmt(label)}</p>
      <p className="text-gray-700">
        <span className="inline-block w-2 h-2 bg-blue-600 rounded mr-1.5" aria-hidden="true" />
        Période : {formatTooltipValue(point.value, unitLabel)}
      </p>
      {compare !== 'none' && point.compare != null && (
        <p className="text-gray-700">
          <span className="inline-block w-2 h-2 bg-gray-400 rounded mr-1.5" aria-hidden="true" />
          Comparaison : {formatTooltipValue(point.compare, unitLabel)}
        </p>
      )}
      <p className="text-[10px] text-gray-400 pt-1">Qualité : {point.quality_status}</p>
    </div>
  );
}

export default function LoadCurveChart({
  series = [],
  seriesCompare = [],
  granularity = 'hour',
  display = 'kwh',
  compare = 'none',
  loading = false,
  emptyState,
  warnings = [],
  className = '',
}) {
  const rawData = useMemo(
    () => buildChartData(series, seriesCompare, display),
    [series, seriesCompare, display]
  );
  const data = useMemo(() => visualDownsample(rawData), [rawData]);
  const sampled = data.length < rawData.length;
  const tickFmt = TICK_FMT[granularity] || TICK_FMT.hour;
  const unitLabel = UNIT_LABEL[display] || 'kWh';

  if (loading) {
    return (
      <div className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}>
        <SkeletonCard />
      </div>
    );
  }

  if (!rawData.length) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="loadcurve-empty"
      >
        <EmptyState
          icon={Activity}
          title={emptyState || 'Aucune donnée sur la période sélectionnée'}
          text="Élargir la période ou vérifier la connexion compteur."
        />
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 space-y-2 ${className}`}
      data-testid="loadcurve-chart"
    >
      {Array.isArray(warnings) && warnings.length > 0 && (
        <div
          className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-2"
          role="status"
        >
          <AlertTriangle size={12} className="shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-0.5">
            {warnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
            {sampled && (
              <p>
                Affichage dégradé visuel : 1 point sur {Math.ceil(rawData.length / data.length)} (
                {rawData.length} → {data.length}). Les valeurs ne sont pas agrégées.
              </p>
            )}
          </div>
        </div>
      )}
      {!warnings.length && sampled && (
        <p
          className="text-xs text-gray-500 italic"
          role="status"
          data-testid="loadcurve-downsample-notice"
        >
          Affichage dégradé visuel (1 point sur {Math.ceil(rawData.length / data.length)}). Les
          valeurs métier ne sont pas modifiées.
        </p>
      )}
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={tickFmt}
            tick={{ fontSize: 10 }}
            stroke="#9ca3af"
            minTickGap={32}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            stroke="#9ca3af"
            unit={` ${unitLabel}`}
            tickFormatter={(v) => Number(v).toLocaleString('fr-FR')}
          />
          <RTooltip
            content={<ChartTooltip granularity={granularity} display={display} compare={compare} />}
          />
          <Legend
            verticalAlign="top"
            height={24}
            iconSize={8}
            wrapperStyle={{ fontSize: 11, color: '#6b7280' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            name={`Période (${unitLabel})`}
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          {compare !== 'none' && (
            <Line
              type="monotone"
              dataKey="compare"
              name={`Comparaison (${unitLabel})`}
              stroke="#9ca3af"
              strokeDasharray="4 3"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export { MAX_POINTS, buildChartData, visualDownsample };
