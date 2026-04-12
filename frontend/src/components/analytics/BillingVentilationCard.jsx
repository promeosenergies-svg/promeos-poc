/**
 * BillingVentilationCard — Ventilation de la facture par usage.
 * Stacked bar chart montrant la repartition fourniture/reseau/taxes par usage.
 * Display-only. Donnees de GET /api/billing/usage-ventilation/sites/{id}.
 */

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Receipt } from 'lucide-react';
import { getBillingUsageVentilation } from '../../services/api';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((sum, p) => sum + (p.value || 0), 0);
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.fill }}>
          {p.name} : {Math.round(p.value).toLocaleString('fr-FR')} &euro; HT
        </p>
      ))}
      <p className="text-gray-600 font-medium border-t border-gray-100 pt-1 mt-1">
        Total : {Math.round(total).toLocaleString('fr-FR')} &euro; HT
      </p>
    </div>
  );
}

export default function BillingVentilationCard({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getBillingUsageVentilation(siteId)
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
  }, [siteId]);

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-400 animate-pulse">
        Chargement ventilation facture...
      </div>
    );
  }
  if (!data || !data.by_usage || Object.keys(data.by_usage).length === 0) return null;

  const chartData = Object.entries(data.by_usage).map(([code, u]) => ({
    name: u.label || code,
    fourniture: u.fourniture_ht || 0,
    reseau: u.reseau_ht || 0,
    taxes: u.taxes_ht || 0,
    abo: u.abo_ht || 0,
  }));

  chartData.sort((a, b) => {
    const totalA = a.fourniture + a.reseau + a.taxes + a.abo;
    const totalB = b.fourniture + b.reseau + b.taxes + b.abo;
    return totalB - totalA;
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Receipt size={16} className="text-emerald-600" />
        <h3 className="text-base font-semibold text-gray-900">Ventilation facture par usage</h3>
        <span className="text-xs text-gray-400">
          {Math.round(data.total_kwh || 0).toLocaleString('fr-FR')} kWh
        </span>
      </div>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" barCategoryGap="15%">
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis type="number" tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={120} />
            <Tooltip content={<CustomTooltip />} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 10 }} />
            <Bar dataKey="fourniture" stackId="a" fill="#3b82f6" name="Fourniture" />
            <Bar dataKey="reseau" stackId="a" fill="#f59e0b" name="Reseau (TURPE)" />
            <Bar dataKey="taxes" stackId="a" fill="#ef4444" name="Taxes" />
            <Bar dataKey="abo" stackId="a" fill="#8b5cf6" name="Abonnement" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="text-[10px] text-gray-400">
        Methode : repartition estimee par archetype (
        {data.archetype_code?.replace(/_/g, ' ').toLowerCase()}) &middot; Confiance :{' '}
        {data.confidence || 'medium'}
      </p>
    </div>
  );
}
