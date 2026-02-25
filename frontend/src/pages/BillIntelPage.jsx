/**
 * PROMEOS - Bill Intelligence Page (/bill-intel)
 * Sprint 7.1: invoices overview, anomaly insights with workflow, seed demo, audit-all.
 */
import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  getBillingSummary,
  getBillingInsights,
  getBillingInvoices,
  auditAllInvoices,
  seedBillingDemo,
  importInvoicesCsv,
  resolveBillingInsight,
  importInvoicesPdf,
  createActionFromBillingInsight,
  getSites,
} from '../services/api';
import { Card, CardBody, Badge, Button, TrustBadge, PageShell, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';
import {
  FileText, AlertTriangle, CheckCircle, Upload, Play, Download,
  DollarSign, Zap, TrendingUp, RefreshCw, CheckCircle2, CalendarRange,
} from 'lucide-react';
import { useExpertMode } from '../contexts/ExpertModeContext';
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

const INSIGHT_STATUS_COLORS = {
  open: 'bg-yellow-100 text-yellow-800',
  ack: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  false_positive: 'bg-gray-100 text-gray-500',
};

const INSIGHT_STATUS_LABELS = {
  open: 'Ouvert',
  ack: 'Pris en charge',
  resolved: 'Resolu',
  false_positive: 'Faux positif',
};

const INSIGHT_FILTER_OPTIONS = [
  { value: 'all', label: 'Tous' },
  { value: 'open', label: 'Ouverts' },
  { value: 'ack', label: 'Pris en charge' },
  { value: 'resolved', label: 'Resolus' },
  { value: 'false_positive', label: 'Faux positifs' },
];

export default function BillIntelPage() {
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Deep-link params: ?site_id=X&month=YYYY-MM
  const [siteFilter, setSiteFilter] = useState(searchParams.get('site_id') || '');
  const [monthFilter, setMonthFilter] = useState(searchParams.get('month') || '');

  const [summary, setSummary] = useState(null);
  const [insights, setInsights] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [insightFilter, setInsightFilter] = useState('all');
  const [createdActions, setCreatedActions] = useState(new Set());
  const [pdfSiteId, setPdfSiteId] = useState('');
  const [invoiceSearch, setInvoiceSearch] = useState('');
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState('');
  const [periodPreset, setPeriodPreset] = useState('all');
  const [sites, setSites] = useState([]);

  async function fetchData() {
    setLoading(true);
    try {
      const insightParams = { ...(insightFilter !== 'all' && { status: insightFilter }), ...(siteFilter && { site_id: siteFilter }) };
      const invoiceParams = { ...(siteFilter && { site_id: siteFilter }) };
      const [s, i, inv] = await Promise.all([
        getBillingSummary(),
        getBillingInsights(insightParams),
        getBillingInvoices(invoiceParams),
      ]);
      setSummary(s);
      setInsights(i.insights || []);
      setInvoices(inv.invoices || []);
    } catch {
      toast('Erreur lors du chargement de la facturation', 'error');
    }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, [insightFilter, siteFilter]);

  useEffect(() => {
    getSites({ limit: 200 })
      .then(data => setSites(Array.isArray(data?.sites) ? data.sites : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (siteFilter && !pdfSiteId) setPdfSiteId(siteFilter);
  }, [siteFilter]);

  // Filtrage front : période (preset ou mois exact), statut, texte libre (N° facture ou PDL)
  const filteredInvoices = useMemo(() => {
    const now = new Date();
    const cutoff = periodPreset === 'last3'  ? new Date(now.getFullYear(), now.getMonth() - 3, 1)
                 : periodPreset === 'last6'  ? new Date(now.getFullYear(), now.getMonth() - 6, 1)
                 : periodPreset === 'last12' ? new Date(now.getFullYear(), now.getMonth() - 12, 1)
                 : null;
    return invoices
      .filter(inv => {
        if (periodPreset === 'specific') return !monthFilter || (inv.period_start || '').startsWith(monthFilter);
        if (cutoff) return new Date(inv.period_start || inv.issue_date || '9999') >= cutoff;
        return true;
      })
      .filter(inv => !invoiceStatusFilter || inv.status === invoiceStatusFilter)
      .filter(inv => {
        if (!invoiceSearch) return true;
        const q = invoiceSearch.toLowerCase();
        return (
          (inv.invoice_number || '').toLowerCase().includes(q) ||
          (inv.pdl_prm || '').toLowerCase().includes(q)
        );
      });
  }, [invoices, periodPreset, monthFilter, invoiceStatusFilter, invoiceSearch]);

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

  async function handleResolveInsight(insightId) {
    try {
      await resolveBillingInsight(insightId);
      track('billing_insight_resolved', { insight_id: insightId });
      await fetchData();
    } catch { /* ignore */ }
  }

  async function handlePdfImport(e) {
    const file = e.target.files[0];
    if (!file || !pdfSiteId) return;
    try {
      await importInvoicesPdf(Number(pdfSiteId), file);
      track('billing_pdf_import', { filename: file.name });
      await fetchData();
    } catch { /* ignore */ }
    e.target.value = '';
  }

  async function handleCreateAction(insight) {
    if (createdActions.has(insight.id)) return;
    try {
      await createActionFromBillingInsight(insight.id, insight.message || insight.type, insight.site_id);
      setCreatedActions(prev => new Set([...prev, insight.id]));
      track('billing_create_action', { insight_id: insight.id });
    } catch { /* ignore */ }
  }

  const hasData = summary && summary.total_invoices > 0;

  return (
    <PageShell
      icon={FileText}
      title="Facturation"
      subtitle="Shadow billing, TURPE/ATRD/ATRT, ecarts & anomalies"
      actions={
        <>
          {siteFilter && (
            <Button size="sm" variant="secondary" onClick={() => navigate(`/billing?site_id=${siteFilter}`)}>
              <CalendarRange size={14} /> Voir timeline
            </Button>
          )}
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <Button variant="secondary" size="sm" as="span">
              <Upload size={14} /> Importer CSV
            </Button>
            <input type="file" accept=".csv" className="sr-only" onChange={handleCsvImport} />
          </label>
          <div className="inline-flex items-center gap-1">
            <select
              value={pdfSiteId}
              onChange={e => setPdfSiteId(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400"
            >
              <option value="">Site…</option>
              {sites.map(s => (
                <option key={s.id} value={s.id}>{s.nom}</option>
              ))}
            </select>
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <Button variant="secondary" size="sm" as="span" disabled={!pdfSiteId}>
                <Upload size={14} /> Importer PDF
              </Button>
              <input type="file" accept=".pdf" className="sr-only" onChange={handlePdfImport} disabled={!pdfSiteId} />
            </label>
          </div>
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
        </>
      }
    >

      {/* Breadcrumb filtres actifs */}
      {(siteFilter || monthFilter) && (
        <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
          {siteFilter && <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full">Site : {siteFilter}</span>}
          {monthFilter && <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded-full">Mois : {monthFilter}</span>}
          <button
            className="text-gray-400 hover:text-gray-600 underline"
            onClick={() => { setSiteFilter(''); setMonthFilter(''); }}
          >
            Réinitialiser filtres
          </button>
        </div>
      )}

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
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Aucune facture importée</h3>
            <p className="text-sm text-gray-500 mb-6">Importez des factures CSV ou générez des données démo pour commencer.</p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={handleSeedDemo} disabled={seeding}>
                <Zap size={14} /> {seeding ? 'Génération...' : 'Générer démo (5 factures)'}
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

      {/* Insights with workflow filter */}
      {insights.length > 0 || insightFilter !== 'all' ? (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">
              Anomalies détectées ({insights.length})
            </h3>
            <div className="flex items-center gap-1">
              {INSIGHT_FILTER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setInsightFilter(opt.value)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    insightFilter === opt.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            {insights.map((insight) => {
              const istatus = insight.insight_status || 'open';
              return (
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
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${INSIGHT_STATUS_COLORS[istatus] || INSIGHT_STATUS_COLORS.open}`}>
                          {INSIGHT_STATUS_LABELS[istatus] || istatus}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{insight.message}</p>
                      {insight.owner && (
                        <p className="text-xs text-gray-400 mt-0.5">Responsable: {insight.owner}</p>
                      )}
                    </div>
                    {insight.estimated_loss_eur > 0 && (
                      <span className="text-sm font-bold text-red-600 whitespace-nowrap">
                        {insight.estimated_loss_eur.toLocaleString()} EUR
                      </span>
                    )}
                    {istatus !== 'resolved' && istatus !== 'false_positive' && (
                      <button
                        onClick={() => handleResolveInsight(insight.id)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                          text-green-700 bg-green-50 hover:bg-green-100 transition-colors whitespace-nowrap"
                        title="Marquer comme resolu"
                      >
                        <CheckCircle2 size={14} /> Resolu
                      </button>
                    )}
                    <button
                      onClick={() => handleCreateAction(insight)}
                      disabled={createdActions.has(insight.id)}
                      className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                        transition-colors whitespace-nowrap
                        ${createdActions.has(insight.id)
                          ? 'text-gray-400 bg-gray-50 cursor-default'
                          : 'text-blue-700 bg-blue-50 hover:bg-blue-100'}`}
                      title="Créer action"
                    >
                      {createdActions.has(insight.id) ? '✓ Action créée' : 'Créer action'}
                    </button>
                  </CardBody>
                </Card>
              );
            })}
            {insights.length === 0 && insightFilter !== 'all' && (
              <p className="text-sm text-gray-400 text-center py-4">
                Aucune anomalie avec le statut "{INSIGHT_FILTER_OPTIONS.find(o => o.value === insightFilter)?.label}".
              </p>
            )}
          </div>
        </div>
      ) : null}

      {/* Invoices table */}
      {(filteredInvoices.length > 0 || invoiceSearch || invoiceStatusFilter) && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Factures ({filteredInvoices.length}{monthFilter ? ` — ${monthFilter}` : ''})
          </h3>
          {/* Filter bar */}
          <div className="flex flex-wrap gap-2 mb-3 items-center">
            <input
              type="text"
              placeholder="N° facture ou PDL…"
              value={invoiceSearch}
              onChange={e => setInvoiceSearch(e.target.value)}
              className="border border-gray-200 rounded px-2 py-1 text-sm w-48 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <select
              value={periodPreset}
              onChange={e => { setPeriodPreset(e.target.value); if (e.target.value !== 'specific') setMonthFilter(''); }}
              className="border border-gray-200 rounded px-2 py-1 text-sm"
            >
              <option value="all">Toutes périodes</option>
              <option value="last3">3 derniers mois</option>
              <option value="last6">6 derniers mois</option>
              <option value="last12">12 derniers mois</option>
              <option value="specific">Mois spécifique</option>
            </select>
            {periodPreset === 'specific' && (
              <input
                type="month"
                value={monthFilter}
                onChange={e => setMonthFilter(e.target.value)}
                className="border border-gray-200 rounded px-2 py-1 text-sm"
              />
            )}
            {['', 'imported', 'audited', 'anomaly', 'archived'].map(s => (
              <button
                key={s}
                onClick={() => setInvoiceStatusFilter(s)}
                className={`px-2 py-1 rounded text-xs border ${
                  invoiceStatusFilter === s
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                }`}
              >
                {s === '' ? 'Tous' : s === 'imported' ? 'Importé' : s === 'audited' ? 'Audité' : s === 'anomaly' ? 'Anomalie' : 'Archivé'}
              </button>
            ))}
          </div>
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
                  {filteredInvoices.map((inv) => (
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
              <TrustBadge source="PROMEOS Bill Intel" period="données importées" confidence="medium" />
            </div>
          </Card>
        </div>
      )}
    </PageShell>
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
