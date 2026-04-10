/**
 * SitesBaselineCard — Conso J-1 vs baseline journalière par site.
 *
 * RÈGLE : display-only. Utilise scopedSites (conso_kwh_an) pour estimer
 * la baseline journalière. TRANSFORMATION DE PRÉSENTATION documentée :
 * baseline_j = conso_kwh_an / 365 (estimation, pas un KPI backend).
 */
import { useScope } from '../../contexts/ScopeContext';

export default function SitesBaselineCard({ consoJ1BySite, consoHierTotal }) {
  const { scopedSites } = useScope();

  if (!scopedSites?.length) return null;

  // TRANSFORMATION DE PRÉSENTATION : conso_kwh_an / 365 = baseline journalière estimée
  const totalConsoAn = scopedSites.reduce((s, site) => s + (site.conso_kwh_an || 0), 0);
  const _hasRealJ1 = consoJ1BySite && Object.keys(consoJ1BySite).length > 0;

  const sites = scopedSites.slice(0, 5).map((site) => {
    const baselineJ = site.conso_kwh_an ? Math.round(site.conso_kwh_an / 365) : null;

    // Données J-1 réelles par site (quand disponibles depuis EMS par site)
    let consoJ1 = consoJ1BySite?.[site.id] ?? null;

    // Fallback : si on a le total J-1 agrégé mais pas par site,
    // répartir proportionnellement MAIS ne pas afficher de delta%
    // (le ratio serait identique pour tous les sites → trompeur)
    let estimated = false;
    if (consoJ1 == null && consoHierTotal > 0 && totalConsoAn > 0 && site.conso_kwh_an > 0) {
      consoJ1 = Math.round((site.conso_kwh_an / totalConsoAn) * consoHierTotal);
      estimated = true;
    }

    // Delta% seulement avec des données réelles par site (pas estimées)
    const deltaPct =
      !estimated && consoJ1 != null && baselineJ
        ? Math.round(((consoJ1 - baselineJ) / baselineJ) * 100)
        : null;
    const isOver = deltaPct != null && deltaPct > 0;

    return { ...site, baselineJ, consoJ1, deltaPct, isOver, estimated };
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
                <span className={site.isOver ? 'text-red-600 font-medium' : 'text-green-700 font-medium'}>
                  {site.consoJ1 != null ? `${site.consoJ1} kWh` : '—'}
                  {site.deltaPct != null ? (
                    <span className="ml-1">
                      · {site.deltaPct > 0 ? '+' : ''}{site.deltaPct}% vs baseline
                    </span>
                  ) : site.estimated ? (
                    <span className="ml-1 text-gray-400"> · estimé</span>
                  ) : null}
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
