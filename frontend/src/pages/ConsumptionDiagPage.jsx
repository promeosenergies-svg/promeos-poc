/**
 * PROMEOS - Page Diagnostic Consommation V1.1 (Usages & Derives)
 * Sprint 5 base + Sprint 6: schedule, tariff, recommended actions, robust stats
 */
import { useState, useEffect } from 'react';
import {
  getConsumptionInsights,
  runConsumptionDiagnose,
  seedDemoConsumption,
} from '../services/api';
import { Card, CardBody, Badge, Button } from '../ui';
import { Clock, Zap, ChevronDown, ChevronUp, Settings } from 'lucide-react';
import { track } from '../services/tracker';

const SEVERITY_COLORS = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
  info: 'bg-gray-100 text-gray-700',
};

const SEVERITY_BADGE = {
  critical: 'crit', high: 'warn', medium: 'info', low: 'neutral',
};

const TYPE_LABELS = {
  hors_horaires: 'Hors horaires',
  base_load: 'Talon eleve',
  pointe: 'Pointe anormale',
  derive: 'Derive consommation',
  data_gap: 'Lacunes donnees',
};

const EFFORT_COLOR = {
  high: 'bg-red-50 text-red-700',
  medium: 'bg-amber-50 text-amber-700',
  low: 'bg-green-50 text-green-700',
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
        <Card key={c.label}>
          <CardBody className={c.bg}>
            <p className="text-xs text-gray-500 mb-1">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function ByTypeBreakdown({ byType }) {
  if (!byType || Object.keys(byType).length === 0) return null;
  return (
    <Card className="mb-6">
      <CardBody>
        <h3 className="font-semibold text-gray-800 mb-3">Repartition par type</h3>
        <div className="grid grid-cols-5 gap-3">
          {Object.entries(byType).map(([type, count]) => (
            <div key={type} className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-gray-800">{count}</p>
              <p className="text-xs text-gray-500">{TYPE_LABELS[type] || type}</p>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function RecommendedAction({ action }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
      <Zap size={16} className="text-blue-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">{action.title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{action.rationale}</p>
        <div className="flex items-center gap-3 mt-2">
          {action.expected_gain_eur > 0 && (
            <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded">
              +{action.expected_gain_eur.toLocaleString()} EUR/an
            </span>
          )}
          {action.effort && (
            <span className={`text-xs px-2 py-0.5 rounded ${EFFORT_COLOR[action.priority] || EFFORT_COLOR.medium}`}>
              Effort: {action.effort}
            </span>
          )}
          <Badge status={SEVERITY_BADGE[action.priority] || 'neutral'}>{action.priority}</Badge>
        </div>
      </div>
    </div>
  );
}

function InsightRow({ insight }) {
  const [expanded, setExpanded] = useState(false);
  const actions = insight.recommended_actions || [];
  const metrics = insight.metrics || {};

  return (
    <>
      <tr
        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
        onClick={() => { setExpanded(!expanded); track('insight_toggle', { type: insight.type, expanded: !expanded }); }}
      >
        <td className="py-3 px-4 text-sm text-gray-800 font-medium">{insight.site_nom || `Site #${insight.site_id}`}</td>
        <td className="py-3 px-4 text-sm">
          <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">
            {TYPE_LABELS[insight.type] || insight.type}
          </span>
        </td>
        <td className="py-3 px-4 text-sm"><SeverityBadge severity={insight.severity} /></td>
        <td className="py-3 px-4 text-sm text-gray-600 max-w-md truncate">{insight.message}</td>
        <td className="py-3 px-4 text-sm text-right text-red-600 font-medium">
          {insight.estimated_loss_eur ? `${Math.round(insight.estimated_loss_eur)} EUR` : '-'}
        </td>
        <td className="py-3 px-4 text-sm text-right text-orange-600">
          {insight.estimated_loss_kwh ? `${Math.round(insight.estimated_loss_kwh)} kWh` : '-'}
        </td>
        <td className="py-3 px-4 text-sm text-center">
          {actions.length > 0 && (
            expanded ? <ChevronUp size={16} className="text-gray-400 inline" /> : <ChevronDown size={16} className="text-gray-400 inline" />
          )}
        </td>
      </tr>
      {expanded && actions.length > 0 && (
        <tr>
          <td colSpan={7} className="px-4 py-3 bg-blue-50/30">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Actions recommandees</p>
              {actions.map((a, i) => <RecommendedAction key={i} action={a} />)}
              {metrics.price_ref_eur_kwh && (
                <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                  <Settings size={12} /> Prix ref: {metrics.price_ref_eur_kwh} EUR/kWh
                  {metrics.schedule_open && ` | Horaires: ${metrics.schedule_open}`}
                  {metrics.schedule_source && ` (${metrics.schedule_source})`}
                </p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
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
      setMessage(`Diagnostic termine: ${r.total_insights || 0} insight(s) sur ${r.sites_analyzed || 0} site(s)`);
      track('diagnostic_run', { insights: r.total_insights });
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
    <div className="px-6 py-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Diagnostic</h2>
          <p className="text-sm text-gray-500 mt-0.5">Détection automatique : horaires, talon, pointes, dérives</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleSeedDemo} disabled={seeding}>
            {seeding ? 'Generation...' : 'Generer conso demo'}
          </Button>
          <Button size="sm" onClick={handleDiagnose} disabled={diagnosing}>
            <Zap size={14} />
            {diagnosing ? 'Analyse...' : 'Lancer diagnostic'}
          </Button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-blue-50 text-blue-800 rounded-lg text-sm">{message}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400">Chargement...</div>
      ) : !summary || summary.total_insights === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <Zap size={32} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 text-lg mb-2">Aucun insight de consommation</p>
            <p className="text-gray-400 text-sm mb-6">
              Generez des donnees demo puis lancez le diagnostic pour detecter les anomalies.
            </p>
            <div className="flex gap-3 justify-center">
              <Button variant="secondary" onClick={handleSeedDemo} disabled={seeding}>
                1. Generer conso demo
              </Button>
              <Button onClick={handleDiagnose} disabled={diagnosing}>
                2. Lancer le diagnostic
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : (
        <>
          <SummaryCards summary={summary} />
          <ByTypeBreakdown byType={summary.by_type} />

          {/* Filters */}
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-500">Type:</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tous</option>
              {Object.entries(TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <span className="text-xs text-gray-400 ml-2">{filtered.length} insight(s)</span>
          </div>

          {/* Table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Site</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Severite</th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Message</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">Perte EUR</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">Perte kWh</th>
                    <th className="w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((ins, i) => (
                    <InsightRow key={ins.id || i} insight={ins} />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
