/**
 * PROMEOS — PortfolioPanel (Sprint V12-C)
 * Portfolio view: aggregate global chart + per-site ranking table.
 *
 * Shown when isPortfolioMode=true (>5 sites or explicit toggle).
 * Panels: Top Conso | Top Dérive | Top Hors-horaires
 * Each row has mini sparkline (inline SVG) + KPI badge.
 *
 * Props:
 *   motor       — useExplorerMotor return value
 *   sites       — [{id, nom}] full site list
 *   unit        — 'kwh' | 'kw' | 'eur'
 */
import { memo, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { colorForSite } from './helpers';
import { Card, CardBody } from '../../ui';

const _EUR_FACTOR = 0.18;

/** Compute a single site's KPIs from its tunnel data */
function computeSiteKPIs(tunnel) {
  if (!tunnel) return null;
  const weekday = tunnel.envelope?.weekday || [];
  if (!weekday.length) return null;

  const vals = weekday.map((s) => s.p50 ?? 0);
  const total = vals.reduce((a, b) => a + b, 0);
  const peak = Math.max(...vals);

  // Night hours 0-6
  const nightVals = weekday.filter((s) => s.hour < 6 || s.hour >= 22).map((s) => s.p50 ?? 0);
  const nightSum = nightVals.reduce((a, b) => a + b, 0);
  const offHoursPct = total > 0 ? (nightSum / total) * 100 : 0;

  // Talon: minimum p10 (base load)
  const talonVals = weekday
    .filter((s) => s.hour >= 0 && s.hour < 6)
    .map((s) => s.p10 ?? s.p50 ?? 0);
  const talon = talonVals.length ? Math.min(...talonVals) : 0;

  return {
    total_kwh: Math.round(total * 24), // rough daily kWh from per-hour p50 sum × hours
    peak_kw: Math.round(peak * 10) / 10,
    off_hours_pct: Math.round(offHoursPct * 10) / 10,
    talon_kw: Math.round(talon * 10) / 10,
    outside_pct: tunnel.outside_pct ?? null,
    hourly: weekday.map((s) => s.p50 ?? 0),
  };
}

/** Inline mini sparkline using recharts */
const MiniSparkline = memo(function MiniSparkline({ data, color }) {
  const chartData = useMemo(() => (data || []).map((v, i) => ({ i, v })), [data]);
  if (!data?.length) return <span className="w-16 h-6 bg-gray-100 rounded inline-block" />;
  return (
    <div style={{ width: 64, height: 24, display: 'inline-block' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={2}>
          <Bar dataKey="v" fill={color} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
});

function fmt(v, dec = 0) {
  if (v == null) return '—';
  return v.toLocaleString('fr-FR', { maximumFractionDigits: dec });
}

/** Single ranking table for one metric */
const RankingTable = memo(function RankingTable({
  rows,
  valueKey,
  valueLabel: _valueLabel,
  unit: _unit,
  suffix = '',
}) {
  const sorted = useMemo(
    () =>
      [...rows]
        .filter((r) => r.kpis?.[valueKey] != null)
        .sort((a, b) => (b.kpis[valueKey] ?? 0) - (a.kpis[valueKey] ?? 0))
        .slice(0, 10),
    [rows, valueKey]
  );

  if (!sorted.length) {
    return <p className="text-xs text-gray-400 py-4 text-center">Aucune donnée disponible</p>;
  }

  const maxVal = sorted[0].kpis[valueKey] ?? 1;

  return (
    <div className="space-y-1">
      {sorted.map((row, rank) => {
        const val = row.kpis[valueKey] ?? 0;
        const pct = maxVal > 0 ? (val / maxVal) * 100 : 0;
        return (
          <div key={row.site.id} className="flex items-center gap-2 py-1">
            <span className="text-xs text-gray-400 w-4 text-right shrink-0">{rank + 1}</span>
            <span className="text-xs text-gray-600 truncate flex-1 min-w-0">{row.site.nom}</span>
            <MiniSparkline data={row.kpis.hourly} color={row.color} />
            <div className="flex items-center gap-1 shrink-0">
              {/* Inline bar */}
              <div className="w-16 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: row.color }}
                />
              </div>
              <span className="text-xs font-semibold text-gray-700 w-16 text-right">
                {fmt(val, valueKey === 'off_hours_pct' ? 1 : 0)}
                {suffix}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
});

/** Aggregate chart across all sites */
function AggregateChart({ rows, unit }) {
  const data = useMemo(() => {
    if (!rows.length) return [];
    const hours = Array.from({ length: 24 }, (_, h) => ({ hour: `${h}h`, total: 0 }));
    for (const row of rows) {
      if (!row.kpis?.hourly?.length) continue;
      row.kpis.hourly.forEach((v, h) => {
        if (hours[h]) hours[h].total += v;
      });
    }
    return hours;
  }, [rows]);

  if (!data.length) return null;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={3} />
        <YAxis tick={{ fontSize: 9 }} width={36} />
        <Tooltip
          formatter={(v) => [
            `${v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${unit === 'eur' ? '€' : 'kWh'}`,
            'Agrégé',
          ]}
        />
        <Bar dataKey="total" fill="#6366f1" radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function PortfolioPanel({ motor, sites, unit = 'kwh' }) {
  const { data, loading } = motor;

  const rows = useMemo(() => {
    return sites
      .map((site, idx) => {
        const tunnel = data.tunnelBySite[site.id];
        const kpis = computeSiteKPIs(tunnel);
        return { site, kpis, color: colorForSite(site.id, idx) };
      })
      .filter((r) => r.kpis != null);
  }, [data.tunnelBySite, sites]);

  if (loading && !rows.length) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-48 bg-gray-200 rounded-lg" />
        <div className="h-32 bg-gray-200 rounded-lg" />
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-500">
          Aucune donnée de consommation disponible pour le Portfolio.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Chargez un pack démo ou importez des données pour visualiser le Portfolio.
        </p>
      </div>
    );
  }

  // Aggregate chart data: sites with data loaded
  const loadedCount = rows.length;
  const totalSites = sites.length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-800">Vue Portfolio</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {loadedCount} / {totalSites} sites — enveloppe agrégée journalière (P50)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Quick stats */}
          <span className="text-xs text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full">
            {fmt(rows.reduce((s, r) => s + (r.kpis?.total_kwh ?? 0), 0))} kWh agrégés/j
          </span>
        </div>
      </div>

      {/* Aggregate chart */}
      <Card>
        <CardBody>
          <h4 className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
            Profil de charge agrégé (P50 somme — semaine)
          </h4>
          <AggregateChart rows={rows} unit={unit} />
        </CardBody>
      </Card>

      {/* Rankings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardBody>
            <h4 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">
              🔋 Top Consommation
            </h4>
            <RankingTable
              rows={rows}
              valueKey="total_kwh"
              valueLabel="kWh/j"
              unit={unit}
              suffix=" kWh"
            />
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h4 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">
              ⚡ Top Dérive (% hors bande)
            </h4>
            <RankingTable
              rows={rows}
              valueKey="outside_pct"
              valueLabel="% hors bande"
              unit={unit}
              suffix=" %"
            />
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h4 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">
              🌙 Top Hors-horaires
            </h4>
            <RankingTable
              rows={rows}
              valueKey="off_hours_pct"
              valueLabel="% hors-horaires"
              unit={unit}
              suffix=" %"
            />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
