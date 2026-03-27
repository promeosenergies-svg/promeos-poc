/**
 * MarketWidget — Widget compact Market Intelligence pour le Cockpit.
 *
 * Affiche en un coup d'œil :
 * - Prix spot moyen 7j + tendance vs 30j
 * - Mini sparkline 7j
 * - Décomposition prix TTC en barre empilée
 *
 * Données : useMarketData hook (endpoints /api/market/*)
 * Calcul : ZERO — tout vient du backend
 */
import React, { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Zap, RefreshCw, Info } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, Tooltip as RTooltip } from 'recharts';
import { useMarketData } from '../../hooks/useMarketData';

// Couleurs des briques pour la barre empilée
const BRIQUE_COLORS = {
  energy: '#D85A30',
  turpe: '#BA7517',
  cspe: '#185FA5',
  capacity: '#1D9E75',
  cee: '#534AB7',
  cta: '#D4537E',
  tva: '#888780',
};

const BRIQUE_LABELS = {
  energy: 'Énergie',
  turpe: 'TURPE',
  cspe: 'CSPE',
  capacity: 'Capacité',
  cee: 'CEE',
  cta: 'CTA',
  tva: 'TVA',
};

export default function MarketWidget({ profile = 'C4' }) {
  const { data, loading, error, refresh } = useMarketData(profile);

  const spotAvg7 = data?.spot?.avg_eur_mwh;
  const spotMin7 = data?.spot?.min_eur_mwh;
  const spotMax7 = data?.spot?.max_eur_mwh;

  // Tendance : dernières 24h vs 24h précédentes
  const trend = useMemo(() => {
    if (!data?.history?.prices || data.history.prices.length < 2) return 'stable';
    const prices = data.history.prices;
    const recent = prices.slice(-24);
    const earlier = prices.slice(0, 24);
    if (recent.length === 0 || earlier.length === 0) return 'stable';
    const avgRecent = recent.reduce((s, p) => s + p.price_eur_mwh, 0) / recent.length;
    const avgEarlier = earlier.reduce((s, p) => s + p.price_eur_mwh, 0) / earlier.length;
    const delta = ((avgRecent - avgEarlier) / avgEarlier) * 100;
    if (delta > 3) return 'up';
    if (delta < -3) return 'down';
    return 'stable';
  }, [data?.history]);

  // Sparkline data (agrégé par jour)
  const sparkData = useMemo(() => {
    if (!data?.history?.prices) return [];
    const byDay = {};
    data.history.prices.forEach((p) => {
      const day = p.delivery_start.slice(0, 10);
      if (!byDay[day]) byDay[day] = { prices: [], day };
      byDay[day].prices.push(p.price_eur_mwh);
    });
    return Object.values(byDay)
      .map((d) => ({
        day: d.day.slice(5),
        avg: Math.round(d.prices.reduce((s, v) => s + v, 0) / d.prices.length),
      }))
      .slice(-7);
  }, [data?.history]);

  // Décomposition — briques pour la barre empilée
  const briques = useMemo(() => {
    const d = data?.decomposition;
    if (!d) return null;
    const total = d.total_ttc_eur_mwh || 1;
    return [
      { key: 'energy', value: d.energy_eur_mwh, pct: (d.energy_eur_mwh / total) * 100 },
      { key: 'turpe', value: d.turpe_eur_mwh, pct: (d.turpe_eur_mwh / total) * 100 },
      { key: 'cspe', value: d.cspe_eur_mwh, pct: (d.cspe_eur_mwh / total) * 100 },
      { key: 'capacity', value: d.capacity_eur_mwh, pct: (d.capacity_eur_mwh / total) * 100 },
      { key: 'cee', value: d.cee_eur_mwh, pct: (d.cee_eur_mwh / total) * 100 },
      { key: 'cta', value: d.cta_eur_mwh, pct: (d.cta_eur_mwh / total) * 100 },
      { key: 'tva', value: d.tva_eur_mwh, pct: (d.tva_eur_mwh / total) * 100 },
    ];
  }, [data?.decomposition]);

  // Forward CAL le plus proche
  const forwardCal = useMemo(() => {
    if (!data?.forwards?.curves) return null;
    const cals = data.forwards.curves.filter((c) => c.market_type === 'FORWARD_YEAR');
    return cals.length > 0 ? cals[0] : null;
  }, [data?.forwards]);

  // ── Render ──

  if (loading && !data) {
    return (
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-zinc-200 dark:bg-zinc-700 rounded w-32 mb-3" />
        <div className="h-20 bg-zinc-100 dark:bg-zinc-800 rounded mb-3" />
        <div className="h-6 bg-zinc-100 dark:bg-zinc-800 rounded" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4">
        <div className="flex items-center gap-2 text-zinc-500 text-sm">
          <Zap size={14} />
          <span>Données marché indisponibles</span>
          <button onClick={refresh} className="ml-auto text-blue-600 hover:text-blue-700">
            <RefreshCw size={12} />
          </button>
        </div>
      </div>
    );
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor =
    trend === 'up' ? 'text-red-500' : trend === 'down' ? 'text-green-600' : 'text-zinc-400';

  return (
    <div
      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4"
      data-testid="market-widget"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-amber-500" />
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
            Marché électricité
          </span>
        </div>
        <button
          onClick={refresh}
          className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          title="Actualiser"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Zone 1 — Spot headline */}
      <div className="flex items-end justify-between mb-2">
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 tabular-nums">
              {spotAvg7 != null ? spotAvg7.toFixed(1) : '—'}
            </span>
            <span className="text-xs text-zinc-500">€/MWh</span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            Spot moy. 7j · {spotMin7 != null ? `${spotMin7}–${spotMax7}` : ''}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className={`flex items-center gap-1 ${trendColor}`}>
            <TrendIcon size={14} />
            <span className="text-xs font-medium">
              {trend === 'up' ? 'Hausse' : trend === 'down' ? 'Baisse' : 'Stable'}
            </span>
          </div>
          {forwardCal && (
            <div className="text-xs text-zinc-400">
              CAL{forwardCal.delivery_start.slice(2, 4)} : {forwardCal.price_eur_mwh.toFixed(1)} €
            </div>
          )}
        </div>
      </div>

      {/* Zone 2 — Mini sparkline */}
      {sparkData.length > 0 && (
        <div className="h-16 -mx-1 mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <defs>
                <linearGradient id="mktSpotGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#BA7517" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#BA7517" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="avg"
                stroke="#BA7517"
                strokeWidth={1.5}
                fill="url(#mktSpotGrad)"
                dot={false}
                isAnimationActive={false}
              />
              <RTooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  border: '1px solid #e4e4e7',
                  background: '#fff',
                }}
                formatter={(v) => [`${v} €/MWh`, 'Spot moy.']}
                labelFormatter={(l) => l}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Zone 3 — Décomposition barre empilée */}
      {briques && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-zinc-500">Décomposition prix {profile}</span>
            <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 tabular-nums">
              {data.decomposition.total_ttc_eur_mwh.toFixed(0)} €/MWh TTC
            </span>
          </div>

          {/* Barre empilée */}
          <div className="flex h-5 rounded-md overflow-hidden mb-2">
            {briques.map((b) => (
              <div
                key={b.key}
                className="relative group transition-all hover:brightness-110"
                style={{
                  width: `${Math.max(b.pct, 1.5)}%`,
                  backgroundColor: BRIQUE_COLORS[b.key],
                }}
              >
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10 whitespace-nowrap bg-zinc-900 text-white text-[10px] px-2 py-1 rounded shadow">
                  {BRIQUE_LABELS[b.key]} : {b.value.toFixed(1)} €/MWh ({b.pct.toFixed(0)}%)
                </div>
              </div>
            ))}
          </div>

          {/* Légende compacte — top 3 + "autres" */}
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {briques.slice(0, 3).map((b) => (
              <div key={b.key} className="flex items-center gap-1 text-[10px] text-zinc-500">
                <span
                  className="inline-block w-2 h-2 rounded-sm shrink-0"
                  style={{ backgroundColor: BRIQUE_COLORS[b.key] }}
                />
                {BRIQUE_LABELS[b.key]} {b.pct.toFixed(0)}%
              </div>
            ))}
            <div className="flex items-center gap-1 text-[10px] text-zinc-400">
              <span className="inline-block w-2 h-2 rounded-sm shrink-0 bg-zinc-300 dark:bg-zinc-600" />
              Autres {(100 - briques.slice(0, 3).reduce((s, b) => s + b.pct, 0)).toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      {/* Footer — méthode + fraîcheur */}
      {data?.decomposition && (
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <span className="text-[10px] text-zinc-400">
            {data.decomposition.calculation_method === 'SPOT_BASED'
              ? 'Basé spot 30j'
              : data.decomposition.calculation_method === 'FORWARD_BASED'
                ? 'Basé forward'
                : data.decomposition.calculation_method === 'FALLBACK'
                  ? 'Estimation'
                  : 'Prix forcé'}
            {' · '}
            {data.decomposition.tariff_version}
          </span>
          {data.decomposition.warnings?.length > 0 && (
            <div
              className="flex items-center gap-1 text-amber-500"
              title={data.decomposition.warnings.join(' | ')}
            >
              <Info size={10} />
              <span className="text-[10px]">
                {data.decomposition.warnings.length} avertissement(s)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
