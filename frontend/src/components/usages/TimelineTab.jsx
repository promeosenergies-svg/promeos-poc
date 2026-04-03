import { useState, useEffect, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Scatter,
  Line,
} from 'recharts';
import { getEnergySignature } from '../../services/api';

export default function TimelineTab({ data, siteId }) {
  const [mode, setMode] = useState('timeline');
  const [signature, setSignature] = useState(null);
  const [sigLoading, setSigLoading] = useState(false);

  useEffect(() => {
    if (mode !== 'signature' || !siteId) {
      setSignature(null);
      return;
    }
    let cancelled = false;
    setSigLoading(true);
    setSignature(null);
    getEnergySignature(siteId)
      .then((d) => {
        if (!cancelled) setSignature(d);
      })
      .catch(() => {
        if (!cancelled) setSignature(null);
      })
      .finally(() => {
        if (!cancelled) setSigLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, siteId]);

  const noTimeline = !data || !data.series?.length;
  const canShowSignature = !!siteId;

  return (
    <div className="p-5">
      {canShowSignature && (
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setMode('timeline')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              mode === 'timeline'
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            📈 Évolution
          </button>
          <button
            onClick={() => setMode('signature')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              mode === 'signature'
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            🔬 Signature DJU
          </button>
        </div>
      )}

      {mode === 'timeline' &&
        (noTimeline ? (
          <div className="text-sm text-gray-400 italic">Données temporelles insuffisantes.</div>
        ) : (
          <TimelineChart data={data} />
        ))}

      {mode === 'signature' && <SignaturePanel loading={sigLoading} signature={signature} />}
    </div>
  );
}

/* ── Signature Panel (avoids nested ternaries) ─────────────────────── */

function SignaturePanel({ loading, signature }) {
  if (loading) {
    return (
      <div className="text-sm text-gray-400 italic py-8 text-center">
        Calcul de la signature énergétique...
      </div>
    );
  }
  if (signature?.error) {
    return <div className="text-sm text-gray-400 italic py-4">{signature.error}</div>;
  }
  if (signature?.signature && signature?.regression_line && signature?.scatter_data) {
    return <SignatureView signature={signature} />;
  }
  return (
    <div className="text-sm text-gray-400 italic py-4">Signature non disponible pour ce site.</div>
  );
}

/* ── AreaChart Évolution ─────────────────────────────────────────────── */

function TimelineChart({ data }) {
  const chartData = useMemo(
    () =>
      data.months.map((m, i) => {
        const row = { month: m.slice(5) };
        data.series.forEach((s) => {
          row[s.usage] = s.data[i] || 0;
        });
        return row;
      }),
    [data]
  );

  // Derive period label from months range
  const periodLabel =
    data.months?.length >= 2 ? `${data.months[0]} à ${data.months[data.months.length - 1]}` : '';

  return (
    <>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F5F5F3" />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              label={{
                value: 'kWh / mois',
                angle: -90,
                position: 'insideLeft',
                fontSize: 10,
                fill: '#9CA3AF',
              }}
            />
            <Tooltip formatter={(v, name) => [`${Number(v).toLocaleString()} kWh`, name]} />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            {data.series.map((s) => (
              <Area
                key={s.usage}
                type="monotone"
                dataKey={s.usage}
                stackId="1"
                fill={s.color}
                stroke={s.color}
                fillOpacity={0.5}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {periodLabel && (
        <div className="text-[10px] text-gray-400 px-2 mt-1">
          Consommation mensuelle par usage · {periodLabel}
        </div>
      )}
    </>
  );
}

/* ── Scatter Plot Signature DJU ──────────────────────────────────────── */

function SignatureView({ signature }) {
  const { signature: sig, benchmark, savings_potential, regression_line, scatter_data } = signature;

  const regressionData = useMemo(
    () => [
      { dju: regression_line.x_min, kwh: regression_line.y_at_x_min },
      { dju: regression_line.x_max, kwh: regression_line.y_at_x_max },
    ],
    [regression_line]
  );

  const combinedData = useMemo(
    () => [
      ...scatter_data.map((d) => ({ ...d, type: 'scatter' })),
      ...regressionData.map((d) => ({ ...d, type: 'line' })),
    ],
    [scatter_data, regressionData]
  );

  const baseloadExcessPct =
    benchmark.baseload_expected > 0
      ? ((sig.baseload_kwh_day / benchmark.baseload_expected - 1) * 100).toFixed(0)
      : 0;

  return (
    <>
      {/* KPIs signature */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <KpiCard
          label="Baseload"
          value={`${sig.baseload_kwh_day.toLocaleString()} kWh/j`}
          sub={`réf. ${benchmark.baseload_expected} kWh/j`}
          status={benchmark.baseload_verdict}
        />
        <KpiCard
          label="Thermosens."
          value={`${sig.thermosensitivity_kwh_dju} kWh/DJU`}
          sub={`réf. ${benchmark.thermo_expected} kWh/DJU`}
          status={benchmark.thermo_verdict}
        />
        <KpiCard
          label="R²"
          value={sig.r_squared?.toFixed(3) ?? 'N/A'}
          sub={sig.model_quality}
          status={sig.r_squared > 0.7 ? 'normal' : 'warning'}
        />
        <KpiCard
          label="Économie potentielle"
          value={`${savings_potential.total_savings_eur.toLocaleString()} €/an`}
          sub={`${savings_potential.total_savings_kwh.toLocaleString()} kWh`}
          status={savings_potential.total_savings_eur > 0 ? 'elevated' : 'normal'}
        />
      </div>

      {/* Scatter plot DJU vs kWh + droite régression */}
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={combinedData} margin={{ left: 10, right: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F5F5F3" />
            <XAxis
              dataKey="dju"
              type="number"
              name="DJU"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              label={{ value: 'DJU chauffage', position: 'bottom', offset: 5, fontSize: 10 }}
            />
            <YAxis
              dataKey="kwh"
              type="number"
              name="kWh"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              label={{ value: 'kWh/jour', angle: -90, position: 'insideLeft', fontSize: 10 }}
            />
            <Tooltip
              formatter={(v, name) => [
                name === 'dju'
                  ? `${Number(v).toFixed(1)} DJU`
                  : `${Number(v).toLocaleString()} kWh`,
                name === 'dju' ? 'DJU chauf.' : 'Conso.',
              ]}
            />
            <Scatter
              dataKey="kwh"
              data={scatter_data}
              fill="#6366F1"
              fillOpacity={0.4}
              r={3}
              name="Conso. journalière"
            />
            <Line
              dataKey="kwh"
              data={regressionData}
              stroke="#DC2626"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              name="E = a×DJU + b"
              legendType="line"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Verdicts */}
      {benchmark.baseload_verdict === 'elevated' && (
        <div className="mt-2 p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          <strong>⚠ Baseload +{baseloadExcessPct}%</strong> au-dessus du benchmark{' '}
          <em>{benchmark.archetype}</em> — gaspillage non-thermique estimé{' '}
          <strong>{savings_potential.baseload_excess_eur_year.toLocaleString()} €/an</strong>
          <div className="text-red-500 mt-0.5">
            Pistes : éclairage nuit, serveurs, veilles, ventilation permanente
          </div>
        </div>
      )}
      {benchmark.thermo_verdict === 'elevated' && (
        <div className="mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          <strong>⚠ Thermosensibilité élevée</strong> — isolation ou GTB à auditer — surcoût estimé{' '}
          <strong>{savings_potential.thermo_excess_eur_year.toLocaleString()} €/an</strong>
        </div>
      )}

      {/* Source */}
      <div className="mt-2 text-[10px] text-gray-400 text-right">
        {signature.period_days} jours · {signature.dju_summary.source} ·{' '}
        {signature.dju_summary.annual_dju_chauf} DJU chauf./an
      </div>
    </>
  );
}

/* ── Mini KPI Card ───────────────────────────────────────────────────── */

function KpiCard({ label, value, sub, status }) {
  const borderColor =
    status === 'elevated'
      ? 'border-red-200 bg-red-50/50'
      : status === 'warning'
        ? 'border-amber-200 bg-amber-50/50'
        : 'border-gray-200 bg-white';

  return (
    <div className={`rounded-lg border p-2 ${borderColor}`}>
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
      <div
        className="text-sm font-semibold text-gray-900 mt-0.5"
        style={{ fontFamily: 'JetBrains Mono, monospace' }}
      >
        {value}
      </div>
      <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>
    </div>
  );
}
