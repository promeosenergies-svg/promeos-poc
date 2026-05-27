const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const ACCENTS = ['#2563EB', '#4F46E5', '#DC2626', '#16A34A'];

function KpiCard({ label, value, unit, sub, accent }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: accent }} />
      <div className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{label}</div>
      <div className="text-2xl font-bold mt-1 tracking-tight">
        {value} <span className="text-sm font-normal text-gray-500">{unit}</span>
      </div>
      <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>
    </div>
  );
}

export default function KpiStrip({ dashboard, scopeLevel, sitesCount, totalSurface }) {
  if (!dashboard) return null;
  const { summary, baselines, billing_links } = dashboard;
  const totalKwh = summary?.total_kwh || 0;
  const totalEur = summary?.total_eur || 0;
  // Usage Steering P0 truth-contract (2026-05-27, brief C2) — lecture
  // pure des champs BE qui exposent IPE et surplus € avec contrat de
  // vérité (source/formule/unité/période/confiance dans truth_contract).
  // Avant : Math.round(totalKwh / totalSurface) + Math.round(surplusKwh
  // × priceRef) côté FE → violation doctrine §8.1. Fallback visible "—"
  // si champ manquant (jamais fallback silencieux).
  const ipe = summary?.ipe_kwh_m2 ?? null;
  const surplusKwh = summary?.surplus_kwh ?? null;
  const surplusEur = summary?.surplus_eur ?? null;
  const priceRef = billing_links?.price_ref?.value || 0;
  const degradCount = baselines?.filter((b) => b.trend === 'degradation').length || 0;

  const sitesLabel = scopeLevel === 'site' ? '' : `${sitesCount} sites · `;
  const ipeDisplay = ipe == null ? '—' : `${ipe} kWh/m²`;

  return (
    <div className="px-7 py-4 grid grid-cols-2 lg:grid-cols-4 gap-2.5">
      <KpiCard
        label="Conso totale"
        value={fmt(Math.round(totalKwh / 1000))}
        unit="MWh/an"
        sub={`${sitesLabel}${fmt(totalSurface)} m² · ${ipeDisplay}`}
        accent={ACCENTS[0]}
      />
      <KpiCard
        label="Coût estimé"
        value={fmt(totalEur)}
        unit="€/an"
        sub={`${(priceRef * 100).toFixed(1)} c€/kWh · Prix moyen`}
        accent={ACCENTS[1]}
      />
      <KpiCard
        label="Surconsommation vs N-1"
        value={surplusKwh && surplusKwh > 0 ? `+${fmt(Math.round(surplusKwh / 1000))}` : '0'}
        unit="MWh"
        sub={
          surplusEur && surplusEur > 0
            ? `+${fmt(surplusEur)} €/an · ${degradCount} en dégradation`
            : 'Aucune surconsommation'
        }
        accent={ACCENTS[2]}
      />
      <KpiCard
        label="Écart DT 2030"
        value={(() => {
          const target = baselines?.[0]?.dt_target_kwh_m2;
          if (!target || !totalSurface) return '—';
          const gapMwh = Math.round(((ipe - target) * totalSurface) / 1000);
          return gapMwh > 0 ? `−${fmt(gapMwh)}` : '✓';
        })()}
        unit={baselines?.[0]?.dt_target_kwh_m2 ? 'MWh' : ''}
        sub="Objectif −40% vs 2020"
        accent={ACCENTS[3]}
      />
    </div>
  );
}
