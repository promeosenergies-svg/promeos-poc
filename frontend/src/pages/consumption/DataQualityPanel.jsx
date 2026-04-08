/**
 * PROMEOS — DataQualityPanel (EMS Tier 1)
 * Affiche le score de fraîcheur données + tableau compteurs.
 * Colonnes : Compteur, Dernière relève, Trous, Complétude%, Score
 */
import { useState, useEffect } from 'react';
import { Activity, Loader2, AlertTriangle, CheckCircle2, AlertCircle } from 'lucide-react';
import { getEmsDataQuality } from '../../services/api/ems';
import DataQualityBadge from '../../components/DataQualityBadge';

const STATUS_ICON = {
  ok: { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50' },
  warning: { icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-50' },
  critical: { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50' },
};

function StatusBadge({ status }) {
  const cfg = STATUS_ICON[status] || STATUS_ICON.critical;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}
    >
      <Icon size={12} />
      {status === 'ok' ? 'OK' : status === 'warning' ? 'Attention' : 'Critique'}
    </span>
  );
}

export default function DataQualityPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getEmsDataQuality(siteId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Erreur chargement qualité données');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  if (!siteId) {
    return (
      <div className="text-center py-8">
        <Activity size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">
          Sélectionnez un site pour voir la qualité des données.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-gray-500">Analyse qualité données...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <AlertTriangle size={24} className="mx-auto text-red-400 mb-2" />
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      {/* En-tête avec score global */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <Activity size={16} className="text-blue-600" />
          Qualité des données
        </h3>
        <div className="flex items-center gap-3">
          <StatusBadge status={data.status_global} />
          <DataQualityBadge score={data.score_global} size="md" />
        </div>
      </div>

      {/* Barre de progression globale */}
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            data.score_global >= 80
              ? 'bg-green-500'
              : data.score_global >= 50
                ? 'bg-amber-500'
                : 'bg-red-500'
          }`}
          style={{ width: `${data.score_global}%` }}
        />
      </div>

      {/* Tableau compteurs */}
      {data.meters?.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                  Compteur
                </th>
                <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                  Dernière relève
                </th>
                <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                  Trous
                </th>
                <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                  Complétude
                </th>
                <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                  Score
                </th>
              </tr>
            </thead>
            <tbody>
              {data.meters.map((m) => (
                <tr
                  key={m.meter_id}
                  className="border-b border-gray-50 hover:bg-gray-50 transition"
                >
                  <td className="py-2 px-3">
                    <div>
                      <span className="font-medium text-gray-800">{m.name}</span>
                      <span className="ml-2 text-xs text-gray-400">{m.meter_ref}</span>
                    </div>
                  </td>
                  <td className="py-2 px-3 text-gray-600">
                    {m.last_reading ? (
                      new Date(m.last_reading).toLocaleDateString('fr-FR')
                    ) : (
                      <span className="text-red-500">Aucune</span>
                    )}
                    {m.delay_days > 2 && m.delay_days < 999 && (
                      <span className="ml-1 text-xs text-amber-500">({m.delay_days}j)</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <span className={m.gaps > 0 ? 'text-amber-600 font-medium' : 'text-gray-500'}>
                      {m.gaps}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <span
                      className={`font-medium ${
                        m.completeness_pct >= 80
                          ? 'text-green-600'
                          : m.completeness_pct >= 50
                            ? 'text-amber-600'
                            : 'text-red-600'
                      }`}
                    >
                      {m.completeness_pct.toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <DataQualityBadge score={m.score} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-500 text-center py-4">
          Aucun compteur actif trouvé pour ce site.
        </p>
      )}
    </div>
  );
}
