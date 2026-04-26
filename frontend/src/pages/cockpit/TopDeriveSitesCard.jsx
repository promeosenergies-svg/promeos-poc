/**
 * TopDeriveSitesCard — top 5 sites du périmètre triés par risque réglementaire,
 * format liste cliquable avec MWh + €.
 *
 * Display-only : sort sur `risque_eur` (déjà chargé en scope, pas un calcul
 * métier — la valeur vient du backend KpiService). À déplacer côté backend
 * si le scope dépasse 500 sites pour éviter le coût client.
 */
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle } from 'lucide-react';
import { fmtEur, fmtKwh } from '../../utils/format';

export default function TopDeriveSitesCard({ sites = [], totalSites }) {
  const navigate = useNavigate();

  const top5 = useMemo(() => {
    const valid = (sites ?? []).filter((s) => s && s.id);
    return valid
      .slice()
      .sort((a, b) => (b.risque_eur ?? 0) - (a.risque_eur ?? 0))
      .slice(0, 5);
  }, [sites]);

  const sitesEnDerive = top5.filter((s) => (s.risque_eur ?? 0) > 0).length;

  if (top5.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-3" data-testid="top-derive-sites-empty">
        <div className="text-xs text-gray-500 mb-1">Top 5 sites en dérive</div>
        <div className="text-xs text-gray-400">Aucun site dans le périmètre.</div>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg p-3 border-amber-200" data-testid="top-derive-sites">
      <div className="flex items-baseline justify-between mb-2">
        <div className="text-xs font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
          {sitesEnDerive > 0 && (
            <AlertTriangle size={11} className="text-amber-500" aria-hidden="true" />
          )}
          Top 5 sites en dérive
        </div>
        <button
          type="button"
          onClick={() => navigate('/patrimoine')}
          className="text-[11px] text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          Voir les {totalSites ?? sites.length} sites
          <ArrowRight size={11} aria-hidden="true" />
        </button>
      </div>

      <ul className="divide-y divide-gray-100">
        {top5.map((site, idx) => {
          const risk = site.risque_eur ?? 0;
          const isDerive = risk > 0;
          return (
            <li key={site.id}>
              <button
                type="button"
                onClick={() => navigate(`/sites/${site.id}`)}
                className="w-full flex items-center justify-between gap-3 py-1.5 text-left hover:bg-blue-50/40 -mx-1 px-1 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <span className="flex items-center gap-2 min-w-0 flex-1">
                  <span
                    className={`shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-semibold ${
                      isDerive ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                    }`}
                    aria-hidden="true"
                  >
                    {idx + 1}
                  </span>
                  <span className="text-xs font-medium text-gray-900 truncate">{site.nom}</span>
                </span>
                <span className="shrink-0 flex items-baseline gap-2 text-xs">
                  <span className="text-gray-500">{fmtKwh(site.conso_kwh_an)}</span>
                  <span
                    className={`font-semibold ${isDerive ? 'text-amber-700' : 'text-gray-400'}`}
                  >
                    {fmtEur(risk)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="text-[10px] text-gray-400 mt-1">
        Tri : risque réglementaire € décroissant · cliquer pour le détail site
      </div>
    </div>
  );
}
