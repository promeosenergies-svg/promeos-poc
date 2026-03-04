/**
 * PROMEOS — ExplorerChart v2
 * Composable Recharts wrapper for the Consumption Explorer.
 * Supports 4 display modes and accepts layer components as children.
 * V11.1: added Brush (timeline zoom) + summary row.
 *
 * Props:
 *   data         {object[]}  chart data array (points with x-key + value keys)
 *   xKey         {string}    key for X-axis (default 'hour')
 *   valueKey     {string}    primary value key (default 'kwh' or 'p50')
 *   mode         {string}    agrege|superpose|empile|separe
 *   unit         {string}    kwh|kw|eur
 *   siteIds      {number[]}  for multi-site rendering
 *   siteColors   {object}    { siteId: color }
 *   height       {number}    chart height (default 300)
 *   onSlotClick  {fn}        called with { x, payload } on chart click
 *   showBrush    {boolean}   show Recharts Brush mini-timeline (default true)
 *   summaryData  {object}    { points, series, meters, source, quality } — summary row
 *   children     — layer components (TunnelLayer, ObjectivesLayer, etc.)
 */
import { useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
} from 'recharts';
import { colorForSite } from './helpers';

const UNIT_AXIS_LABELS = {
  kwh: 'kWh',
  kw: 'kW',
  eur: 'EUR',
};

/** French pluralization helper */
function plural(n, singular, plural) {
  return n != null ? `${n}\u00a0${n <= 1 ? singular : plural}` : null;
}

/** Summary row shown below chart */
function SummaryRow({ summaryData }) {
  if (!summaryData) return null;
  const { points, series, meters, source, quality } = summaryData;
  const parts = [
    plural(points, 'point', 'points'),
    plural(series, 'série', 'séries'),
    plural(meters, 'compteur', 'compteurs'),
    source ? `Source\u00a0: ${source}` : null,
    quality != null ? `Qualité\u00a0: ${quality}\u00a0%` : null,
  ].filter(Boolean);

  if (!parts.length) return null;

  return (
    <div
      className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500 select-none"
      aria-label="résumé du graphique"
    >
      {parts.map((p, i) => (
        <span key={i}>{p}</span>
      ))}
    </div>
  );
}

/** Shown when fewer than 2 valid data points are available */
function InsufficientDataPlaceholder({ count = 0 }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mb-3">
        <BarChart3 size={24} className="text-amber-400" />
      </div>
      <p className="text-sm font-medium text-gray-600">
        Données insuffisantes pour tracer le graphique
      </p>
      <p className="text-xs text-gray-400 mt-1">
        {count} point{count !== 1 ? 's' : ''} valide{count !== 1 ? 's' : ''} — 2 minimum requis
      </p>
    </div>
  );
}

