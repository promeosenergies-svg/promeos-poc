/**
 * PROMEOS — WeekdayOverlayChart (Sprint P3.1).
 *
 * Affiche les 7 courbes moyennes par jour de semaine (Lun → Dim) sur
 * un axe X horaire (0h → 23h). Données fournies par
 * `/api/energy/loadcurve.weekday_overlay` (extension P3.1).
 *
 * Doctrine zéro calcul métier frontend :
 * - Aucun recalcul des moyennes ; backend fournit `avg_kwh` / `avg_kw`
 *   par (day_of_week, hour).
 * - Mapping affichage uniquement.
 *
 * Props :
 * - curves         : list [{ day_of_week, label, points: [{ hour, avg_kwh,
 *                            avg_kw, n_points, quality_status }],
 *                            provenance }] (cf. EnergyWeekdayCurve)
 * - display        : 'kwh' | 'kw' (sélection valeur YAxis)
 */
import React, { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from 'recharts';

const WEEKDAY_COLORS = {
  Lundi: '#2563eb',
  Mardi: '#0891b2',
  Mercredi: '#16a34a',
  Jeudi: '#ca8a04',
  Vendredi: '#dc2626',
  Samedi: '#9333ea',
  Dimanche: '#db2777',
};

function fmtNumber(v, decimals = 1) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

function ChartTooltip({ active, payload, label, display }) {
  if (!active || !payload || payload.length === 0) return null;
  const unit = display === 'kw' ? 'kW' : 'kWh';
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2 text-xs shadow-lg">
      <p className="font-semibold text-gray-800 mb-1">{label}h</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="flex items-center gap-1.5 text-gray-700">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ background: entry.color }}
            aria-hidden="true"
          />
          {entry.dataKey} :{' '}
          <span className="font-mono">
            {fmtNumber(entry.value)} {unit}
          </span>
        </p>
      ))}
    </div>
  );
}

export default function WeekdayOverlayChart({
  curves,
  display = 'kwh',
  className = '',
  testId = 'weekday-overlay-chart',
}) {
  // Construction de la data Recharts : un point par heure, avec une
  // colonne par jour de semaine. Pas de calcul métier — pur remapping.
  const chartData = useMemo(() => {
    if (!Array.isArray(curves) || curves.length === 0) return [];
    const rows = Array.from({ length: 24 }, (_, hour) => ({ hour }));
    for (const curve of curves) {
      const valueKey = display === 'kw' ? 'avg_kw' : 'avg_kwh';
      for (const point of curve.points || []) {
        if (point.hour >= 0 && point.hour <= 23) {
          rows[point.hour][curve.label] = point[valueKey];
        }
      }
    }
    return rows;
  }, [curves, display]);

  if (!Array.isArray(curves) || curves.length === 0) {
    return null;
  }

  // Provenance commune : la première courbe représente le calcul backend
  const commonProvenance = curves[0]?.provenance;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">Profil moyen par jour</h3>
        <p className="text-[11px] text-gray-500 italic">Courbe moyenne du lundi au dimanche</p>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="hour"
            tick={{ fontSize: 11 }}
            label={{
              value: 'Heure',
              position: 'insideBottom',
              offset: -2,
              style: { fontSize: 10, fill: '#9ca3af' },
            }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{
              value: display === 'kw' ? 'kW moyen' : 'kWh moyen',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 10, fill: '#9ca3af' },
            }}
          />
          <RTooltip content={<ChartTooltip display={display} />} />
          <Legend wrapperStyle={{ fontSize: 10 }} iconSize={8} iconType="line" />
          {curves.map((curve) => (
            <Line
              key={curve.label}
              type="monotone"
              dataKey={curve.label}
              stroke={WEEKDAY_COLORS[curve.label] || '#6b7280'}
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {commonProvenance?.service && (
        <p
          className="text-[9px] text-gray-400 font-mono italic mt-2"
          data-testid="weekday-overlay-provenance"
          aria-label={`Provenance : ${commonProvenance.service}`}
        >
          Source : {commonProvenance.service}
        </p>
      )}
    </div>
  );
}
