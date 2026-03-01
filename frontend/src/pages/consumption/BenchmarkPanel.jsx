/**
 * PROMEOS — BenchmarkPanel (P1-1 / P1.1 polish)
 * Courbe de reference grand public (Enedis-inspired).
 * Toggle "Comparer a la courbe moyenne de sites similaires" + 2 selectors + KPI ecart.
 * Confidence tooltip "Comment calcule ?" + KPI source (estime).
 */
import { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Card, CardBody, TrustBadge } from '../../ui';
import { SkeletonCard } from '../../ui';
import { getEmsReferenceProfile } from '../../services/api';
import { track } from '../../services/tracker';
import { HelpCircle } from 'lucide-react';

const FAMILLE_OPTIONS = [
  { value: 'habitat', label: 'Habitat' },
  { value: 'petit_tertiaire', label: 'Petit tertiaire' },
  { value: 'entreprise', label: 'Entreprise' },
];

const PUISSANCE_OPTIONS = [
  { value: '0-6', label: '0-6 kVA' },
  { value: '6-9', label: '6-9 kVA' },
  { value: '9-12', label: '9-12 kVA' },
  { value: '12-36', label: '12-36 kVA' },
  { value: '>36', label: '> 36 kVA' },
];

const CONFIDENCE_MAP = {
  high: { label: 'Elevee', variant: 'ok', desc: 'Couverture > 80 % des points attendus' },
  medium: { label: 'Moyenne', variant: 'warn', desc: 'Couverture entre 50 % et 80 %' },
  low: { label: 'Basse', variant: 'crit', desc: 'Couverture < 50 % — profil indicatif' },
};

function formatDate(t) {
  if (!t || t.length < 10) return t;
  const d = new Date(t.replace(' ', 'T'));
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

export default function BenchmarkPanel({ siteId, days, startDate, endDate, seriesData, toast }) {
  const [enabled, setEnabled] = useState(false);
  const [famille, setFamille] = useState('entreprise');
  const [puissance, setPuissance] = useState('9-12');
  const [refData, setRefData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Compute date range
  const dateFrom = startDate || (() => {
    const d = new Date();
    d.setDate(d.getDate() - (days || 30));
    return d.toISOString().slice(0, 10);
  })();
  const dateTo = endDate || new Date().toISOString().slice(0, 10);

  const load = useCallback(async () => {
    if (!enabled || !siteId) return;
    setLoading(true);
    try {
      const data = await getEmsReferenceProfile(siteId, dateFrom, dateTo, famille, puissance, 'daily');
      setRefData(data);
      track('benchmark_loaded', { famille, puissance, site_id: siteId });
    } catch (e) {
      toast?.('Erreur chargement profil de reference', 'error');
      setRefData(null);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, siteId, dateFrom, dateTo, famille, puissance]);

  useEffect(() => { load(); }, [load]);

  // Merge actual + reference into chart data
  const chartData = (() => {
    if (!refData?.series) return [];
    const refMap = {};
    for (const pt of refData.series) {
      const key = pt.t.slice(0, 10);
      refMap[key] = pt.v;
    }

    // Actual data from seriesData (parent TimeseriesPanel)
    const actualMap = {};
    if (seriesData?.[0]?.data) {
      for (const pt of seriesData[0].data) {
        const key = (pt.t || '').slice(0, 10);
        if (pt.v != null) actualMap[key] = (actualMap[key] || 0) + pt.v;
      }
    }

    const allDates = [...new Set([...Object.keys(refMap), ...Object.keys(actualMap)])].sort();
    return allDates.map(d => ({
      date: formatDate(d),
      rawDate: d,
      actual: actualMap[d] != null ? Math.round(actualMap[d] * 10) / 10 : null,
      reference: refMap[d] != null ? Math.round(refMap[d] * 10) / 10 : null,
    }));
  })();

  const kpi = refData?.kpi;
  const conf = kpi?.confidence ? CONFIDENCE_MAP[kpi.confidence] : null;

  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">Comparer a la courbe moyenne de sites similaires</span>
        </label>
      </div>

      {enabled && (
        <>
          {/* Selectors */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Type de site</label>
              <select
                value={famille}
                onChange={(e) => setFamille(e.target.value)}
                className="text-sm border rounded px-2 py-1"
              >
                {FAMILLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Puissance souscrite</label>
              <select
                value={puissance}
                onChange={(e) => setPuissance(e.target.value)}
                className="text-sm border rounded px-2 py-1"
              >
                {PUISSANCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            {conf && (
              <span className="inline-flex items-center gap-1" title={`Comment calcule ? ${conf.desc}`}>
                <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
                <HelpCircle size={12} className="text-gray-400 cursor-help" />
              </span>
            )}
          </div>

          {loading && <SkeletonCard rows={4} />}

          {/* KPI delta cards */}
          {kpi && !loading && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card>
                <CardBody className="py-3 px-4 text-center">
                  <p className="text-xs text-gray-500">Votre consommation</p>
                  <p className="text-lg font-bold text-gray-800">{Math.round(kpi.actual_kwh).toLocaleString('fr-FR')} kWh</p>
                  <p className="text-[10px] text-gray-400" title="Estime a partir des releves compteur">Source : releves</p>
                </CardBody>
              </Card>
              <Card>
                <CardBody className="py-3 px-4 text-center">
                  <p className="text-xs text-gray-500">Moyenne sites similaires</p>
                  <p className="text-lg font-bold text-blue-600">{Math.round(kpi.reference_kwh).toLocaleString('fr-FR')} kWh</p>
                  <p className="text-[10px] text-gray-400">Profil statistique</p>
                </CardBody>
              </Card>
              <Card>
                <CardBody className="py-3 px-4 text-center">
                  <p className="text-xs text-gray-500">Ecart</p>
                  <p className={`text-lg font-bold ${kpi.delta_pct > 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {kpi.delta_pct > 0 ? '+' : ''}{kpi.delta_pct} %
                  </p>
                  <p className="text-xs text-gray-400">{kpi.delta_kwh > 0 ? '+' : ''}{Math.round(kpi.delta_kwh).toLocaleString('fr-FR')} kWh</p>
                </CardBody>
              </Card>
              <Card>
                <CardBody className="py-3 px-4 text-center">
                  <p className="text-xs text-gray-500">Couverture donnees</p>
                  <p className="text-lg font-bold text-gray-800">{kpi.coverage_pct} %</p>
                  <p className="text-[10px] text-gray-400" title="Pourcentage de points de mesure disponibles vs attendus">Points mesures / attendus</p>
                </CardBody>
              </Card>
            </div>
          )}

          {/* Chart: actual vs reference */}
          {chartData.length > 0 && !loading && (
            <Card>
              <CardBody>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Votre consommation vs moyenne de sites similaires</h4>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
                    <YAxis tick={{ fontSize: 10 }} label={{ value: 'kWh', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="reference" stroke="#93c5fd" fill="#dbeafe" fillOpacity={0.5} name="Moyenne sites similaires" strokeDasharray="5 5" />
                    <Area type="monotone" dataKey="actual" stroke="#3b82f6" fill="#bfdbfe" fillOpacity={0.3} name="Votre consommation" />
                  </AreaChart>
                </ResponsiveContainer>
                <p className="text-[10px] text-gray-400 mt-1 text-center">
                  Profil : {FAMILLE_OPTIONS.find(o => o.value === famille)?.label} · {PUISSANCE_OPTIONS.find(o => o.value === puissance)?.label}
                </p>
              </CardBody>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
