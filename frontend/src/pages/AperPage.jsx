/**
 * PROMEOS — AperPage (Step 29)
 * Page dédiée Loi APER : sites éligibles, estimation production PV, timeline.
 */
import { useState, useEffect } from 'react';
import { Sun, MapPin, Calendar, Zap, Leaf, Euro, ChevronRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Explain, KpiCardInline } from '../ui';
import ErrorState from '../ui/ErrorState'; // eslint-disable-line no-unused-vars
import { getAperDashboard, getAperEstimate } from '../services/api';

const MONTH_LABELS = [
  'Jan',
  'Fev',
  'Mar',
  'Avr',
  'Mai',
  'Juin',
  'Jul',
  'Aou',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

const APER_COLORS = {
  blue: { iconBg: 'bg-blue-50', color: 'text-blue-700' },
  emerald: { iconBg: 'bg-emerald-50', color: 'text-emerald-700' },
  amber: { iconBg: 'bg-amber-50', color: 'text-amber-700' },
  red: { iconBg: 'bg-red-50', color: 'text-red-700' },
};

function fmt(val) {
  if (val == null) return '--';
  return val.toLocaleString('fr-FR');
}

function DeadlineBadge({ deadline }) {
  if (!deadline) return null;
  const d = new Date(deadline);
  const now = new Date();
  const months = Math.round((d - now) / (1000 * 60 * 60 * 24 * 30));
  const color =
    months < 6
      ? 'bg-red-50 text-red-700'
      : months < 18
        ? 'bg-amber-50 text-amber-700'
        : 'bg-emerald-50 text-emerald-700';
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${color}`}>
      {d.toLocaleDateString('fr-FR')}
    </span>
  );
}

export default function AperPage() {
  const { isExpert } = useExpertMode();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [_selectedSite, setSelectedSite] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);

  useEffect(() => {
    setLoading(true);
    getAperDashboard()
      .then(setDashboard)
      .catch((e) => setError(e.message || 'Erreur chargement'))
      .finally(() => setLoading(false));
  }, []);

  const handleEstimate = (site, surfaceType) => {
    setSelectedSite({ ...site, surfaceType });
    setEstimating(true);
    setEstimate(null);
    getAperEstimate(site.site_id, { surface_type: surfaceType })
      .then(setEstimate)
      .catch(() => setEstimate({ error: 'Estimation indisponible' }))
      .finally(() => setEstimating(false));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <Sun className="w-12 h-12 text-amber-400 mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Solarisation — Loi APER</h2>
        <p className="text-sm text-gray-500 mb-4">
          Les données de solarisation ne sont pas encore disponibles pour votre périmètre.
        </p>
        <p className="text-xs text-gray-400">
          Importez votre patrimoine immobilier avec les surfaces de parkings et toitures pour
          activer l'analyse APER.
        </p>
      </div>
    );
  }

  const allSites = [
    ...(dashboard?.parking?.sites || []).map((s) => ({
      ...s,
      type: 'Parking',
      surfaceType: 'parking',
    })),
    ...(dashboard?.roof?.sites || []).map((s) => ({ ...s, type: 'Toiture', surfaceType: 'roof' })),
  ];

  const monthlyData =
    estimate?.monthly_kwh?.map((kwh, i) => ({
      month: MONTH_LABELS[i],
      kwh: kwh,
    })) || [];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Sun className="w-6 h-6 text-amber-500" />
            <Explain term="aper">Solarisation — Loi APER</Explain>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Parkings et toitures éligibles à l'obligation de solarisation
          </p>
        </div>
        {dashboard?.total_eligible_sites > 0 && (
          <span className="px-3 py-1 text-sm font-semibold rounded-full bg-amber-50 text-amber-700 ring-1 ring-amber-200">
            {dashboard.total_eligible_sites} site{dashboard.total_eligible_sites > 1 ? 's' : ''}{' '}
            éligible{dashboard.total_eligible_sites > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCardInline
          icon={MapPin}
          label="Sites éligibles"
          value={dashboard?.total_eligible_sites || 0}
          unit="sites"
          {...APER_COLORS.blue}
        />
        <KpiCardInline
          icon={Sun}
          label="Surface parking"
          value={fmt(dashboard?.parking?.total_surface_m2 || 0)}
          unit="m²"
          {...APER_COLORS.amber}
        />
        <KpiCardInline
          icon={Sun}
          label="Surface toiture"
          value={fmt(dashboard?.roof?.total_surface_m2 || 0)}
          unit="m²"
          {...APER_COLORS.emerald}
        />
        <KpiCardInline
          icon={Calendar}
          label="Prochaine échéance"
          value={
            dashboard?.next_deadline
              ? new Date(dashboard.next_deadline).toLocaleDateString('fr-FR')
              : '--'
          }
          {...(dashboard?.next_deadline &&
          new Date(dashboard.next_deadline) < new Date(Date.now() + 180 * 86400000)
            ? APER_COLORS.red
            : APER_COLORS.blue)}
        />
      </div>

      {/* Tableau sites eligibles */}
      {allSites.length > 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Sites éligibles</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Site
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Type
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                    Surface (m2)
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">
                    Échéance
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {allSites.map((site, idx) => (
                  <tr
                    key={`${site.site_id}-${site.surfaceType}-${idx}`}
                    className="hover:bg-gray-50/50"
                  >
                    <td className="px-4 py-2.5 font-medium text-gray-900">{site.site_nom}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full ${site.type === 'Parking' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}
                      >
                        {site.type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium">{fmt(site.surface_m2)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <DeadlineBadge deadline={site.deadline} />
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <button
                        onClick={() => handleEstimate(site, site.surfaceType)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                      >
                        Estimer la production <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <Sun className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Aucun site éligible détecté</p>
          <p className="text-xs text-gray-400 mt-1">
            Complétez les surfaces parking/toiture dans la fiche site
          </p>
        </div>
      )}

      {/* Estimation PV */}
      {estimating && (
        <div className="bg-white rounded-xl border border-gray-100 p-8 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-500 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Estimation en cours...</p>
        </div>
      )}

      {estimate && !estimate.error && (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-amber-50/60 to-transparent">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              <Explain term="production_pv">Estimation production PV</Explain>
              {' — '}
              <span className="text-gray-900">{estimate.site_nom}</span>
              <span className="text-xs text-gray-400 ml-2">
                ({estimate.surface_type === 'parking' ? 'Parking' : 'Toiture'})
              </span>
            </h2>
          </div>

          {/* KPIs estimation */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-4">
            <KpiCardInline
              icon={Zap}
              label="Puissance crête"
              value={fmt(estimate.puissance_crete_kwc)}
              unit="kWc"
              {...APER_COLORS.amber}
            />
            <KpiCardInline
              icon={Sun}
              label="Production annuelle"
              value={fmt(estimate.production_annuelle_mwh)}
              unit="MWh/an"
              {...APER_COLORS.amber}
            />
            <KpiCardInline
              icon={Euro}
              label="Économies"
              value={fmt(estimate.economies_annuelles_eur)}
              unit="EUR/an"
              {...APER_COLORS.emerald}
            />
            <KpiCardInline
              icon={Leaf}
              label="CO2 évité"
              value={fmt(estimate.co2_evite_tonnes)}
              unit="t/an"
              {...APER_COLORS.emerald}
            />
          </div>

          {/* Graphique barres mensuelles */}
          {monthlyData.length === 12 && (
            <div className="px-4 pb-4">
              <p className="text-xs text-gray-500 mb-2">Production mensuelle estimée (kWh)</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v) => [`${fmt(v)} kWh`, 'Production']}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Bar dataKey="kwh" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Source + methodologie */}
          <div className="px-4 pb-4 border-t border-gray-50 pt-3">
            <p className="text-xs text-gray-500">
              Source : <span className="font-medium">{estimate.source}</span>
            </p>
            {isExpert && estimate.methodology && (
              <p className="text-xs text-gray-400 mt-1">{estimate.methodology}</p>
            )}
            {isExpert && (
              <div className="flex gap-4 text-xs text-gray-400 mt-1">
                <span>Surface panneaux : {fmt(estimate.surface_panneaux_m2)} m2</span>
                <span>Couverture : {(estimate.coverage_ratio * 100).toFixed(0)}%</span>
                <span>Autoconso : {estimate.autoconsommation_pct}%</span>
              </div>
            )}
          </div>
        </div>
      )}

      {estimate?.error && (
        <div className="bg-red-50 rounded-lg p-4 text-center">
          <p className="text-sm text-red-700">{estimate.error}</p>
        </div>
      )}
    </div>
  );
}
