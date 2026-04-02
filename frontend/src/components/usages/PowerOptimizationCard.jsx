const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const SHIFT_COLOR = '#16A34A';
const FIXED_COLOR = '#9CA3AF';

export default function PowerOptimizationCard({ data }) {
  if (!data || data.error || !data.current_situation) return null;

  const cs = data.current_situation;
  const opt = data.optimization;
  const decomp = data.peak_decomposition || [];

  const utilizationPct = Math.min(cs.utilization_pct, 100);
  const isOverloaded = cs.actual_peak_kw > cs.subscribed_power_kva;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="text-[13px] font-semibold mb-2">Optimisation puissance souscrite</div>

      {/* Jauge PS */}
      <div className="flex items-center gap-3 mb-3">
        <div className="text-[10px] text-gray-500 w-16">PS actuelle</div>
        <div className="flex-1 h-4 bg-gray-100 rounded relative overflow-visible">
          <div
            className="h-full rounded"
            style={{
              width: `${Math.min(utilizationPct, 100)}%`,
              background: isOverloaded ? '#EF4444' : '#3B82F6',
            }}
          />
          {isOverloaded && (
            <div
              className="absolute top-0 h-full bg-red-300 rounded-r opacity-50"
              style={{
                left: `${(cs.subscribed_power_kva / cs.actual_peak_kw) * 100}%`,
                width: `${100 - (cs.subscribed_power_kva / cs.actual_peak_kw) * 100}%`,
              }}
            />
          )}
        </div>
        <div className="text-[10px] font-mono w-28 text-right whitespace-nowrap">
          {fmt(cs.actual_peak_kw)} / {fmt(cs.subscribed_power_kva)} kVA
        </div>
      </div>

      {/* Info pointe */}
      <div className="text-[10px] text-gray-500 mb-2">
        Pointe : {cs.peak_weekday} {cs.peak_hour}h · {cs.tariff_option || '?'} · {cs.price_kva_an}{' '}
        €/kVA/an
      </div>

      {/* Décomposition pointe — mini barres */}
      <div className="text-[10px] text-gray-500 mb-1 font-medium">Décomposition de la pointe</div>
      {decomp.map((d) => (
        <div key={d.usage} className="flex items-center gap-2 py-0.5">
          <span className="w-24 text-[10px] truncate">{d.usage}</span>
          <div className="flex-1 h-2.5 bg-gray-100 rounded overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: `${d.pct}%`,
                background: d.shiftable ? SHIFT_COLOR : FIXED_COLOR,
              }}
            />
          </div>
          <span className="text-[10px] font-mono w-16 text-right">{fmt(d.kw)} kW</span>
          {d.shiftable && <span className="text-[10px] text-green-600">↻</span>}
        </div>
      ))}

      {/* Légende */}
      <div className="flex gap-3 text-[10px] text-gray-400 mt-1.5 mb-2">
        <span>
          <span className="inline-block w-2 h-2 rounded mr-1" style={{ background: SHIFT_COLOR }} />
          Décalable
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded mr-1" style={{ background: FIXED_COLOR }} />
          Fixe
        </span>
      </div>

      {/* Recommandation */}
      {opt && opt.net_savings_eur > 0 ? (
        <div className="p-2.5 bg-green-50 border border-green-200 rounded-lg text-xs">
          <div className="font-medium text-green-800">
            PS réductible : {fmt(cs.subscribed_power_kva)} → {fmt(opt.recommended_ps_kva)} kVA
          </div>
          <div className="text-green-600 mt-0.5">{opt.strategy}</div>
          <div className="font-medium text-green-700 mt-1">
            Économie nette : {fmt(opt.net_savings_eur)} €/an
          </div>
          {opt.cmdps_estimated_eur > 0 && (
            <div className="text-[10px] text-gray-500 mt-0.5">
              CMDPS résiduel estimé : {fmt(opt.cmdps_estimated_eur)} €/an
            </div>
          )}
        </div>
      ) : isOverloaded ? (
        <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          <strong>Attention :</strong> pointe réelle ({fmt(cs.actual_peak_kw)} kW) dépasse la PS (
          {fmt(cs.subscribed_power_kva)} kVA). Risque de pénalités CMDPS.
        </div>
      ) : (
        <div className="p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600">
          PS correctement dimensionnée. Marge : {fmt(cs.margin_kw)} kW (
          {(100 - cs.utilization_pct).toFixed(0)}%)
        </div>
      )}
    </div>
  );
}
