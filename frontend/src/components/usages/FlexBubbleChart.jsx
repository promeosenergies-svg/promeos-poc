import { useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const revenueColor = (rev) => {
  if (rev > 20000) return '#16A34A';
  if (rev > 10000) return '#65A30D';
  if (rev > 5000) return '#D97706';
  return '#9CA3AF';
};

export default function FlexBubbleChart({ data }) {
  const chartData = useMemo(
    () =>
      (data?.sites || []).map((s) => ({
        x: s.availability_pct ?? 50,
        y: 6 - (s.complexity_score ?? 3),
        z: s.kw_pilotable ?? 10,
        name: s.site_name,
        revenue: s.revenue_mid_eur ?? 0,
        nebco: s.nebco_eligible ?? false,
        kw: s.kw_pilotable ?? 0,
      })),
    [data?.sites]
  );

  if (!data?.sites?.length) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="text-[13px] font-semibold mb-2">Portefeuille flexibilité</div>
      <div className="text-[10px] text-gray-400 mb-2">
        {data.total_sites} sites · {fmt(data.total_kw)} kW pilotable · {data.nebco_sites} NEBCO
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="x"
              type="number"
              domain={[0, 100]}
              name="Disponibilité"
              unit="%"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              label={{
                value: 'Disponibilité flex (%)',
                position: 'bottom',
                offset: 5,
                style: { fontSize: 10 },
              }}
            />
            <YAxis
              dataKey="y"
              type="number"
              domain={[1, 5]}
              tick={{ fontSize: 10 }}
              tickFormatter={(v) => ({ 2: 'Complexe', 3.5: 'Moyen', 5: 'Simple' })[v] || ''}
            />
            <ZAxis dataKey="z" range={[100, 800]} name="kW pilotable" />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-white border border-gray-200 rounded-lg p-2 shadow text-xs">
                    <div className="font-medium">{d.name}</div>
                    <div>{fmt(d.kw)} kW pilotable</div>
                    <div>Revenu : {fmt(d.revenue)} €/an</div>
                    <div>{d.nebco ? '✓ NEBCO éligible' : '✗ Non éligible'}</div>
                  </div>
                );
              }}
            />
            <Scatter data={chartData}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={revenueColor(entry.revenue)}
                  fillOpacity={0.7}
                  stroke={revenueColor(entry.revenue)}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Légende */}
      <div className="flex gap-3 text-[10px] text-gray-400 mt-1">
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-green-600 mr-1" />
          &gt;20k€
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-lime-600 mr-1" />
          10-20k€
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />
          5-10k€
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-gray-400 mr-1" />
          &lt;5k€
        </span>
        <span className="ml-auto">Taille = kW pilotable</span>
      </div>
    </div>
  );
}
