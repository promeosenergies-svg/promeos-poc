/**
 * PROMEOS - Bill Intelligence Page (/bill-intel)
 * Sprint 7: invoices overview, anomaly insights, seed demo, audit-all.
 */
import { useState, useEffect } from 'react';
import {
  getBillingSummary,
  getBillingInsights,
  getBillingInvoices,
  auditAllInvoices,
  seedBillingDemo,
  importInvoicesCsv,
} from '../services/api';
import { Card, CardBody, Badge, Button, TrustBadge } from '../ui';
import {
  FileText, AlertTriangle, CheckCircle, Upload, Play, Download,
  DollarSign, Zap, TrendingUp, RefreshCw,
} from 'lucide-react';
import { track } from '../services/tracker';

const SEVERITY_BADGE = {
  critical: 'crit', high: 'warn', medium: 'info', low: 'neutral',
};

const TYPE_LABELS = {
  shadow_gap: 'Ecart shadow billing',
  unit_price_high: 'Prix unitaire eleve',
  duplicate_invoice: 'Doublon facture',
  missing_period: 'Periode manquante',
  period_too_long: 'Periode longue',
  negative_kwh: 'kWh negatifs',
  zero_amount: 'Montant zero',
  lines_sum_mismatch: 'Ecart lignes/total',
  consumption_spike: 'Pic de consommation',
  price_drift: 'Derive de prix',
};

const STATUS_COLORS = {
  imported: 'bg-gray-100 text-gray-700',
  validated: 'bg-blue-100 text-blue-700',
  audited: 'bg-green-100 text-green-700',
  anomaly: 'bg-red-100 text-red-700',
  archived: 'bg-gray-100 text-gray-500',
};

