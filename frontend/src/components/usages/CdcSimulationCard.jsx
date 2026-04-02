const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const RISK_STYLES = {
  faible: 'bg-green-50 text-green-700',
  modéré: 'bg-amber-50 text-amber-700',
  élevé: 'bg-red-50 text-red-700',
};

export default function CdcSimulationCard({ data }) {
  if (!data || data.error || !data.strategies?.length || !data.cdc_profile) return null;

  const profile = data.cdc_profile;
  const reco = data.recommendation;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="text-[13px] font-semibold mb-1">Simulation achat CDC</div>
      <div className="text-[10px] text-gray-400 mb-3">
        Profil : {profile?.type?.replace(/_/g, ' ') ?? '—'} · Baseload{' '}
        {profile?.baseload_ratio != null ? (profile.baseload_ratio * 100).toFixed(0) : '—'}% · HP{' '}
        {profile?.hp_ratio != null ? (profile.hp_ratio * 100).toFixed(0) : '—'}%
      </div>

      {/* Tableau compact */}
      <table className="w-full text-[11px] mb-3">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500">
            <th className="text-left py-1 font-medium">Stratégie</th>
            <th className="text-right py-1 font-medium">Coût/an</th>
            <th className="text-center py-1 font-medium">Risque</th>
          </tr>
        </thead>
        <tbody>
          {data.strategies.map((s) => (
            <tr
              key={s.name}
              className={`border-b border-gray-50 ${
                s.name === reco.strategy ? 'bg-green-50/50' : ''
              }`}
            >
              <td className="py-1.5">
                {s.name}
                {s.name === reco.strategy && (
                  <span className="ml-1 text-[9px] bg-green-100 text-green-700 px-1 py-0.5 rounded">
                    Reco
                  </span>
                )}
              </td>
              <td className="text-right py-1.5 font-mono">{fmt(s.cost_eur_year)} €</td>
              <td className="text-center py-1.5">
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded ${RISK_STYLES[s.risk_level] || ''}`}
                >
                  {s.risk_level}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Recommandation */}
      <div className="p-2 bg-green-50 border border-green-200 rounded-lg text-[11px] text-green-700">
        <div className="font-medium">{reco.strategy}</div>
        <div className="mt-0.5 text-green-600">{reco.reasoning}</div>
        {reco.savings_vs_fixe_eur > 0 && (
          <div className="font-medium mt-1">
            Économie : {fmt(reco.savings_vs_fixe_eur)} €/an vs fixe
          </div>
        )}
      </div>
    </div>
  );
}