function SepareGrid({ siteIds, data, xKey, valueKey, unit, height, children }) {
  const colCount = Math.min(siteIds.length, 3);
  return (
    <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${colCount}, 1fr)` }}>
      {siteIds.map((sid, idx) => {
        const color = colorForSite(sid, idx);
        const siteData = data.map((p) => ({ ...p, kwh: p[`kwh_${sid}`] ?? p.kwh ?? null }));
        return (
          <div key={sid}>
            <ResponsiveContainer width="100%" height={Math.round(height * 0.6)}>
              <ComposedChart data={siteData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={xKey} tick={{ fontSize: 9 }} />
                <YAxis
                  tick={{ fontSize: 9 }}
                  label={{
                    value: UNIT_AXIS_LABELS[unit],
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 9 },
                  }}
                />
                <Tooltip
                  formatter={(v) => (v != null ? `${v} ${UNIT_AXIS_LABELS[unit]}` : 'N/A')}
                />
                <Area
                  type="monotone"
                  dataKey={valueKey}
                  stroke={color}
                  fill={color}
                  fillOpacity={0.2}
                  name={`Site ${idx + 1}`}
                />
                {children}
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-center text-xs text-gray-500 mt-1">Site {idx + 1}</p>
          </div>
        );
      })}
    </div>
  );
}

export default function ExplorerChart({
  data = [],
  xKey = 'hour',
  valueKey = 'kwh',
  mode = 'agrege',
  unit = 'kwh',
  siteIds = [],
  siteColors = {},
  height = 300,
  onSlotClick,
  showBrush = true,
  summaryData,
  children,
}) {
  const yLabel = UNIT_AXIS_LABELS[unit] || 'kWh';

  // Memoize data to avoid unnecessary re-renders when parent re-renders
  const stableData = useMemo(() => data, [JSON.stringify(data)]); // eslint-disable-line react-hooks/exhaustive-deps

  const showBrushBar = showBrush && stableData.length > 20;

  // ── ChartRenderGuard: validate points before rendering ──
  const validPoints = stableData.filter((p) => p[valueKey] != null && !isNaN(p[valueKey]));

  // For superpose/empile, also check per-site keys to avoid blank overlays
  const hasAnySiteData =
    mode === 'superpose' || mode === 'empile'
      ? siteIds.some((sid) =>
          stableData.some((p) => p[`kwh_${sid}`] != null && !isNaN(p[`kwh_${sid}`]))
        )
      : false;

  if (validPoints.length < 2 && !hasAnySiteData) {
    return <InsufficientDataPlaceholder count={validPoints.length} />;
  }

  // Safe Y domain with padding to prevent flat-line chart (when all values equal)
  const ys = validPoints.map((p) => p[valueKey]).filter(Number.isFinite);
  const yMin = ys.length ? Math.min(...ys) : 0;
  const yMax = ys.length ? Math.max(...ys) : 1;
  const pad = yMin === yMax ? Math.max(1, Math.abs(yMin) * 0.05) : 0;
  const yDomain = [Math.max(0, yMin - pad), yMax + pad];

  if (mode === 'separe' && siteIds.length > 1) {
    return (
      <>
        <SepareGrid
          siteIds={siteIds}
          data={stableData}
          xKey={xKey}
          valueKey={valueKey}
          unit={unit}
          height={height}
        >
          {children}
        </SepareGrid>
        <SummaryRow summaryData={summaryData} />
      </>
    );
  }

  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={stableData}
          onClick={onSlotClick ? (d) => onSlotClick(d) : undefined}
          style={onSlotClick ? { cursor: 'pointer' } : {}}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{ value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 11 } }}
            domain={yDomain}
          />
          <Tooltip
            formatter={(v, name) =>
              v != null && !isNaN(v)
                ? [`${Number(v).toLocaleString('fr-FR')} ${yLabel}`, name]
                : ['N/A', name]
            }
          />
          <Legend />

          {/* Core series by mode */}
          {mode === 'agrege' && (
            <Area
              type="monotone"
              dataKey={valueKey}
              stroke="#3b82f6"
              fill="#93c5fd"
              fillOpacity={0.3}
              name="Agrégé"
            />
          )}

          {mode === 'superpose' &&
            siteIds.map((sid, idx) => {
              const color = siteColors[sid] || colorForSite(sid, idx);
              return (
                <Line
                  key={sid}
                  type="monotone"
                  dataKey={`kwh_${sid}`}
                  stroke={color}
                  dot={false}
                  strokeWidth={2}
                  name={`Site ${idx + 1}`}
                />
              );
            })}

          {mode === 'empile' &&
            siteIds.map((sid, idx) => {
              const color = siteColors[sid] || colorForSite(sid, idx);
              return (
                <Area
                  key={sid}
                  type="monotone"
                  dataKey={`kwh_${sid}`}
                  stackId="stack"
                  stroke={color}
                  fill={color}
                  fillOpacity={0.4}
                  name={`Site ${idx + 1}`}
                />
              );
            })}

          {/* Composable layer children */}
          {children}

          {/* Brush — mini-timeline zoom (only when enough data points) */}
          {showBrushBar && (
            <Brush dataKey={xKey} height={24} stroke="#94a3b8" travellerWidth={6} fill="#f8fafc" />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Summary row: points / séries / compteurs / source / qualité */}
      <SummaryRow summaryData={summaryData} />
    </>
  );
}
