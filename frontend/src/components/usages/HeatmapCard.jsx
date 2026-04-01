import React from 'react';

const fmt = (n) => (n == null ? '—' : Math.round(n));

export default function HeatmapCard({ data, currentSiteId }) {
  if (!data?.sites?.length) return null;

  const usages = data.usages?.slice(0, 4) || [];
  const maxByUsage = {};
  usages.forEach((u) => {
    maxByUsage[u] = Math.max(...data.sites.map((s) => s.ipe_by_usage[u] || 0));
  });

  const cellBg = (val, maxVal) => {
    if (!val || !maxVal) return '#F3F4F6';
    const intensity = val / maxVal;
    if (intensity > 0.8) return '#FEE2E2';
    if (intensity > 0.5) return '#FED7AA';
    if (intensity > 0.2) return '#FEF9C3';
    return '#DBEAFE';
  };

  const cellColor = (val, maxVal) => {
    if (!val || !maxVal) return '#9CA3AF';
    const intensity = val / maxVal;
    if (intensity > 0.8) return '#991B1B';
    if (intensity > 0.5) return '#9A3412';
    if (intensity > 0.2) return '#854D0E';
    return '#1E40AF';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[13px] font-semibold">Portefeuille IPE</span>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-600">
          kWh/m²
        </span>
      </div>
      <div
        className="grid gap-px text-[10px]"
        style={{ gridTemplateColumns: `80px repeat(${usages.length + 1}, 1fr)` }}
      >
        <div />
        {usages.map((u) => (
          <div key={u} className="text-center font-semibold text-gray-400 py-1.5">
            {u.slice(0, 7)}
          </div>
        ))}
        <div className="text-center font-semibold text-gray-400 py-1.5">Total</div>
        {data.sites.map((s) => (
          <React.Fragment key={s.site_id}>
            <div
              className={`py-1.5 font-medium text-[11px] ${s.site_id === currentSiteId ? 'text-blue-600 font-semibold' : ''}`}
            >
              {s.site_name.length > 10 ? s.site_name.slice(0, 10) + '…' : s.site_name}
            </div>
            {usages.map((u) => {
              const val = s.ipe_by_usage[u];
              return (
                <div
                  key={u}
                  className="text-center py-1.5 rounded cursor-pointer font-mono font-medium transition-transform hover:scale-105"
                  style={{
                    background: cellBg(val, maxByUsage[u]),
                    color: cellColor(val, maxByUsage[u]),
                  }}
                >
                  {val ? fmt(val) : '—'}
                </div>
              );
            })}
            <div
              className="text-center py-1.5 font-mono font-bold"
              style={{
                background: '#F3F4F6',
                color: s.ipe_total > s.benchmark_ademe ? '#DC2626' : '#1A1A1A',
              }}
            >
              {fmt(s.ipe_total)}
            </div>
          </React.Fragment>
        ))}
        {/* Ref ADEME */}
        <div className="py-1.5 text-[9px] text-gray-400">Réf. ADEME</div>
        {usages.map((u) => (
          <div key={u} className="text-center py-1.5 text-[9px] text-gray-400 italic">
            {data.ademe_ref_by_usage?.[u] || '—'}
          </div>
        ))}
        <div className="text-center py-1.5 text-[9px] text-gray-400 italic">
          {data.sites[0]?.benchmark_ademe || '—'}
        </div>
      </div>
    </div>
  );
}
