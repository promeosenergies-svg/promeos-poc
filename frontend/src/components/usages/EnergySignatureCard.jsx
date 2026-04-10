const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const fmtDecimal = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 2 });

const QUALITY_BADGE = {
  excellent: { bg: '#F0FDF4', color: '#16A34A', border: '#BBF7D0', label: 'Excellent' },
  bon: { bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE', label: 'Bon' },
  faible: { bg: '#FFFBEB', color: '#D97706', border: '#FDE68A', label: 'Faible' },
};

const VERDICT_STYLES = {
  elevated: { bg: '#FEF2F2', color: '#DC2626', border: '#FECACA', label: 'Élevé' },
  normal: { bg: '#F0FDF4', color: '#16A34A', border: '#BBF7D0', label: 'Conforme' },
};

export default function EnergySignatureCard({ data }) {
  if (!data || data.error || !data.signature) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="text-[13px] font-semibold mb-2">Signature énergétique (DJU)</div>
        <div className="text-[11px] text-gray-500">
          {data?.error ?? 'Données insuffisantes pour calculer la signature.'}
        </div>
      </div>
    );
  }

  const sig = data.signature;
  const bench = data.benchmark || {};
  const savings = data.savings_potential || {};
  const quality = QUALITY_BADGE[sig.model_quality] || QUALITY_BADGE.faible;
  const baseloadVerdict = VERDICT_STYLES[bench.baseload_verdict] || VERDICT_STYLES.normal;
  const thermoVerdict = VERDICT_STYLES[bench.thermo_verdict] || VERDICT_STYLES.normal;

  const totalSavings = savings.total_savings_eur || 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[13px] font-semibold">Signature énergétique (DJU)</div>
        <div
          className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
          style={{
            background: quality.bg,
            color: quality.color,
            border: `1px solid ${quality.border}`,
          }}
        >
          R²&nbsp;{fmtDecimal(sig.r_squared)} · {quality.label}
        </div>
      </div>

      <div className="text-[10px] text-gray-500 mb-3">
        E = a × DJU + b · {data.period_days} jours · archétype {bench.archetype || '?'}
      </div>

      {/* Baseload */}
      <div className="flex items-center justify-between py-1.5 border-b border-gray-100">
        <div>
          <div className="text-[11px] text-gray-500">Baseload (b)</div>
          <div className="text-[10px] text-gray-400">
            Attendu&nbsp;: {fmt(bench.baseload_expected)} kWh/j
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-[13px] font-mono font-semibold">
            {fmt(sig.baseload_kwh_day)} kWh/j
          </div>
          <span
            className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
            style={{
              background: baseloadVerdict.bg,
              color: baseloadVerdict.color,
              border: `1px solid ${baseloadVerdict.border}`,
            }}
          >
            {baseloadVerdict.label}
          </span>
        </div>
      </div>

      {/* Thermosensibilité */}
      <div className="flex items-center justify-between py-1.5 border-b border-gray-100">
        <div>
          <div className="text-[11px] text-gray-500">Thermosensibilité (a)</div>
          <div className="text-[10px] text-gray-400">
            Attendu&nbsp;: {fmtDecimal(bench.thermo_expected)} kWh/DJU
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-[13px] font-mono font-semibold">
            {fmtDecimal(sig.thermosensitivity_kwh_dju)} kWh/DJU
          </div>
          <span
            className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
            style={{
              background: thermoVerdict.bg,
              color: thermoVerdict.color,
              border: `1px solid ${thermoVerdict.border}`,
            }}
          >
            {thermoVerdict.label}
          </span>
        </div>
      </div>

      {/* Verdict / potentiel économie */}
      {totalSavings > 0 ? (
        <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs">
          <div className="font-medium text-amber-800">
            Potentiel d'économie&nbsp;: {fmt(totalSavings)} €/an
          </div>
          <div className="text-[10px] text-amber-700 mt-0.5">
            Baseload excès&nbsp;: {fmt(savings.baseload_excess_eur_year)} € · Thermo excès&nbsp;:{' '}
            {fmt(savings.thermo_excess_eur_year)} €
          </div>
        </div>
      ) : (
        <div className="mt-3 p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-[11px] text-gray-600">
          Signature conforme au benchmark archétype. Pas d'excès détecté.
        </div>
      )}
    </div>
  );
}
