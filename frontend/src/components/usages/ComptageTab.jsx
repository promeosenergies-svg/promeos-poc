const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const VECTOR_ICON = { ELECTRICITY: '⚡', GAS: '🔥', HEAT: '♨️', WATER: '💧' };
const SRC_CLS = {
  mesure_directe: 'bg-green-50 text-green-700',
  estimation_prorata: 'bg-amber-50 text-amber-700',
};

export default function ComptageTab({ data }) {
  if (!data?.meters?.length)
    return <div className="p-6 text-sm text-gray-400 italic">Aucun compteur configuré.</div>;

  return (
    <div className="p-5 text-xs">
      {data.meters.map((meter) => (
        <div key={meter.id || meter.meter_id} className="mb-4">
          <div className="flex items-center gap-2 font-semibold py-2">
            <span>{VECTOR_ICON[meter.energy_vector] || '⚡'}</span>
            <span>{meter.meter_id || meter.name}</span>
            <span className="ml-auto font-mono">{fmt(meter.kwh)} kWh</span>
          </div>
          {meter.sub_meters?.map((sub) => (
            <div key={sub.id} className="flex items-center gap-2 py-1 pl-5 text-gray-500">
              <span>↳</span>
              <span>{sub.name || sub.usage?.label || 'Sous-compteur'}</span>
              <span
                className={`text-[8px] px-1.5 py-0.5 rounded font-semibold ${SRC_CLS[sub.data_source] || 'bg-gray-100 text-gray-500'}`}
              >
                {sub.data_source === 'mesure_directe' ? 'Mesuré' : 'Estimé'}
              </span>
              <div className="flex-1 h-1 bg-gray-100 rounded max-w-[100px]">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${sub.pct_of_principal || 0}%`,
                    background: sub.usage?.color || '#94a3b8',
                  }}
                />
              </div>
              <span className="font-mono text-[10px]">
                {fmt(sub.kwh)} (
                {sub.pct_of_principal ? `${Math.round(sub.pct_of_principal)}%` : '—'})
              </span>
            </div>
          ))}
          {meter.delta_kwh > 0 && (
            <div className="flex items-center gap-2 py-1 pl-5 text-gray-400">
              <span>↳</span>
              <span>Pertes & communs</span>
              <div className="flex-1 h-1 bg-gray-100 rounded max-w-[100px]">
                <div
                  className="h-full rounded bg-gray-300"
                  style={{ width: `${meter.delta_pct || 0}%` }}
                />
              </div>
              <span className="font-mono text-[10px]">
                {fmt(meter.delta_kwh)} ({meter.delta_pct ? `${Math.round(meter.delta_pct)}%` : '—'})
              </span>
            </div>
          )}
          <div className="text-[10px] text-gray-400 py-1">
            Couverture : {meter.coverage_pct ? `${Math.round(meter.coverage_pct)}%` : '—'}
          </div>
        </div>
      ))}
    </div>
  );
}
