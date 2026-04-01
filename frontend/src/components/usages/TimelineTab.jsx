import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function TimelineTab({ data }) {
  if (!data || !data.series?.length) {
    return (
      <div className="p-6 text-sm text-gray-400 italic">Données temporelles insuffisantes.</div>
    );
  }

  const chartData = data.months.map((m, i) => {
    const row = { month: m.slice(5) };
    data.series.forEach((s) => {
      row[s.usage] = s.data[i] || 0;
    });
    return row;
  });

  return (
    <div className="p-5">
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F5F5F3" />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
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
    </div>
  );
}
