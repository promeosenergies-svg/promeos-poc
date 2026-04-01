import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { getMeterReadingsPreview } from '../../services/api';

const fmt = (n, d = 0) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: d });

const TREND = {
  amelioration: { icon: '↘', cls: 'text-green-600' },
  degradation: { icon: '↗', cls: 'text-red-600' },
  stable: { icon: '→', cls: 'text-gray-500' },
};
const SRC_LABEL = {
  mesure_directe: 'Mesuré',
  estimation_prorata: 'Estimé',
  estimation_deterministe: 'Estimé',
  baseline_stockee: 'Baseline',
};
const SRC_CLS = {
  mesure_directe: 'bg-green-50 text-green-700',
  estimation_prorata: 'bg-amber-50 text-amber-700',
  estimation_deterministe: 'bg-amber-50 text-amber-700',
  baseline_stockee: 'bg-violet-50 text-violet-700',
};

export default function BaselineTab({ baselines, meteringPlan }) {
  const [expanded, setExpanded] = useState(null);
  const [meterData, setMeterData] = useState(null);
  const [expandedMeter, setExpandedMeter] = useState(null);

  if (!baselines?.length)
    return <div className="p-6 text-sm text-gray-400 italic">Baselines non disponibles.</div>;

  const totalEcart = baselines.reduce((s, b) => s + (b.ecart_kwh || 0), 0);
  const degradCount = baselines.filter((b) => b.trend === 'degradation').length;

  const toggleMeter = (meterId) => {
    if (expandedMeter === meterId) {
      setExpandedMeter(null);
      setMeterData(null);
      return;
    }
    setExpandedMeter(meterId);
    setMeterData(null);
    getMeterReadingsPreview(meterId)
      .then(setMeterData)
      .catch(() => setMeterData(null));
  };

  return (
    <div className="p-5">
      <div className="flex justify-between items-center mb-3">
        <div className="flex gap-1.5">
          {degradCount > 0 && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-red-50 text-red-600">
              {degradCount} en dégradation
            </span>
          )}
        </div>
        <span
          className={`font-mono text-sm font-semibold ${totalEcart > 0 ? 'text-red-600' : 'text-green-600'}`}
        >
          {totalEcart > 0 ? '+' : ''}
          {fmt(totalEcart)} kWh
        </span>
      </div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-1.5 px-2 text-[10px] text-gray-400 uppercase tracking-wide font-semibold">
              Usage
            </th>
            <th className="text-right py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              Baseline
            </th>
            <th className="text-right py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              Actuel
            </th>
            <th className="text-right py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              Écart
            </th>
            <th className="text-right py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              IPE
            </th>
            <th className="text-right py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              Obj. DT
            </th>
            <th className="py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">Tend.</th>
            <th className="py-1.5 px-2 text-[10px] text-gray-400 uppercase font-semibold">
              Source
            </th>
          </tr>
        </thead>
        <tbody>
          {baselines.map((b, i) => (
            <React.Fragment key={b.usage_id || i}>
              <tr
                className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpanded(expanded === b.label ? null : b.label)}
              >
                <td className="py-2 px-2 flex items-center gap-1.5">
                  <span className="text-[9px] text-gray-400">
                    {expanded === b.label ? '▼' : '▶'}
                  </span>
                  <span className="font-medium">{b.label}</span>
                  {b.is_significant && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-semibold">
                      UES
                    </span>
                  )}
                </td>
                <td className="text-right py-2 px-2 font-mono text-gray-500">
                  {fmt(b.kwh_baseline)}
                </td>
                <td className="text-right py-2 px-2 font-mono font-semibold">
                  {fmt(b.kwh_current)}
                </td>
                <td
                  className={`text-right py-2 px-2 font-mono font-semibold ${b.ecart_kwh > 0 ? 'text-red-600' : b.ecart_kwh < 0 ? 'text-green-600' : 'text-gray-500'}`}
                >
                  {b.ecart_kwh != null ? `${b.ecart_kwh > 0 ? '+' : ''}${fmt(b.ecart_kwh)}` : '—'}
                </td>
                <td className="text-right py-2 px-2">
                  {b.ipe_current != null ? fmt(b.ipe_current, 1) : '—'}
                </td>
                <td className="text-right py-2 px-2 text-indigo-600">
                  {b.dt_target_kwh_m2 ? fmt(b.dt_target_kwh_m2, 0) : '—'}
                </td>
                <td className={`py-2 px-2 ${TREND[b.trend]?.cls || 'text-gray-400'}`}>
                  {TREND[b.trend]?.icon || '—'}{' '}
                  {b.ecart_pct != null
                    ? `${b.ecart_pct > 0 ? '+' : ''}${fmt(b.ecart_pct, 1)}%`
                    : ''}
                </td>
                <td className="py-2 px-2">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${SRC_CLS[b.data_source] || 'bg-gray-100 text-gray-500'}`}
                  >
                    {SRC_LABEL[b.data_source] || b.data_source || '—'}
                  </span>
                </td>
              </tr>
              {expanded === b.label &&
                meteringPlan?.meters?.map((meter) =>
                  meter.sub_meters
                    ?.filter((s) => s.usage?.label === b.label)
                    .map((sub) => (
                      <React.Fragment key={sub.id}>
                        <tr
                          className="bg-gray-50 text-[11px]"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleMeter(sub.id);
                          }}
                        >
                          <td className="py-1.5 pl-7 pr-2 text-gray-500 cursor-pointer">
                            ↳ {sub.name || sub.meter_id} {expandedMeter === sub.id ? '▼' : '▶'}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500 font-mono">
                            {fmt(sub.kwh)}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500 font-mono">
                            {sub.pct_of_principal ? `${fmt(sub.pct_of_principal, 0)}%` : '—'}
                          </td>
                          <td colSpan={5} />
                        </tr>
                        {expandedMeter === sub.id && meterData?.readings?.length > 0 && (
                          <tr>
                            <td colSpan={8} className="py-2 px-7">
                              <div style={{ width: '100%', height: 80 }}>
                                <ResponsiveContainer>
                                  <LineChart data={meterData.readings}>
                                    <XAxis
                                      dataKey="ts"
                                      tick={{ fontSize: 8 }}
                                      tickFormatter={(v) => v?.slice(11, 16) || ''}
                                    />
                                    <YAxis tick={{ fontSize: 8 }} />
                                    <Tooltip formatter={(v) => [`${v} kWh`]} />
                                    <Line
                                      type="monotone"
                                      dataKey="kwh"
                                      stroke="#3b82f6"
                                      dot={false}
                                      strokeWidth={1.5}
                                    />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                              <div className="text-[9px] text-gray-400 text-right">
                                Total 7j : {fmt(meterData.total_kwh, 1)} kWh
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))
                )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
