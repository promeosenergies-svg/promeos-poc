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

export default function CostCard({ data }) {
  if (!data?.by_usage?.length) return null;

  const maxEur = Math.max(...data.by_usage.map((u) => u.eur || 0));
  const priceRef = data.price_ref_eur_kwh || 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[13px] font-semibold">Coût par usage</span>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-500">
          {(priceRef * 100).toFixed(1)} c€/kWh
        </span>
      </div>
      {data.by_usage.slice(0, 5).map((u) => {
        const pct = maxEur > 0 ? (u.eur / maxEur) * 100 : 0;
        return (
          <div key={u.label || u.type} className="flex items-center gap-2 py-1">
            <div className="w-[80px] text-[11px] font-medium truncate">{u.label || u.type}</div>
            <div className="flex-1 h-3.5 bg-gray-100 rounded overflow-hidden">
              <div
                className="h-full rounded"
                style={{ width: `${pct}%`, background: COLORS[u.label] || '#BDBDBD' }}
              />
            </div>
            <div className="min-w-[90px] text-right text-[10px] text-gray-500 font-mono">
              {fmt(u.eur)} € ({u.pct_of_total ? Math.round(u.pct_of_total) : 0}%)
            </div>
          </div>
        );
      })}
    </div>
  );
}
