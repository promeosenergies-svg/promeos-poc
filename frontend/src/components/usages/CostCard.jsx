import { useState } from 'react';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const COLORS = {
  Chauffage: '#E57373',
  Climatisation: '#64B5F6',
  Éclairage: '#FFD54F',
  'IT & Bureautique': '#7986CB',
  Ventilation: '#81C784',
  CVC: '#E57373',
  Process: '#FF8A65',
  Cuisine: '#FFAB91',
};

const PERIOD_COLORS = {
  HPH: '#EF4444',
  HCH: '#FCA5A5',
  HPB: '#3B82F6',
  HCB: '#93C5FD',
  P: '#7C3AED',
};

export default function CostCard({ data, costByPeriod }) {
  const [view, setView] = useState('usage');

  if (!data?.by_usage?.length) return null;

  // Build display list: usages + "Autres / non ventilé" if uncovered > 0
  const uncoveredEur = data.uncovered_eur || 0;
  const displayUsages = [...data.by_usage];
  if (uncoveredEur > 0) {
    const totalEurAll = data.by_usage.reduce((s, u) => s + (u.eur || 0), 0) + uncoveredEur;
    displayUsages.push({
      label: 'Autres / non ventilé',
      type: 'autres',
      eur: uncoveredEur,
      kwh: data.uncovered_kwh || 0,
      pct_of_total: totalEurAll > 0 ? Math.round((uncoveredEur / totalEurAll) * 100) : 0,
    });
  }

  const maxEur = Math.max(...displayUsages.map((u) => u.eur || 0));
  const priceRef = data.price_ref_eur_kwh || 0;
  const hasPeriodData = costByPeriod?.usages?.length > 0;
  const totalCostEur = displayUsages.reduce((s, u) => s + (u.eur || 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[13px] font-semibold">Coût par usage</span>
        <div className="flex items-center gap-1.5">
          {hasPeriodData && (
            <div className="flex rounded-md border border-gray-200 overflow-hidden text-[10px]">
              <button
                onClick={() => setView('usage')}
                className={`px-2 py-0.5 font-medium transition ${
                  view === 'usage'
                    ? 'bg-gray-800 text-white'
                    : 'bg-white text-gray-500 hover:bg-gray-50'
                }`}
              >
                Par usage
              </button>
              <button
                onClick={() => setView('period')}
                className={`px-2 py-0.5 font-medium transition ${
                  view === 'period'
                    ? 'bg-gray-800 text-white'
                    : 'bg-white text-gray-500 hover:bg-gray-50'
                }`}
              >
                Par période
              </button>
            </div>
          )}
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-500">
            {(priceRef * 100).toFixed(1)} c€/kWh
          </span>
        </div>
      </div>

      {/* Vue par usage (défaut) */}
      {view === 'usage' && (
        <>
          {displayUsages.slice(0, 6).map((u) => {
            const pct = maxEur > 0 ? (u.eur / maxEur) * 100 : 0;
            const isAutres = u.type === 'autres';
            return (
              <div key={u.label || u.type} className="flex items-center gap-2 py-1">
                <div
                  className={`w-[80px] text-[11px] font-medium truncate ${isAutres ? 'text-gray-400' : ''}`}
                >
                  {u.label || u.type}
                </div>
                <div className="flex-1 h-3.5 bg-gray-100 rounded overflow-hidden">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${pct}%`,
                      background: isAutres ? '#D1D5DB' : COLORS[u.label] || '#BDBDBD',
                    }}
                  />
                </div>
                <div className="min-w-[90px] text-right text-[10px] text-gray-500 font-mono">
                  {fmt(u.eur)} € ({u.pct_of_total ? Math.round(u.pct_of_total) : 0}%)
                </div>
              </div>
            );
          })}
          <div className="flex justify-between text-[11px] font-semibold pt-2 mt-1 border-t border-gray-100">
            <span>Total</span>
            <span className="font-mono">
              {fmt(totalCostEur)} €<span className="text-green-600 ml-1 text-[10px]">= KPI</span>
            </span>
          </div>
        </>
      )}

      {/* Vue par période tarifaire */}
      {view === 'period' && costByPeriod?.usages && (
        <div>
          {costByPeriod.usages.slice(0, 5).map((u) => (
            <div key={u.usage} className="mb-2.5">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[11px] font-medium">{u.usage}</span>
                <span className="text-[10px] text-gray-500 font-mono">{fmt(u.total_eur)} €</span>
              </div>
              <div className="flex h-4 rounded overflow-hidden">
                {['HPH', 'HCH', 'HPB', 'HCB'].map((p) => {
                  const pct = u.by_period?.[p]?.pct_eur || 0;
                  if (pct < 1) return null;
                  return (
                    <div
                      key={p}
                      style={{ width: `${pct}%`, background: PERIOD_COLORS[p] }}
                      className="transition-all"
                      title={`${p} : ${fmt(u.by_period[p]?.eur)} € (${pct}%)`}
                    />
                  );
                })}
              </div>
              {u.optimization?.savings_eur > 0 && (
                <div className="text-[10px] text-green-600 mt-0.5">
                  💡 {u.optimization.action?.split('(')[0]?.trim()} — économie{' '}
                  {fmt(u.optimization.savings_eur)} €/an
                </div>
              )}
            </div>
          ))}
          {/* Légende */}
          <div className="flex gap-3 text-[10px] text-gray-400 mt-2 pt-2 border-t border-gray-100">
            {['HPH', 'HCH', 'HPB', 'HCB'].map((p) => (
              <span key={p}>
                <span
                  className="inline-block w-2 h-2 rounded mr-1"
                  style={{ background: PERIOD_COLORS[p] }}
                />
                {p}
              </span>
            ))}
          </div>
          {costByPeriod.total_optimization_eur > 0 && (
            <div className="mt-2 p-2 bg-green-50 rounded text-[11px] text-green-700 font-medium">
              Économie totale estimée : {fmt(costByPeriod.total_optimization_eur)} €/an par shift
              HP→HC
            </div>
          )}
        </div>
      )}
    </div>
  );
}
