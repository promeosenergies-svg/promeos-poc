/**
 * TrajectorySection — Courbe trajectoire Décret Tertiaire.
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
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <Skeleton className="h-5 w-72 mb-4" />
        <Skeleton className="h-[280px] w-full rounded-lg" />
      </div>
    );
  }

  // ── Empty / Partial ──
  if (!trajectoire?.annees?.length) {
    if (trajectoire?.partial && trajectoire.jalons?.length) {
      return (
        <div
          className="bg-white border border-gray-200 rounded-xl p-5"
          data-testid="trajectory-section"
        >
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Trajectoire de consommation vs objectifs Décret Tertiaire
          </h3>
          <p className="text-xs text-gray-500 mb-3">
            Données de consommation annuelle en cours de collecte — jalons réglementaires :
          </p>
          <div className="flex gap-2 text-xs text-gray-500 flex-wrap">
            <span className="text-gray-400">Jalons DT ·</span>
            {trajectoire.jalons.map((j) => (
              <span key={j.annee} className="text-blue-600 font-medium">
                {j.annee} {j.reduction_pct}%
              </span>
            ))}
          </div>
        </div>
      );
    }
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <EmptyState
          title="Trajectoire non disponible"
          text="Aucune donnée de consommation annuelle disponible pour calculer la trajectoire."
        />
      </div>
    );
  }

  const yKey = (base) => (mode === 'pct' ? `${base}Pct` : base);
  const nbSites = (sites?.length ?? trajectoire.annees?.length) ? '' : '';
  const siteCount = sites?.length ?? 0;

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-5"
      data-testid="trajectory-section"
    >
      {/* ── Header + Toggle ── */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Trajectoire de consommation vs objectifs Décret Tertiaire
        </h3>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
          <button
            onClick={() => setMode('kwh')}
            className={`px-3 py-1.5 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              mode === 'kwh' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            KWH
          </button>
          <button
            onClick={() => setMode('pct')}
            className={`px-3 py-1.5 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              mode === 'pct' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            % RÉDUCTION
          </button>
        </div>
      </div>

      {/* ── Légende custom ── */}
      <div className="flex gap-5 flex-wrap mb-4 text-xs text-gray-600">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-0.5 bg-blue-500 rounded" />
          <span className="font-medium">
            Réel HELIOS{siteCount > 0 ? ` (${siteCount} sites)` : ''}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed border-red-400" />
          <span>Objectif DT (−40% 2030)</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dotted border-green-600" />
          <span>Projection actions planifiées</span>
        </span>
      </div>

      {/* ── Graphique Recharts ── */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="annee" tick={{ fontSize: 11, fill: '#6b7280' }} />
          <YAxis
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickFormatter={(v) => (mode === 'pct' ? `${v}%` : `${v.toLocaleString('fr-FR')} MWh`)}
            label={{
              value: mode === 'pct' ? 'Réduction (%)' : 'MWh',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 10, fill: '#9ca3af' },
            }}
            width={80}
          />
          <Tooltip
            formatter={(value, name) => {
              if (value == null) return ['—', name];
              return mode === 'pct'
                ? [`${value.toFixed(1)} %`, name]
                : [`${value.toLocaleString('fr-FR')} MWh`, name];
            }}
            labelFormatter={(l) => `Année ${l}`}
          />

          {/* Réel HELIOS */}
          <Area
            type="monotone"
            dataKey={yKey('reel')}
            name="Réel HELIOS"
            stroke="#378ADD"
            fill="rgba(55,138,221,0.10)"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#378ADD', strokeWidth: 0 }}
            connectNulls={false}
          />

          {/* Objectif DT */}
          <Line
            type="monotone"
            dataKey={yKey('objectif')}
            name="Objectif DT"
            stroke="#E24B4A"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            dot={false}
            connectNulls
          />

          {/* Projection + actions */}
          <Area
            type="monotone"
            dataKey={yKey('projection')}
            name="Projection + actions"
            stroke="#1D9E75"
            fill="rgba(29,158,117,0.12)"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={{ r: 3, fill: '#1D9E75', strokeWidth: 0 }}
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

      {/* ── Footer : Jalons + Référence ── */}
      <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-gray-400">Jalons DT ·</span>
          {trajectoire.jalons?.map((j, i) => (
            <span key={j.annee}>
              <span className="text-blue-600 font-medium">
                {j.annee} {j.reduction_pct}%
              </span>
              {i < trajectoire.jalons.length - 1 && <span className="text-gray-300 mx-0.5">·</span>}
            </span>
          ))}
        </div>
        <span className="text-gray-400">
          Réf. {trajectoire.refYear} · Surface :{' '}
          {trajectoire.surfaceM2Total?.toLocaleString('fr-FR') ?? '—'} m²
        </span>
      </div>
    </div>
  );
}
