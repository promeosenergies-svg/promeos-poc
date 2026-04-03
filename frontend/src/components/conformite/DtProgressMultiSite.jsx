/**
 * DtProgressMultiSite — Vue comparatif trajectoire DT pour tous les sites
 *
 * REGLE ABSOLUE : zero calcul metier. Display-only.
 * Toutes les valeurs viennent de GET /api/tertiaire/portfolio/{orgId}/dt-progress
 *
 * Jalons affiches : -40% 2030 / -50% 2040 / -60% 2050 (officiels uniquement)
 * Source : Decret n°2019-771 du 23/07/2019
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
import { getPortfolioDtProgress } from '../../services/api';

const STATUS_CONFIG = {
  on_track: { label: 'En trajectoire', cls: 'bg-green-100 text-green-800', bar: 'bg-green-500' },
  off_track: { label: 'En retard', cls: 'bg-red-100 text-red-800', bar: 'bg-red-500' },
  no_data: { label: 'Sans données', cls: 'bg-gray-100 text-gray-500', bar: 'bg-gray-300' },
};

function ProgressBar({ reductionPct, cible = 40 }) {
  if (reductionPct == null) return <div className="h-2 w-full bg-gray-100 rounded" />;
  const pct = Math.max(0, Math.min(100, (reductionPct / cible) * 100));
  const ok = reductionPct >= cible;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded overflow-hidden">
        <div
          className={`h-full rounded transition-all ${ok ? 'bg-green-500' : 'bg-red-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-xs font-medium tabular-nums ${ok ? 'text-green-700' : 'text-red-600'}`}
      >
        {reductionPct >= 0 ? '-' : '+'}
        {Math.abs(reductionPct).toFixed(1)}%
      </span>
    </div>
  );
}

export default function DtProgressMultiSite({ orgId }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!orgId) return;
    let stale = false;
    setLoading(true);
    getPortfolioDtProgress(orgId)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch(() => {
        if (!stale) setData(null);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [orgId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 py-6">
        <Loader2 size={14} className="animate-spin" /> Chargement trajectoire DT multi-sites...
      </div>
    );
  }
  if (!data || !data.sites?.length) return null;

  const cible = data.jalons_officiels?.[0]?.reduction_cible_pct || 40;

  return (
    <div className="space-y-3" data-testid="dt-progress-multi-site">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">
            Trajectoire Décret Tertiaire — Vue multi-sites
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Jalons officiels : -40% 2030 · -50% 2040 · -60% 2050
            <span className="ml-1 text-gray-400">Décret n°2019-771</span>
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            {data.n_on_track} en trajectoire
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            {data.n_off_track} en retard
          </span>
          {data.n_no_data > 0 && (
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-300" />
              {data.n_no_data} sans données
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600 text-xs">
              <th className="text-left px-3 py-2 font-medium">Site</th>
              <th className="text-right px-3 py-2 font-medium w-20">Surface</th>
              <th className="text-left px-3 py-2 font-medium w-48">Réduction vs réf.</th>
              <th className="text-center px-3 py-2 font-medium w-16">Obj.</th>
              <th className="text-center px-3 py-2 font-medium w-28">Statut</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.sites.map((site) => {
              const cfg = STATUS_CONFIG[site.status] || STATUS_CONFIG.no_data;
              return (
                <tr key={site.site_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-3 py-2.5">
                    <span className="font-medium text-gray-900">{site.site_nom}</span>
                    {site.is_dju_applied && (
                      <span
                        className="ml-1.5 text-[10px] px-1 py-0.5 bg-blue-50 text-blue-600 rounded font-medium"
                        title="Correction DJU appliquée (normalisation OPERAT)"
                      >
                        DJU
                      </span>
                    )}
                  </td>
                  <td className="text-right px-3 py-2.5 text-gray-600 tabular-nums">
                    {site.surface_m2?.toLocaleString('fr-FR')} m²
                  </td>
                  <td className="px-3 py-2.5">
                    <ProgressBar reductionPct={site.reduction_pct} cible={cible} />
                  </td>
                  <td className="text-center px-3 py-2.5 text-gray-500 text-xs">-{cible}%</td>
                  <td className="text-center px-3 py-2.5">
                    <span
                      className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${cfg.cls}`}
                    >
                      {cfg.label}
                    </span>
                  </td>
                  <td className="px-2 py-2.5">
                    <button
                      onClick={() => navigate(`/conformite/tertiaire`)}
                      className="text-gray-400 hover:text-gray-700"
                      title="Détail"
                    >
                      <ArrowRight size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
