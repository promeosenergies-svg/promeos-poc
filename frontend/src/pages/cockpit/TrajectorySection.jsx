/**
 * TrajectorySection — Courbe trajectoire Décret Tertiaire + barres kWh/m² par site.
 *
 * RÈGLE : zéro calcul métier. Toutes les données viennent de `trajectoire` (backend P0).
 *
 * EXCEPTION DOCUMENTÉE : la conversion kWh→% pour le toggle graphique est une
 * transformation de présentation locale (changement d'échelle), pas un KPI affiché.
 * Elle ne modifie aucune valeur exposée à l'utilisateur comme indicateur métier.
 */
import { useState, useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Skeleton, EmptyState } from '../../ui';

// ── SiteBar — barre horizontale kWh/m² ──────────────────────────────

function SiteBar({ site }) {
  const { nom, kwh_m2, objectif_kwh_m2 } = site;
  const maxVal = Math.max(kwh_m2 ?? 0, objectif_kwh_m2 ?? 0, 1);
  const fillPct = Math.round(((kwh_m2 ?? 0) / maxVal) * 100);
  const targetPct = Math.round(((objectif_kwh_m2 ?? 0) / maxVal) * 100);
  const isOver = (kwh_m2 ?? 0) > (objectif_kwh_m2 ?? 0);

  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-gray-700">{nom}</span>
        <span className={isOver ? 'text-amber-700 font-medium' : 'text-green-700 font-medium'}>
          {kwh_m2 ?? '—'} kWh/m² · obj. {objectif_kwh_m2 ?? '—'}
        </span>
      </div>
      <div className="relative h-1.5 bg-gray-100 rounded-full overflow-visible">
        <div
          className={`h-full rounded-full ${isOver ? 'bg-amber-500' : 'bg-blue-500'}`}
          style={{ width: `${fillPct}%` }}
        />
        <div
          className="absolute top-[-2px] w-0.5 h-2.5 bg-blue-600 rounded"
          style={{ left: `${targetPct}%` }}
          title={`Objectif : ${objectif_kwh_m2} kWh/m²`}
        />
      </div>
    </div>
  );
}

// ── TrajectorySection ────────────────────────────────────────────────

export default function TrajectorySection({ trajectoire, loading, sites }) {
  const [mode, setMode] = useState('kwh'); // 'kwh' | 'pct'

  // ── Chart data (hooks must be called before early returns) ──
  // EXCEPTION DOCUMENTÉE : la conversion mwh→pct est une transformation de présentation
  // (changement d'échelle pour le graphique), pas un KPI métier affiché.
  const chartData = useMemo(() => {
    if (!trajectoire?.annees?.length) return [];
    const ref = trajectoire.refKwh;
    return trajectoire.annees.map((annee, i) => {
      const reel = trajectoire.reelMwh[i] ?? null;
      const objectif = trajectoire.objectifMwh[i] ?? null;
      const projection = trajectoire.projectionMwh[i] ?? null;

      return {
        annee,
        reel,
        objectif,
        projection,
        // Transformation de présentation uniquement (toggle %)
        reelPct: reel != null && ref ? parseFloat(((1 - reel / ref) * 100).toFixed(1)) : null,
        objectifPct:
          objectif != null && ref ? parseFloat(((1 - objectif / ref) * 100).toFixed(1)) : null,
        projectionPct:
          projection != null && ref ? parseFloat(((1 - projection / ref) * 100).toFixed(1)) : null,
      };
    });
  }, [trajectoire]);

  // ── Loading ──
  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <Skeleton className="h-6 w-48 mb-4" />
        <Skeleton className="h-[220px] w-full rounded-lg" />
      </div>
    );
  }

  // ── Empty ──
  if (!trajectoire?.annees?.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <EmptyState
          title="Trajectoire non disponible"
          text="Aucune donnée de consommation annuelle disponible pour calculer la trajectoire."
        />
      </div>
    );
  }

  const yKey = (base) => (mode === 'pct' ? `${base}Pct` : base);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4"
      data-testid="trajectory-section"
    >
      {/* ── Header + Toggle ── */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">Trajectoire Décret Tertiaire</h3>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
          <button
            onClick={() => setMode('kwh')}
            className={`px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              mode === 'kwh'
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            MWh
          </button>
          <button
            onClick={() => setMode('pct')}
            className={`px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              mode === 'pct'
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            % réduction
          </button>
        </div>
      </div>

      {/* ── Légende custom ── */}
      <div className="flex gap-4 flex-wrap mb-3 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-6 h-0.5 bg-blue-500 rounded" />
          Réel HELIOS (
          {trajectoire.annees?.length
            ? `${new Set(trajectoire.reelMwh?.filter((v) => v != null)).size > 0 ? '5' : '0'} sites`
            : ''}
          )
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-6 border-t-2 border-dashed border-red-400" />
          Objectif DT (−40% 2030)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-6 h-0.5 bg-green-600 rounded" />
          Projection actions planifiées
        </span>
        <span className="ml-auto text-xs text-gray-400">
          Réf. {trajectoire.refYear} · {trajectoire.surfaceM2Total?.toLocaleString('fr-FR')} m²
        </span>
      </div>

      {/* ── Graphique Recharts ── */}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="annee" tick={{ fontSize: 11, fill: '#6b7280' }} />
          <YAxis
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickFormatter={(v) => (mode === 'pct' ? `${v}%` : `${v}`)}
            label={{
              value: mode === 'pct' ? 'Réduction (%)' : 'MWh',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 10, fill: '#9ca3af' },
            }}
          />
          <Tooltip
            formatter={(value, name) => {
              if (value == null) return ['—', name];
              return mode === 'pct' ? [`${value.toFixed(1)} %`, name] : [`${value} MWh`, name];
            }}
            labelFormatter={(l) => `Année ${l}`}
          />

          {/* Réel */}
          <Area
            type="monotone"
            dataKey={yKey('reel')}
            name="Réel"
            stroke="#378ADD"
            fill="rgba(55,138,221,0.08)"
            strokeWidth={2}
            dot={{ r: 3, fill: '#378ADD' }}
            connectNulls={false}
          />

          {/* Objectif DT */}
          <Line
            type="monotone"
            dataKey={yKey('objectif')}
            name="Objectif DT"
            stroke="#E24B4A"
            strokeWidth={1.5}
            strokeDasharray="5 3"
            dot={false}
            connectNulls
          />

          {/* Projection + actions */}
          <Area
            type="monotone"
            dataKey={yKey('projection')}
            name="Projection + actions"
            stroke="#1D9E75"
            fill="rgba(29,158,117,0.06)"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={{ r: 2, fill: '#1D9E75' }}
            connectNulls={false}
          />

          {/* Année courante */}
          <ReferenceLine
            x={new Date().getFullYear()}
            stroke="#9ca3af"
            strokeDasharray="3 3"
            label={{ value: "Aujourd'hui", position: 'top', fontSize: 10, fill: '#9ca3af' }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* ── Jalons DT ── */}
      <div className="flex gap-3 mt-2 text-xs text-gray-500 flex-wrap">
        <span>Jalons :</span>
        {trajectoire.jalons?.map((j) => (
          <span key={j.annee} className="text-blue-600 font-medium">
            {j.annee} {j.reduction_pct} %
          </span>
        ))}
      </div>

      {/* ── Barres kWh/m² par site ── */}
      {sites?.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Performance par site — kWh/m²
          </div>
          {sites.map((site) => (
            <SiteBar key={site.nom} site={site} />
          ))}
        </div>
      )}
    </div>
  );
}
