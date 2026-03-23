/**
 * SitesBaselineCard — Conso J-1 vs baseline journalière par site.
 *
 * RÈGLE : display-only. Utilise scopedSites (conso_kwh_an) pour estimer
 * la baseline journalière. TRANSFORMATION DE PRÉSENTATION documentée :
 * baseline_j = conso_kwh_an / 365 (estimation, pas un KPI backend).
 */
import { useScope } from '../../contexts/ScopeContext';

export default function SitesBaselineCard({ consoJ1BySite }) {
  const { scopedSites } = useScope();

  if (!scopedSites?.length) return null;

  // TRANSFORMATION DE PRÉSENTATION : conso_kwh_an / 365 = baseline journalière estimée
  const sites = scopedSites.slice(0, 5).map((site) => {
    const baselineJ = site.conso_kwh_an ? Math.round(site.conso_kwh_an / 365) : null;
    const consoJ1 = consoJ1BySite?.[site.id] ?? null;
    const deltaPct =
      consoJ1 != null && baselineJ ? Math.round(((consoJ1 - baselineJ) / baselineJ) * 100) : null;
    const isOver = deltaPct != null && deltaPct > 0;

    return { ...site, baselineJ, consoJ1, deltaPct, isOver };
  });

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4" data-testid="sites-baseline">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
        Sites — Conso J-1 vs baseline (kWh/j)
      </div>

      <div className="space-y-3">
        {sites.map((site) => {
          const maxVal = Math.max(site.consoJ1 ?? 0, site.baselineJ ?? 0, 1);
          const fillPct =
            site.consoJ1 != null ? Math.min(100, Math.round((site.consoJ1 / maxVal) * 100)) : 0;
          const baselinePct =
            site.baselineJ != null ? Math.min(100, Math.round((site.baselineJ / maxVal) * 100)) : 0;

          return (
            <div key={site.id}>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-gray-700">{site.nom}</span>
                <span
                  className={
                    site.isOver ? 'text-red-600 font-medium' : 'text-green-700 font-medium'
                  }
                >
                  {site.consoJ1 != null ? `${site.consoJ1} kWh` : '—'}
                  {site.deltaPct != null && (
                    <span className="ml-1">
                      · {site.deltaPct > 0 ? '+' : ''}
                      {site.deltaPct}% vs baseline
                    </span>
                  )}
                </span>
              </div>
              <div className="relative h-2 bg-gray-100 rounded-full overflow-visible">
                <div
                  className={`h-full rounded-full ${site.isOver ? 'bg-red-500' : 'bg-teal-500'}`}
                  style={{ width: `${fillPct}%` }}
                />
                {site.baselineJ != null && (
                  <div
                    className="absolute top-[-2px] w-0.5 h-3 bg-blue-800 rounded"
                    style={{ left: `${baselinePct}%` }}
                    title={`Baseline : ${site.baselineJ} kWh/j`}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
