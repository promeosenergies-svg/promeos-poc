/**
 * PROMEOS - Page Diagnostic Consommation (Usages & Derives)
 * Sprint 5: insights hors horaires, base load, pointe, derive, data gaps
 */
import { useState, useEffect } from 'react';
import {
  getConsumptionInsights,
  getConsumptionSite,
  runConsumptionDiagnose,
  seedDemoConsumption,
} from '../services/api';

const SEVERITY_COLORS = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
  info: 'bg-gray-100 text-gray-700',
};

const TYPE_LABELS = {
  hors_horaires: 'Hors horaires',
  base_load: 'Talon eleve',
  pointe: 'Pointe anormale',
  derive: 'Derive consommation',
  data_gap: 'Lacunes donnees',
};

function SeverityBadge({ severity }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERITY_COLORS[severity] || SEVERITY_COLORS.info}`}>
      {severity}
    </span>
  );
}

function SummaryCards({ summary }) {
  if (!summary) return null;
  const cards = [
    { label: 'Insights total', value: summary.total_insights, color: 'text-blue-700', bg: 'bg-blue-50' },
    { label: 'Sites analyses', value: summary.sites_with_insights, color: 'text-indigo-700', bg: 'bg-indigo-50' },
    { label: 'Pertes estimees', value: `${Math.round(summary.total_loss_eur || 0)} EUR`, color: 'text-red-700', bg: 'bg-red-50' },
    { label: 'Pertes kWh', value: `${Math.round(summary.total_loss_kwh || 0)} kWh`, color: 'text-orange-700', bg: 'bg-orange-50' },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {cards.map((c) => (
        <div key={c.label} className={`${c.bg} rounded-lg p-4`}>
          <p className="text-xs text-gray-500 mb-1">{c.label}</p>
          <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}

function ByTypeBreakdown({ byType }) {
  if (!byType || Object.keys(byType).length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <h3 className="font-semibold text-gray-800 mb-3">Repartition par type</h3>
      <div className="grid grid-cols-5 gap-3">
        {Object.entries(byType).map(([type, count]) => (
          <div key={type} className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-lg font-bold text-gray-800">{count}</p>
            <p className="text-xs text-gray-500">{TYPE_LABELS[type] || type}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightRow({ insight }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-3 px-4 text-sm text-gray-800">{insight.site_nom || `Site #${insight.site_id}`}</td>
      <td className="py-3 px-4 text-sm">
        <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">
          {TYPE_LABELS[insight.type] || insight.type}
        </span>
      </td>
      <td className="py-3 px-4 text-sm"><SeverityBadge severity={insight.severity} /></td>
      <td className="py-3 px-4 text-sm text-gray-600 max-w-md">{insight.message}</td>
      <td className="py-3 px-4 text-sm text-right text-red-600 font-medium">
        {insight.estimated_loss_eur ? `${Math.round(insight.estimated_loss_eur)} EUR` : '-'}
      </td>
      <td className="py-3 px-4 text-sm text-right text-orange-600">
        {insight.estimated_loss_kwh ? `${Math.round(insight.estimated_loss_kwh)} kWh` : '-'}
      </td>
    </tr>
  );
}

export default function ConsumptionDiagPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [message, setMessage] = useState(null);
  const [filterType, setFilterType] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await getConsumptionInsights();
      setSummary(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setMessage(null);
    try {
      const r = await seedDemoConsumption();
      setMessage(`Demo conso generee: ${r.total || r.sites?.length || 0} site(s)`);
      await load();
    } catch (e) {
      setMessage('Erreur: ' + (e.response?.data?.detail || e.message));
    } finally {
      setSeeding(false);
    }
  };

  const handleDiagnose = async () => {
    setDiagnosing(true);
    setMessage(null);
    try {
      const r = await runConsumptionDiagnose();
      setMessage(`Diagnostic termine: ${r.total_insights || 0} insight(s) sur ${r.sites_evaluated || 0} site(s)`);
      await load();
    } catch (e) {
      setMessage('Erreur: ' + (e.response?.data?.detail || e.message));
    } finally {
      setDiagnosing(false);
    }
  };

  const insights = summary?.insights || [];
  const filtered = filterType ? insights.filter((i) => i.type === filterType) : insights;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Usages & Derives</h2>
          <p className="text-gray-500 text-sm mt-1">Diagnostic automatique de la consommation energetique</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="px-4 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300 transition text-sm disabled:opacity-50"
          >
            {seeding ? 'Generation...' : 'Generer conso demo'}
          </button>
          <button
            onClick={handleDiagnose}
            disabled={diagnosing}
            className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 transition text-sm disabled:opacity-50"
          >
            {diagnosing ? 'Analyse en cours...' : 'Lancer diagnostic'}
          </button>
        </div>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-blue-50 text-blue-800 rounded text-sm">{message}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400">Chargement...</div>
      ) : !summary || summary.total_insights === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg mb-4">Aucun insight de consommation</p>
          <p className="text-gray-400 text-sm mb-6">
            Generez des donnees demo puis lancez le diagnostic pour detecter les anomalies.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="px-6 py-3 rounded bg-gray-600 text-white hover:bg-gray-700 transition disabled:opacity-50"
            >
              1. Generer conso demo
            </button>
            <button
              onClick={handleDiagnose}
              disabled={diagnosing}
              className="px-6 py-3 rounded bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50"
            >
              2. Lancer le diagnostic
            </button>
          </div>
        </div>
      ) : (
        <>
          <SummaryCards summary={summary} />
          <ByTypeBreakdown byType={summary.by_type} />

          {/* Filters */}
          <div className="flex items-center gap-3 mb-4">
            <label className="text-sm text-gray-500">Type:</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm"
            >
              <option value="">Tous</option>
              {Object.entries(TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <span className="text-xs text-gray-400 ml-2">{filtered.length} insight(s)</span>
          </div>

          {/* Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Site</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Severite</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Message</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">Perte EUR</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">Perte kWh</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ins, i) => (
                  <InsightRow key={ins.id || i} insight={ins} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