export default function BillIntelPage() {
  const [summary, setSummary] = useState(null);
  const [insights, setInsights] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [seeding, setSeeding] = useState(false);

  async function fetchData() {
    setLoading(true);
    try {
      const [s, i, inv] = await Promise.all([
        getBillingSummary(),
        getBillingInsights(),
        getBillingInvoices(),
      ]);
      setSummary(s);
      setInsights(i.insights || []);
      setInvoices(inv.invoices || []);
    } catch {
      // API may not be running
    }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, []);

  async function handleSeedDemo() {
    setSeeding(true);
    try {
      await seedBillingDemo();
      track('billing_seed_demo');
      await fetchData();
    } catch { /* ignore */ }
    setSeeding(false);
  }

  async function handleAuditAll() {
    setAuditing(true);
    try {
      await auditAllInvoices();
      track('billing_audit_all');
      await fetchData();
    } catch { /* ignore */ }
    setAuditing(false);
  }

  async function handleCsvImport(e) {
    const file = e.target.files[0];
    if (!file) return;
    try {
      await importInvoicesCsv(file);
      track('billing_csv_import', { filename: file.name });
      await fetchData();
    } catch { /* ignore */ }
    e.target.value = '';
  }

  const hasData = summary && summary.total_invoices > 0;

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Bill Intelligence</h2>
          <p className="text-sm text-gray-500 mt-0.5">Shadow billing simplifie + detection d'anomalies</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <Button variant="secondary" size="sm" as="span">
              <Upload size={14} /> Importer CSV
            </Button>
            <input type="file" accept=".csv" className="sr-only" onChange={handleCsvImport} />
          </label>
          {hasData && (
            <Button size="sm" onClick={handleAuditAll} disabled={auditing}>
              <Play size={14} /> {auditing ? 'Audit...' : 'Auditer tout'}
            </Button>
          )}
          {!hasData && (
            <Button onClick={handleSeedDemo} disabled={seeding}>
              <Zap size={14} /> {seeding ? 'Seed...' : 'Seed demo'}
            </Button>
          )}
          <button onClick={fetchData} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600" title="Rafraichir">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-4">
          <SummaryCard icon={FileText} label="Factures" value={summary.total_invoices} color="blue" />
          <SummaryCard icon={DollarSign} label="Total EUR" value={`${Math.round(summary.total_eur).toLocaleString()}`} color="indigo" />
          <SummaryCard icon={Zap} label="Total kWh" value={`${Math.round(summary.total_kwh).toLocaleString()}`} color="purple" />
          <SummaryCard icon={AlertTriangle} label="Anomalies" value={summary.total_insights} color="red" />
          <SummaryCard icon={TrendingUp} label="Pertes estimees" value={`${Math.round(summary.total_estimated_loss_eur)} EUR`} color="orange" />
        </div>
      )}

      {/* No data state */}
      {!loading && !hasData && (
        <Card>
          <CardBody className="text-center py-12">
            <FileText size={40} className="text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Aucune facture importee</h3>
            <p className="text-sm text-gray-500 mb-6">Importez des factures CSV ou generez des donnees demo pour commencer.</p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={handleSeedDemo} disabled={seeding}>
                <Zap size={14} /> {seeding ? 'Generation...' : 'Generer demo (5 factures)'}
              </Button>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <Button variant="secondary" as="span">
                  <Upload size={14} /> Importer CSV
                </Button>
                <input type="file" accept=".csv" className="sr-only" onChange={handleCsvImport} />
              </label>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Anomalies detectees ({insights.length})
          </h3>
          <div className="space-y-2">
            {insights.map((insight) => (
              <Card key={insight.id} className="border-l-4 border-l-red-300">
                <CardBody className="flex items-center gap-4">
                  <AlertTriangle size={18} className={insight.severity === 'critical' ? 'text-red-600' : insight.severity === 'high' ? 'text-orange-600' : 'text-amber-500'} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">
                        {TYPE_LABELS[insight.type] || insight.type}
                      </span>
                      <Badge status={SEVERITY_BADGE[insight.severity] || 'neutral'}>
                        {insight.severity}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{insight.message}</p>
                  </div>
                  {insight.estimated_loss_eur > 0 && (
                    <span className="text-sm font-bold text-red-600 whitespace-nowrap">
                      {insight.estimated_loss_eur.toLocaleString()} EUR
                    </span>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Invoices table */}
      {invoices.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Factures ({invoices.length})
          </h3>
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Numero</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Periode</th>
                    <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Total EUR</th>
                    <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">kWh</th>
                    <th className="text-center px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Statut</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-medium text-gray-900">{inv.invoice_number}</td>
                      <td className="px-4 py-2.5 text-gray-600">
                        {inv.period_start && inv.period_end
                          ? `${inv.period_start} → ${inv.period_end}`
                          : inv.period_start || '-'
                        }
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium">{inv.total_eur ? `${inv.total_eur.toLocaleString()} EUR` : '-'}</td>
                      <td className="px-4 py-2.5 text-right">{inv.energy_kwh ? inv.energy_kwh.toLocaleString() : '-'}</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[inv.status] || STATUS_COLORS.imported}`}>
                          {inv.status || 'imported'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500">{inv.source || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-2 border-t border-gray-100">
              <TrustBadge source="PROMEOS Bill Intel" period="donnees importees" confidence="medium" />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, color }) {
  const bg = {
    blue: 'bg-blue-50', indigo: 'bg-indigo-50', purple: 'bg-purple-50',
    red: 'bg-red-50', orange: 'bg-orange-50',
  }[color] || 'bg-gray-50';
  const textColor = {
    blue: 'text-blue-700', indigo: 'text-indigo-700', purple: 'text-purple-700',
    red: 'text-red-700', orange: 'text-orange-700',
  }[color] || 'text-gray-700';
  const iconColor = {
    blue: 'text-blue-500', indigo: 'text-indigo-500', purple: 'text-purple-500',
    red: 'text-red-500', orange: 'text-orange-500',
  }[color] || 'text-gray-500';

  return (
    <Card>
      <CardBody className={bg}>
        <div className="flex items-center gap-2 mb-1">
          <Icon size={16} className={iconColor} />
          <p className="text-xs text-gray-500 font-medium">{label}</p>
        </div>
        <p className={`text-2xl font-bold ${textColor}`}>{value}</p>
      </CardBody>
    </Card>
  );
}
