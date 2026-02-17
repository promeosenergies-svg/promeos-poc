/**
 * PROMEOS — ExplorerChart
 * Composable Recharts wrapper for the Consumption Explorer.
 * Supports 4 display modes and accepts layer components as children.
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
 *   children     — layer components (TunnelLayer, ObjectivesLayer, etc.)
 */
import {
  ComposedChart,
  Area, Bar, Line, ReferenceLine,
  XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { UNIT_LABELS } from './types';
import { colorForSite } from './helpers';

const UNIT_AXIS_LABELS = {
  kwh: 'kWh',
  kw: 'kW',
  eur: 'EUR',
};

function SepareGrid({ siteIds, data, xKey, valueKey, unit, height, children }) {
  const colCount = Math.min(siteIds.length, 3);
  return (
    <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${colCount}, 1fr)` }}>
      {siteIds.map((sid, idx) => {
        const color = colorForSite(sid, idx);
        const siteData = data.map(p => ({ ...p, kwh: p[`kwh_${sid}`] ?? p.kwh ?? null }));
        return (
          <div key={sid}>
            <ResponsiveContainer width="100%" height={Math.round(height * 0.6)}>
              <ComposedChart data={siteData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={xKey} tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 9 }} label={{ value: UNIT_AXIS_LABELS[unit], angle: -90, position: 'insideLeft', style: { fontSize: 9 } }} />
                <Tooltip formatter={(v) => v != null ? `${v} ${UNIT_AXIS_LABELS[unit]}` : 'N/A'} />
                <Area type="monotone" dataKey={valueKey} stroke={color} fill={color} fillOpacity={0.2} name={`Site ${idx + 1}`} />
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
  children,
}) {
  const yLabel = UNIT_AXIS_LABELS[unit] || 'kWh';

  if (mode === 'separe' && siteIds.length > 1) {
    return (
      <SepareGrid
        siteIds={siteIds}
        data={data}
        xKey={xKey}
        valueKey={valueKey}
        unit={unit}
        height={height}
        children={children}
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} onClick={onSlotClick ? (d) => onSlotClick(d) : undefined} style={onSlotClick ? { cursor: 'pointer' } : {}}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis
          tick={{ fontSize: 11 }}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 11 } }}
        />
        <Tooltip formatter={(v, name) => v != null ? [`${v} ${yLabel}`, name] : ['N/A', name]} />
        <Legend />

        {/* Core series by mode */}
        {mode === 'agrege' && (
          <Area
            type="monotone"
            dataKey={valueKey}
            stroke="#3b82f6"
            fill="#93c5fd"
            fillOpacity={0.3}
            name="Agrege"
          />
        )}

        {mode === 'superpose' && siteIds.map((sid, idx) => {
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

        {mode === 'empile' && siteIds.map((sid, idx) => {
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
      </ComposedChart>
    </ResponsiveContainer>
  );
}
