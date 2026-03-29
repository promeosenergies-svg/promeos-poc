/**
 * PerformanceSitesCard — Performance par site en kWh/m² vs benchmark OID.
 *
 * Source primaire : GET /api/cockpit/benchmark (backend)
 * Fallback V2 : calcul depuis scopedSites (surface_m2 + conso_kwh_an)
 */
import { useState, useEffect, useMemo } from 'react';
import { getCockpitBenchmark } from '../../services/api';
import { useScope } from '../../contexts/ScopeContext';
import { Skeleton } from '../../ui';

// Benchmarks OID par usage (kWh/m²/an)
const OID_BENCHMARKS = {
  bureaux: 146,
  hotel: 170,
  ecole: 110,
  entrepot: 80,
  commerce: 200,
  industrie: 180,
  logistique: 90,
  default: 146,
};

function getBenchmarkForUsage(usageType) {
  if (!usageType) return OID_BENCHMARKS.default;
  const key = usageType.toLowerCase().replace(/[^a-z]/g, '');
  return OID_BENCHMARKS[key] ?? OID_BENCHMARKS.default;
}

// Couleur sémantique selon écart à la référence
function getBarColor(ipe, objectif) {
  if (ipe == null || objectif == null) return { bar: 'bg-gray-300', text: 'text-gray-500' };
  const ratio = ipe / objectif;
  if (ratio <= 1) return { bar: 'bg-emerald-500', text: 'text-emerald-700' };
  if (ratio <= 1.2) return { bar: 'bg-amber-500', text: 'text-amber-700' };
  return { bar: 'bg-red-500', text: 'text-red-600' };
}

function SitePerformanceBar({ site, maxVal }) {
  const { site_nom, ipe_kwh_m2_an, objectif } = site;
  const color = getBarColor(ipe_kwh_m2_an, objectif);
  const fillPct =
    ipe_kwh_m2_an != null ? Math.min(100, Math.round((ipe_kwh_m2_an / maxVal) * 100)) : 0;
  const targetPct = Math.min(100, Math.round((objectif / maxVal) * 100));

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-gray-700 truncate">{site_nom}</span>
        <span className={`font-medium shrink-0 ml-2 ${color.text}`}>
          {ipe_kwh_m2_an ?? '—'} kWh/m² · réf. {objectif}
        </span>
      </div>
      <div className="relative h-2.5 bg-gray-100 rounded-full overflow-visible">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color.bar}`}
          style={{ width: `${fillPct}%` }}
        />
        <div
          className="absolute top-[-2px] w-0.5 h-3.5 bg-blue-800 rounded"
          style={{ left: `${targetPct}%` }}
          title={`Cible OID : ${objectif} kWh/m²`}
        />
      </div>
    </div>
  );
}

export default function PerformanceSitesCard({ fallbackSites }) {
  const { org } = useScope();
  const [apiSites, setApiSites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!org?.id) return;
    setApiSites([]);
    setLoading(true);
    getCockpitBenchmark()
      .then((data) => setApiSites(data?.sites ?? []))
      .catch(() => setApiSites([]))
      .finally(() => setLoading(false));
  }, [org?.id]);

  // V2: fallback — calculer IPE depuis scopedSites si l'API ne retourne rien
  const sites = useMemo(() => {
    if (apiSites.length > 0) {
      return apiSites.map((s) => ({
        site_id: s.site_id,
        site_nom: s.site_nom,
        ipe_kwh_m2_an: s.ipe_kwh_m2_an,
        objectif: s.benchmark?.median ?? s.benchmark?.bon ?? getBenchmarkForUsage(s.usage_type),
      }));
    }
    if (!fallbackSites?.length) return [];
    return fallbackSites
      .filter((s) => s.surface_m2 > 0 && s.conso_kwh_an > 0)
      .map((s) => ({
        site_id: s.id,
        site_nom: s.nom || s.name || `Site #${s.id}`,
        ipe_kwh_m2_an: Math.round(s.conso_kwh_an / s.surface_m2),
        objectif: getBenchmarkForUsage(s.usage_type ?? s.activite),
      }))
      .sort((a, b) => b.ipe_kwh_m2_an - a.ipe_kwh_m2_an);
  }, [apiSites, fallbackSites]);

  const maxVal = useMemo(
    () => Math.max(...sites.map((s) => s.ipe_kwh_m2_an ?? 0), ...sites.map((s) => s.objectif), 1),
    [sites]
  );

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4" data-testid="performance-sites">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
        Performance par site — kWh/m²
      </div>

      {loading && apiSites.length === 0 && !fallbackSites?.length ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-8 rounded" />
          ))}
        </div>
      ) : sites.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">
          Surface ou consommation manquante pour le calcul kWh/m².
        </p>
      ) : (
        <>
          {sites.slice(0, 5).map((site) => (
            <SitePerformanceBar key={site.site_id} site={site} maxVal={maxVal} />
          ))}
          <p className="text-[10px] text-gray-400 mt-2">
            <span className="inline-block w-0.5 h-2.5 bg-blue-800 rounded mr-1 align-middle" />
            Cible OID par usage · Vert = sous la cible · Ambre = au-dessus
          </p>
        </>
      )}
    </div>
  );
}
