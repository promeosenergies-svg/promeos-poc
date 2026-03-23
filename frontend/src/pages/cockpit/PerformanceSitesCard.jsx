/**
 * PerformanceSitesCard — Performance par site en kWh/m² vs benchmark ADEME.
 *
 * RÈGLE : zéro calcul métier. Les données viennent de GET /api/cockpit/benchmark.
 * Le composant affiche — ne calcule pas.
 */
import { useState, useEffect } from 'react';
import { getCockpitBenchmark } from '../../services/api';
import { Skeleton } from '../../ui';

function SitePerformanceBar({ site }) {
  const { site_nom, ipe_kwh_m2_an, benchmark } = site;
  const objectif = benchmark?.median ?? benchmark?.bon ?? 120;
  const isOver = ipe_kwh_m2_an != null && ipe_kwh_m2_an > objectif;
  const maxVal = Math.max(ipe_kwh_m2_an ?? 0, objectif, 1);
  const fillPct =
    ipe_kwh_m2_an != null ? Math.min(100, Math.round((ipe_kwh_m2_an / maxVal) * 100)) : 0;
  const targetPct = Math.min(100, Math.round((objectif / maxVal) * 100));

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-gray-700">{site_nom}</span>
        <span className={isOver ? 'text-red-600 font-medium' : 'text-green-700 font-medium'}>
          {ipe_kwh_m2_an ?? '—'} kWh/m² · obj. {objectif}
        </span>
      </div>
      <div className="relative h-2 bg-gray-100 rounded-full overflow-visible">
        <div
          className={`h-full rounded-full ${isOver ? 'bg-red-500' : 'bg-blue-500'}`}
          style={{ width: `${fillPct}%` }}
        />
        <div
          className="absolute top-[-2px] w-0.5 h-3 bg-blue-800 rounded"
          style={{ left: `${targetPct}%` }}
          title={`Objectif : ${objectif} kWh/m²`}
        />
      </div>
    </div>
  );
}

export default function PerformanceSitesCard() {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCockpitBenchmark()
      .then((data) => setSites(data?.sites ?? []))
      .catch(() => setSites([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4" data-testid="performance-sites">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
        Performance par site — kWh/m²
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-8 rounded" />
          ))}
        </div>
      ) : sites.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">Données benchmark non disponibles.</p>
      ) : (
        sites.slice(0, 5).map((site) => <SitePerformanceBar key={site.site_id} site={site} />)
      )}
    </div>
  );
}
