/**
 * PROMEOS - Bill Intelligence Page (/bill-intel)
 * Sprint 7.1: invoices overview, anomaly insights with workflow, seed demo, audit-all.
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  getBillingSummary,
  getBillingInsights,
  getBillingInvoices,
  auditAllInvoices,
  seedBillingDemo,
  importInvoicesCsv,
  resolveBillingInsight,
  importInvoicesPdf,
  getSites,
  getInsightDetail,
} from '../services/api';
import { Card, CardBody, Badge, Button, TrustBadge, PageShell, EmptyState, Explain } from '../ui';
// Sprint 2 refonte : header éditorial Sol.
import { SolPageHeader } from '../ui/sol';
import { SkeletonKpi, SkeletonTable } from '../ui/Skeleton';
import ErrorState from '../ui/ErrorState';
import Tooltip from '../ui/Tooltip';
import { useToast } from '../ui/ToastProvider';
import {
  FileText,
  AlertTriangle,
  Upload,
  Play,
  Printer,
  Euro,
  Zap,
  TrendingUp,
  RefreshCw,
  CheckCircle2,
  CalendarRange,
  ArrowRight,
  Download,
} from 'lucide-react';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
import { getKpiMessage } from '../services/kpiMessaging';
import InsightDrawer from '../components/InsightDrawer';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import ActionDetailDrawer from '../components/ActionDetailDrawer';
import DossierPrintView from '../components/DossierPrintView';
import HealthSummary from '../components/HealthSummary';
import {
  computeBillingHealthState,
  computeHealthTrend,
  loadHealthSnapshot,
  saveHealthSnapshot,
  isActiveInsight,
} from '../models/billingHealthModel';
import { fmtEur, fmtKwh } from '../utils/format';

const VALID_STATUSES = ['open', 'ack', 'resolved', 'false_positive'];

const SEVERITY_BADGE = {
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
};

const TYPE_LABELS = {
  shadow_gap: 'Écart facture / consommation',
  unit_price_high: 'Prix unitaire élevé',
  duplicate_invoice: 'Doublon facture',
  missing_period: 'Période manquante',
  period_too_long: 'Période longue',
  negative_kwh: 'kWh négatifs',
  zero_amount: 'Montant zéro',
  lines_sum_mismatch: 'Écart lignes/total',
  consumption_spike: 'Pic de consommation',
  price_drift: 'Dérive de prix',
  ttc_coherence: 'Cohérence TTC',
  contract_expiry: 'Contrat expiré',
  reseau_mismatch: 'Écart réseau / TURPE',
  taxes_mismatch: 'Écart taxes / accise',
};

const STATUS_COLORS = {
  imported: 'bg-gray-100 text-gray-700',
  validated: 'bg-blue-100 text-blue-700',
  audited: 'bg-green-100 text-green-700',
  anomaly: 'bg-red-100 text-red-700',
  archived: 'bg-gray-100 text-gray-500',
};

const STATUS_LABELS = {
  imported: 'Importé',
  validated: 'Validé',
  audited: 'Audité',
  anomaly: 'Anomalie',
  archived: 'Archivé',
};

const SEVERITY_LABELS = {
  critical: 'Critique',
  high: 'Élevé',
  medium: 'Moyen',
  low: 'Faible',
};

const INSIGHT_STATUS_COLORS = {
  open: 'bg-yellow-100 text-yellow-700',
  ack: 'bg-blue-100 text-blue-700',
  resolved: 'bg-green-100 text-green-700',
  false_positive: 'bg-gray-100 text-gray-700',
};

const INSIGHT_STATUS_LABELS = {
  open: 'Ouvert',
  ack: 'Pris en charge',
  resolved: 'Résolu',
  false_positive: 'Faux positif',
};

const INSIGHT_FILTER_OPTIONS = [
  { value: 'all', label: 'Tous' },
  { value: 'open', label: 'Ouverts' },
  { value: 'ack', label: 'Pris en charge' },
  { value: 'resolved', label: 'Résolus' },
  { value: 'false_positive', label: 'Faux positifs' },
];

export default function BillIntelPage() {
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const navigate = useNavigate();
  const { selectedSiteId: scopeSiteId, scope } = useScope();
  const [searchParams] = useSearchParams();
  const anomaliesRef = useRef(null);

  // Deep-link params: ?site_id=X&month=YYYY-MM — init from scope global
  const [siteFilter, setSiteFilter] = useState(
    searchParams.get('site_id') || (scopeSiteId ? String(scopeSiteId) : '')
  );
  const [monthFilter, setMonthFilter] = useState(searchParams.get('month') || '');

  const [summary, setSummary] = useState(null);
  const [insights, setInsights] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [auditing, setAuditing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [insightFilter, setInsightFilter] = useState(
    searchParams.get('filter') === 'anomalies' ? 'open' : 'all'
  );
  const [actionMap, setActionMap] = useState(new Map());
  const { openActionDrawer } = useActionDrawer();
  const [viewActionId, setViewActionId] = useState(null);
  const [pdfSiteId, setPdfSiteId] = useState('');
  const [invoiceSearch, setInvoiceSearch] = useState('');
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState('');
  const [periodPreset, setPeriodPreset] = useState('all');
  const [invoicePage, setInvoicePage] = useState(0);
  const INVOICES_PER_PAGE = 20;
  const [drawerInsightId, setDrawerInsightId] = useState(null);
  const [sites, setSites] = useState([]);
  const [allInsights, setAllInsights] = useState([]); // unfiltered — for health computation
  const csvInputRef = useRef(null);
  const pdfInputRef = useRef(null);
  const [dossierSource, setDossierSource] = useState(null);
  const [dossierInsightDetail, setDossierInsightDetail] = useState(null);

  async function fetchData() {
    setLoading(true);
    setLoadError(null);
    try {
      const insightParams = {
        ...(insightFilter !== 'all' && { status: insightFilter }),
        ...(siteFilter && { site_id: siteFilter }),
      };
      const invoiceParams = { ...(siteFilter && { site_id: siteFilter }) };
      // Fetch unfiltered insights in parallel for health banner
      const healthInsightParams = siteFilter ? { site_id: siteFilter } : {};
      const [s, i, inv, allIns] = await Promise.all([
        getBillingSummary({ ...(siteFilter && { site_id: siteFilter }) }),
        getBillingInsights(insightParams),
        getBillingInvoices(invoiceParams),
        getBillingInsights(healthInsightParams).catch(() => ({ insights: [] })),
      ]);
      setSummary(s);
      const insightsData = i.insights || [];
      setInsights(insightsData);
      setAllInsights(allIns.insights || []);
      // Initialize actionMap from backend action_id
      const newMap = new Map();
      for (const ins of insightsData) {
        if (ins.action_id) newMap.set(ins.id, ins.action_id);
      }
      setActionMap(newMap);
      setInvoices(inv.invoices || []);
    } catch (err) {
      setLoadError(err?.message || 'Erreur lors du chargement de la facturation');
      toast('Erreur lors du chargement de la facturation', 'error');
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insightFilter, siteFilter]);

  // Sync scope global → local siteFilter
  useEffect(() => {
    setSiteFilter(scopeSiteId ? String(scopeSiteId) : '');
  }, [scopeSiteId]);

  // Auto-scroll to anomalies section when deep-linked with ?filter=anomalies
  const filterParam = searchParams.get('filter');
  useEffect(() => {
    if (filterParam === 'anomalies' && !loading && anomaliesRef.current) {
      anomaliesRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [loading, filterParam]);

  useEffect(() => {
    getSites({ limit: 200 })
      .then((data) => setSites(Array.isArray(data?.sites) ? data.sites : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (siteFilter) {
      setPdfSiteId(siteFilter);
    } else if (!pdfSiteId && sites.length > 0) {
      setPdfSiteId(String(sites[0].id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteFilter, sites]);

  // Filtrage front : période (preset ou mois exact), statut, texte libre (N° facture ou PDL)
  const filteredInvoices = useMemo(() => {
    const now = new Date();
    const cutoff =
      periodPreset === 'last3'
        ? new Date(now.getFullYear(), now.getMonth() - 3, 1)
        : periodPreset === 'last6'
          ? new Date(now.getFullYear(), now.getMonth() - 6, 1)
          : periodPreset === 'last12'
            ? new Date(now.getFullYear(), now.getMonth() - 12, 1)
            : null;
    return invoices
      .filter((inv) => {
        if (periodPreset === 'specific')
          return !monthFilter || (inv.period_start || '').startsWith(monthFilter);
        if (cutoff) {
          const dateStr = inv.period_start || inv.issue_date;
          if (!dateStr) return true;
          return new Date(dateStr) >= cutoff;
        }
        return true;
      })
      .filter((inv) => !invoiceStatusFilter || inv.status === invoiceStatusFilter)
      .filter((inv) => {
        if (!invoiceSearch) return true;
        const q = invoiceSearch.toLowerCase();
        return (
          (inv.invoice_number || '').toLowerCase().includes(q) ||
          (inv.pdl_prm || '').toLowerCase().includes(q)
        );
      });
  }, [invoices, periodPreset, monthFilter, invoiceStatusFilter, invoiceSearch]);

  // Reset pagination when filters change
  useEffect(() => {
    setInvoicePage(0);
  }, [invoiceSearch, invoiceStatusFilter, periodPreset, monthFilter]);

  const invoicePageCount = Math.ceil(filteredInvoices.length / INVOICES_PER_PAGE);
  const pagedInvoices = filteredInvoices.slice(
    invoicePage * INVOICES_PER_PAGE,
    (invoicePage + 1) * INVOICES_PER_PAGE
  );

  // ── Billing health banner ──
  const billingHealth = useMemo(() => {
    if (!summary) return null;
    return computeBillingHealthState(summary, allInsights);
  }, [summary, allInsights]);

  const activeLoss = useMemo(
    () => allInsights.filter(isActiveInsight).reduce((s, i) => s + (i.estimated_loss_eur || 0), 0),
    [allInsights]
  );

  // Top insight by estimated loss — for hero card
  const topInsight = useMemo(() => {
    const active = allInsights.filter(isActiveInsight).filter((i) => i.estimated_loss_eur > 0);
    if (!active.length) return null;
    return active.reduce(
      (max, i) => (i.estimated_loss_eur > max.estimated_loss_eur ? i : max),
      active[0]
    );
  }, [allInsights]);

  const [billingTrend, setBillingTrend] = useState(null);
  const snapshotScope = useMemo(
    () => ({
      orgId: scope?.orgId,
      scopeType: 'billing',
      scopeId: scope?.orgId || 'all',
    }),
    [scope?.orgId]
  );

  useEffect(() => {
    if (!billingHealth) return;
    const prev = loadHealthSnapshot('billing', snapshotScope);
    setBillingTrend(computeHealthTrend(billingHealth, prev));
    saveHealthSnapshot('billing', billingHealth, snapshotScope);
  }, [billingHealth, snapshotScope]);

  async function handleSeedDemo() {
    setSeeding(true);
    try {
      await seedBillingDemo();
      track('billing_seed_demo');
      toast('Données de démonstration générées avec succès', 'success');
      await fetchData();
    } catch {
      toast('Erreur lors de la génération des données démo', 'error');
    }
    setSeeding(false);
  }

  async function handleAuditAll() {
    setAuditing(true);
    try {
      await auditAllInvoices();
      track('billing_audit_all');
      toast('Audit terminé — les anomalies détectées sont affichées ci-dessous', 'success');
      await fetchData();
    } catch {
      toast("Erreur lors de l'audit", 'error');
    }
    setAuditing(false);
  }

  function handleCsvClick() {
    csvInputRef.current?.click();
  }

  async function handleCsvImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 50 * 1024 * 1024) {
      toast('Fichier trop volumineux (max 50 Mo)', 'error');
      return;
    }
    try {
      const result = await importInvoicesCsv(file);
      track('billing_csv_import', { filename: file.name });
      const imported = result?.imported ?? result?.rows_inserted ?? 0;
      const skipped = result?.skipped ?? result?.rows_skipped ?? 0;
      if (skipped > 0 && imported === 0) {
        toast(`${skipped} facture(s) déjà importée(s) — aucun doublon créé.`, 'info');
      } else if (skipped > 0) {
        toast(`${imported} facture(s) importée(s), ${skipped} doublon(s) ignoré(s).`, 'success');
      } else if (imported > 0) {
        toast(`Import CSV réussi : ${imported} facture(s) importée(s)`, 'success');
      } else {
        toast('Import CSV terminé — aucune facture à importer.', 'info');
      }
      await fetchData();
    } catch {
      toast("Erreur lors de l'import CSV", 'error');
    }
    e.target.value = '';
  }

  async function handleResolveInsight(insightId) {
    try {
      await resolveBillingInsight(insightId);
      track('billing_insight_resolved', { insight_id: insightId });
      toast('Anomalie marquée comme résolue', 'success');
      await fetchData();
    } catch {
      toast("Erreur lors de la résolution de l'anomalie", 'error');
    }
  }

  function handlePdfClick() {
    pdfInputRef.current?.click();
  }

  async function handlePdfImport(e) {
    const file = e.target.files?.[0];
    if (!file || !pdfSiteId) return;
    if (file.size > 20 * 1024 * 1024) {
      toast('Fichier trop volumineux (max 20 Mo)', 'error');
      return;
    }
    try {
      const result = await importInvoicesPdf(Number(pdfSiteId), file);
      track('billing_pdf_import', { filename: file.name });
      toast(
        `Import PDF réussi : facture ${result?.invoice_id ?? ''} (confiance ${result?.confidence ?? '?'})`,
        'success'
      );
      await fetchData();
    } catch {
      toast("Erreur lors de l'import PDF", 'error');
    }
    e.target.value = '';
  }

  function handleOpenCreateAction(insight) {
    openActionDrawer(
      {
        prefill: {
          titre: insight?.message || '',
          type: 'facture',
          impact_eur: insight?.estimated_loss_eur || '',
          description: insight?.message || '',
        },
        siteId: insight?.site_id,
        sourceType: 'billing',
        sourceId: insight ? String(insight.id) : null,
        idempotencyKey: insight ? `billing-insight:${insight.id}` : null,
      },
      {
        onSave: (result) => {
          const insightId = insight?.id;
          const actionId = result?.id;
          if (insightId) {
            setActionMap((prev) => new Map([...prev, [insightId, actionId || true]]));
          }
          track('billing_create_action', { insight_id: insightId, action_id: actionId });
          toast("Action créée — visible dans le Plan d'actions", 'success');
        },
      }
    );
  }

  function handleExportCsv() {
    const params = new URLSearchParams();
    if (siteFilter) params.set('site_id', siteFilter);
    if (insightFilter !== 'all') params.set('status', insightFilter);
    const qs = params.toString();
    window.open(`/api/bill/anomalies/csv${qs ? '?' + qs : ''}`, '_blank');
    track('billing_export_csv');
  }

  const hasData = summary && summary.total_invoices > 0;

  if (loading && !summary) {
    return (
      <PageShell icon={FileText} title="Facturation" subtitle="Chargement...">
        <SkeletonKpi count={5} />
        <SkeletonTable rows={5} cols={6} />
      </PageShell>
    );
  }

  if (loadError && !summary) {
    return (
      <PageShell icon={FileText} title="Facturation">
        <ErrorState message={loadError} onRetry={fetchData} />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={FileText}
      title="Facturation"
      subtitle="Vérifiez vos factures : PROMEOS recalcule le montant attendu et détecte les écarts."
      hideHeader
      actions={
        <>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={!pdfSiteId}
            onClick={handleCsvClick}
            title={!pdfSiteId ? 'Sélectionnez un site' : undefined}
          >
            <Upload size={14} /> Importer CSV
          </Button>
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv"
            className="sr-only"
            onChange={handleCsvImport}
          />
          <div className="inline-flex items-center gap-1">
            <select
              value={pdfSiteId}
              onChange={(e) => setPdfSiteId(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400"
            >
              <option value="">Site…</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nom}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={!pdfSiteId}
              onClick={handlePdfClick}
              title={!pdfSiteId ? 'Sélectionnez un site' : undefined}
            >
              <Upload size={14} /> Importer PDF
            </Button>
            <input
              ref={pdfInputRef}
              type="file"
              accept=".pdf"
              className="sr-only"
              onChange={handlePdfImport}
            />
          </div>
          {hasData && (
            <Tooltip
              text={
                (summary?.distinct_months ?? summary?.total_invoices ?? 0) < 3
                  ? 'Minimum 3 mois de factures requis'
                  : ''
              }
            >
              <Button
                size="sm"
                onClick={handleAuditAll}
                disabled={
                  auditing || (summary?.distinct_months ?? summary?.total_invoices ?? 0) < 3
                }
              >
                <Play size={14} /> {auditing ? 'Audit...' : 'Auditer tout'}
              </Button>
            </Tooltip>
          )}
          {!hasData && isExpert && (
            <Button onClick={handleSeedDemo} disabled={seeding}>
              <Zap size={14} /> {seeding ? 'Génération...' : 'Générer démo'}
            </Button>
          )}
          <button
            onClick={fetchData}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600"
            title="Rafraîchir"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </>
      }
    >
      {/* Sprint 2 refonte — header éditorial Sol */}
      <SolPageHeader
        kicker="Facturation · shadow billing PROMEOS"
        title="Vos factures"
        titleEm=" — vérifiées, recalculées, expliquées"
        narrative={
          <>
            Chaque facture est recalculée côté PROMEOS à partir de vos consommations — <em>les
            écarts sont détectés automatiquement</em>.
          </>
        }
        subNarrative="Si un fournisseur a oublié une bascule d'accise ou appliqué le mauvais taux CTA, vous le verrez ici avant même qu'il s'en rende compte."
      />

      {/* CTA vers achat énergie */}
      <button
        onClick={() => navigate('/achat-energie')}
        className="text-sm text-blue-600 hover:underline flex items-center gap-1"
      >
        Optimiser l'achat énergie →
      </button>

      {/* Navigation interne Facturation */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        <span className="px-3 py-1.5 text-sm font-medium rounded-md bg-white text-blue-700 shadow-sm">
          Anomalies & Audit
        </span>
        <Link
          to={`/billing${siteFilter ? `?site_id=${siteFilter}` : ''}`}
          className="px-3 py-1.5 text-sm font-medium rounded-md text-gray-500 hover:text-gray-700 hover:bg-white/60 transition"
        >
          <span className="flex items-center gap-1.5">
            <CalendarRange size={14} />
            Chronologie & Couverture
          </span>
        </Link>
      </div>

      {/* Breadcrumb filtres actifs */}
      {(siteFilter || monthFilter) && (
        <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
          {siteFilter && (
            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full">
              Site : {siteFilter}
            </span>
          )}
          {monthFilter && (
            <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded-full">
              Mois : {monthFilter}
            </span>
          )}
          <button
            className="text-gray-400 hover:text-gray-600 underline"
            onClick={() => {
              setSiteFilter('');
              setMonthFilter('');
            }}
          >
            Réinitialiser filtres
          </button>
        </div>
      )}

      {/* Shadow billing explainer — methodology block */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
        <div className="flex items-start gap-3">
          <Zap size={16} className="mt-0.5 shrink-0 text-blue-600" />
          <div>
            <span className="font-semibold">Comment ça marche ?</span> PROMEOS recalcule le montant
            attendu de chaque facture à partir de votre consommation réelle, de votre contrat et des
            tarifs réglementaires (TURPE, accise, TVA). Si l'écart dépasse 10 %, une anomalie est
            signalée.
          </div>
        </div>
        {isExpert && (
          <details className="mt-2 ml-7">
            <summary className="cursor-pointer text-[11px] font-medium text-blue-700 hover:text-blue-900">
              Méthodologie détaillée
            </summary>
            <div className="mt-1.5 text-[11px] text-blue-700 space-y-1.5 leading-relaxed">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div>
                  <span className="font-semibold">Données réelles</span>
                  <p className="text-blue-600">
                    Consommation (kWh) issue des compteurs ou factures importées.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Données contractuelles</span>
                  <p className="text-blue-600">
                    Prix fourniture, puissance souscrite, option tarifaire — extraits de votre
                    contrat.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Tarifs réglementaires</span>
                  <p className="text-blue-600">
                    TURPE (C5 BT), accise électricité, CTA, TVA — catalogue PROMEOS versionné.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Valeurs par défaut</span>
                  <p className="text-blue-600">
                    Si le contrat est absent, un prix moyen marché est utilisé (indiqué « estimé »).
                  </p>
                </div>
              </div>
              <p className="border-t border-blue-200 pt-1.5">
                <span className="font-semibold">Couverture :</span> fourniture, réseau (TURPE),
                taxes (accise + CTA), TVA, abonnement.{' '}
                <span className="font-semibold">Non couvert :</span> pénalités dépassement, services
                complémentaires, ajustements rétroactifs.
              </p>
            </div>
          </details>
        )}
      </div>

      {/* Billing Health Banner */}
      {billingHealth && (
        <HealthSummary
          healthState={billingHealth}
          onNavigate={(path) => {
            if (path === '/bill-intel') {
              anomaliesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
              navigate(path);
            }
          }}
          compact
          trend={billingTrend}
        />
      )}

      {/* Step 15: Summary phrase */}
      {summary &&
        (() => {
          const count = summary.total_insights || 0;
          if (count === 0) {
            return (
              <p
                className="text-sm text-green-700 bg-green-50 rounded-lg px-4 py-2"
                data-testid="billing-summary-phrase"
              >
                Toutes les factures sont cohérentes. Aucune action requise.
              </p>
            );
          }
          const lossStr =
            activeLoss >= 1000
              ? `${(activeLoss / 1000).toFixed(1)} k€`
              : `${Math.round(activeLoss)} €`;
          return (
            <p
              className="text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-2"
              data-testid="billing-summary-phrase"
            >
              {count} anomalie{count > 1 ? 's' : ''} détectée{count > 1 ? 's' : ''} pour un écart
              estimé de {lossStr}.
              {isExpert &&
                ` Facturation théorique active — ${summary.total_invoices} factures analysées.`}
            </p>
          );
        })()}

      {/* Summary cards */}
      {summary && (
        <>
          <div className="grid grid-cols-5 gap-4">
            <SummaryCard
              icon={FileText}
              label="Factures"
              value={summary.total_invoices}
              color="blue"
            />
            <SummaryCard
              icon={Euro}
              label="Total €"
              value={fmtEur(summary.total_eur)}
              color="indigo"
            />
            <SummaryCard
              icon={Zap}
              label={
                <>
                  Total <Explain term="kwh">kWh</Explain>
                </>
              }
              value={fmtKwh(Math.round(summary.total_kwh))}
              color="purple"
            />
            <SummaryCard
              icon={AlertTriangle}
              label={<Explain term="anomalie">Anomalies</Explain>}
              value={summary.total_insights}
              color="red"
            />
            <SummaryCard
              icon={TrendingUp}
              label="Pertes estimées"
              value={fmtEur(activeLoss)}
              color="orange"
            />
          </div>
          {/* Step 15: Billing KPI messages */}
          <div className="flex flex-col gap-1">
            {(() => {
              const msg = getKpiMessage('billing_total_cost', summary.total_eur, {
                sitesCount: siteFilter ? 1 : sites.length,
              });
              if (!msg) return null;
              return (
                <p
                  className={`text-xs px-1 ${
                    msg.severity === 'crit'
                      ? 'text-red-600'
                      : msg.severity === 'warn'
                        ? 'text-amber-600'
                        : 'text-gray-500'
                  }`}
                  data-testid="kpi-message-billing-cost"
                >
                  {isExpert ? msg.expert : msg.simple}
                </p>
              );
            })()}
            {(() => {
              const msg = getKpiMessage('billing_anomalies_count', summary.total_insights, {
                totalLossEur: activeLoss,
              });
              if (!msg) return null;
              return (
                <p
                  className={`text-xs px-1 ${
                    msg.severity === 'crit'
                      ? 'text-red-600'
                      : msg.severity === 'warn'
                        ? 'text-amber-600'
                        : 'text-gray-500'
                  }`}
                  data-testid="kpi-message-billing-anomalies"
                >
                  {isExpert ? msg.expert : msg.simple}
                </p>
              );
            })()}
          </div>
        </>
      )}
      {isExpert && summary && (
        <div className="flex items-center gap-4 text-xs text-gray-500 bg-gray-50 rounded-lg px-4 py-2">
          <span>Source : PROMEOS Bill Intel v2</span>
          <span>·</span>
          <span>Couverture : {summary.coverage_months || '?'} mois</span>
          <span>·</span>
          <span>
            Dernière maj : {summary.last_updated || new Date().toLocaleDateString('fr-FR')}
          </span>
          <span>·</span>
          <span>Moteur : {summary.engine_version || 'rules_v2'}</span>
        </div>
      )}

      {/* No data state */}
      {!loading && !hasData && (
        <EmptyState
          variant="unconfigured"
          icon={FileText}
          title="Aucune facture importée"
          text="Importez des factures pour détecter les anomalies de facturation (surfacturation, doublons, dérives). Pourquoi c'est important : chaque anomalie non détectée est un surcoût invisible."
          ctaLabel="Importer des factures"
          onCta={() => navigate('/consommations/import')}
          actions={
            <div className="flex items-center gap-3">
              {isExpert && (
                <Button onClick={handleSeedDemo} disabled={seeding} variant="secondary">
                  <Zap size={14} /> {seeding ? 'Génération...' : 'Générer démo'}
                </Button>
              )}
              <Button type="button" variant="secondary" onClick={handleCsvClick}>
                <Upload size={14} /> Importer CSV
              </Button>
            </div>
          }
        />
      )}

      {/* Top anomalie — hero card */}
      {topInsight && (
        <div
          className="flex items-center gap-4 p-4 bg-red-50 border border-red-200 rounded-lg cursor-pointer hover:bg-red-100 transition"
          onClick={() => setDrawerInsightId(topInsight.id)}
          data-testid="top-anomaly-hero"
        >
          <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center shrink-0">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-red-500 font-medium uppercase tracking-wide">
              Anomalie prioritaire
            </p>
            <p className="text-sm font-semibold text-gray-900 mt-0.5 truncate">
              {topInsight.message}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {TYPE_LABELS[topInsight.type] || topInsight.type}
              {topInsight.site_label && ` · ${topInsight.site_label}`}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-lg font-bold text-red-600">
              {topInsight.estimated_loss_eur.toLocaleString('fr-FR')} €
            </p>
            <p className="text-xs text-gray-400">écart estimé</p>
          </div>
          <ArrowRight size={16} className="text-red-400 shrink-0" />
        </div>
      )}

      {/* Insights with workflow filter */}
      {insights.length > 0 || insightFilter !== 'all' ? (
        <div ref={anomaliesRef}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-semibold text-gray-700">
                <Explain term="anomalie">Anomalies</Explain> détectées ({insights.length})
              </h3>
              <Button variant="secondary" size="sm" onClick={handleExportCsv}>
                <Download size={14} /> Exporter CSV
              </Button>
            </div>
            <div className="flex items-center gap-1">
              {INSIGHT_FILTER_OPTIONS.map((opt) => {
                const count =
                  opt.value === 'all'
                    ? allInsights.length
                    : allInsights.filter((i) => (i.insight_status || i.status) === opt.value)
                        .length;
                return (
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
                    <span className="ml-1 opacity-70">{count}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="space-y-2">
            {insights.map((insight) => {
              const istatus = VALID_STATUSES.includes(insight.insight_status)
                ? insight.insight_status
                : 'open';
              return (
                <Card key={insight.id} className="border-l-4 border-l-red-300">
                  <CardBody className="flex items-center gap-4">
                    <AlertTriangle
                      size={18}
                      className={
                        insight.severity === 'critical'
                          ? 'text-red-600'
                          : insight.severity === 'high'
                            ? 'text-orange-600'
                            : 'text-amber-500'
                      }
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          {[
                            'shadow_gap',
                            'unit_price_high',
                            'duplicate_invoice',
                            'consumption_spike',
                            'price_drift',
                          ].includes(insight.type) ? (
                            <Explain term={insight.type}>{TYPE_LABELS[insight.type]}</Explain>
                          ) : insight.type === 'ttc_coherence' ? (
                            <>
                              Cohérence <Explain term="ttc">TTC</Explain>
                            </>
                          ) : insight.type === 'reseau_mismatch' ? (
                            <>
                              Écart réseau / <Explain term="turpe">TURPE</Explain>
                            </>
                          ) : insight.type === 'taxes_mismatch' ? (
                            <>
                              Écart taxes / <Explain term="accise">accise</Explain>
                            </>
                          ) : insight.type === 'negative_kwh' ? (
                            <>
                              <Explain term="kwh">kWh</Explain> négatifs
                            </>
                          ) : (
                            TYPE_LABELS[insight.type] || insight.type
                          )}
                        </span>
                        <Badge status={SEVERITY_BADGE[insight.severity] || 'neutral'}>
                          {SEVERITY_LABELS[insight.severity] || insight.severity}
                        </Badge>
                        {insight.supplier && (
                          <span className="text-xs text-zinc-500">{insight.supplier}</span>
                        )}
                        {isExpert && (
                          <span className="text-[10px] font-mono text-gray-400">#{insight.id}</span>
                        )}
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${INSIGHT_STATUS_COLORS[istatus] || INSIGHT_STATUS_COLORS.open}`}
                        >
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
                        {insight.estimated_loss_eur.toLocaleString('fr-FR')} €
                      </span>
                    )}
                    {istatus !== 'resolved' && istatus !== 'false_positive' && (
                      <button
                        onClick={() => handleResolveInsight(insight.id)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                          text-green-700 bg-green-50 hover:bg-green-100 transition-colors whitespace-nowrap"
                        title="Marquer comme résolu"
                      >
                        <CheckCircle2 size={14} /> Résolu
                      </button>
                    )}
                    {actionMap.has(insight.id) ? (
                      <button
                        onClick={() => setViewActionId(actionMap.get(insight.id))}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                          text-green-700 bg-green-50 hover:bg-green-100 transition-colors whitespace-nowrap"
                      >
                        ✓ Voir l'action
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenCreateAction(insight)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                          text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors whitespace-nowrap"
                        title="Créer une action"
                      >
                        Créer une action
                      </button>
                    )}
                    <button
                      onClick={() => setDrawerInsightId(insight.id)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                        text-purple-700 bg-purple-50 hover:bg-purple-100 transition-colors whitespace-nowrap"
                    >
                      Comprendre l'écart
                    </button>
                    <button
                      onClick={() => {
                        setDossierSource({
                          sourceType: 'billing',
                          sourceId: String(insight.id),
                          label: insight.message,
                        });
                        getInsightDetail(insight.id)
                          .then(setDossierInsightDetail)
                          .catch(() => setDossierInsightDetail(null));
                      }}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                        text-gray-600 bg-gray-50 hover:bg-gray-100 transition-colors whitespace-nowrap"
                      title="Exporter le dossier"
                    >
                      <Printer size={12} /> Dossier
                    </button>
                  </CardBody>
                </Card>
              );
            })}
            {insights.length === 0 && insightFilter !== 'all' && (
              <p className="text-sm text-gray-400 text-center py-4">
                Aucune anomalie avec le statut "
                {INSIGHT_FILTER_OPTIONS.find((o) => o.value === insightFilter)?.label}".
              </p>
            )}
          </div>
        </div>
      ) : null}

      {/* Invoices table */}
      {(filteredInvoices.length > 0 || invoiceSearch || invoiceStatusFilter) && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Factures ({filteredInvoices.length}
            {monthFilter ? ` — ${monthFilter}` : ''})
          </h3>
          {/* Filter bar */}
          <div className="flex flex-wrap gap-2 mb-3 items-center">
            <input
              type="text"
              placeholder="N° facture ou PDL…"
              value={invoiceSearch}
              onChange={(e) => setInvoiceSearch(e.target.value)}
              className="border border-gray-200 rounded px-2 py-1 text-sm w-48 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <select
              value={periodPreset}
              onChange={(e) => {
                setPeriodPreset(e.target.value);
                if (e.target.value !== 'specific') setMonthFilter('');
              }}
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
                onChange={(e) => setMonthFilter(e.target.value)}
                className="border border-gray-200 rounded px-2 py-1 text-sm"
              />
            )}
            {['', 'imported', 'audited', 'anomaly', 'archived'].map((s) => (
              <button
                key={s}
                onClick={() => setInvoiceStatusFilter(s)}
                className={`px-2 py-1 rounded text-xs border ${
                  invoiceStatusFilter === s
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                }`}
              >
                {s === ''
                  ? 'Tous'
                  : s === 'imported'
                    ? 'Importé'
                    : s === 'audited'
                      ? 'Audité'
                      : s === 'anomaly'
                        ? 'Anomalie'
                        : 'Archivé'}
              </button>
            ))}
          </div>
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      N° facture
                    </th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      Période
                    </th>
                    <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      Total EUR
                    </th>
                    <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      <Explain term="kwh">kWh</Explain>
                    </th>
                    <th className="text-center px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      Statut
                    </th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      Source
                    </th>
                    {isExpert && (
                      <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                        €/kWh
                      </th>
                    )}
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">
                      Type énergie
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInvoices.length === 0 && (
                    <tr>
                      <td colSpan={isExpert ? 8 : 7} className="py-8">
                        <EmptyState
                          variant="empty"
                          title="Aucune facture ne correspond"
                          text="Essayez d'autres critères de recherche ou de filtrage."
                          ctaLabel="Réinitialiser"
                          onCta={() => {
                            setInvoiceSearch('');
                            setInvoiceStatusFilter('');
                            setPeriodPreset('all');
                            setMonthFilter('');
                          }}
                        />
                      </td>
                    </tr>
                  )}
                  {pagedInvoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-medium text-gray-900">
                        {inv.invoice_number}
                      </td>
                      <td className="px-4 py-2.5 text-gray-600">
                        {inv.period_start && inv.period_end
                          ? `${inv.period_start} → ${inv.period_end}`
                          : inv.period_start || '-'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium">
                        {inv.total_eur ? `${inv.total_eur.toLocaleString('fr-FR')} €` : '-'}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {inv.energy_kwh ? inv.energy_kwh.toLocaleString('fr-FR') : '-'}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[inv.status] || STATUS_COLORS.imported}`}
                        >
                          {STATUS_LABELS[inv.status] || STATUS_LABELS.imported}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500">{inv.source || '-'}</td>
                      {isExpert && (
                        <td className="px-4 py-2.5 text-right font-mono text-xs">
                          {inv.total_eur && inv.energy_kwh
                            ? (inv.total_eur / inv.energy_kwh).toFixed(4)
                            : '-'}
                        </td>
                      )}
                      <td className="px-4 py-2.5 text-gray-500">{inv.energy_type || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-2 border-t border-gray-100 flex items-center justify-between">
              <TrustBadge
                source="PROMEOS Bill Intel"
                period="données importées"
                confidence="medium"
              />
              {invoicePageCount > 1 && (
                <div className="flex items-center gap-2 text-sm">
                  <button
                    onClick={() => setInvoicePage((p) => Math.max(0, p - 1))}
                    disabled={invoicePage === 0}
                    className="px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    ←
                  </button>
                  <span className="text-gray-500">
                    {invoicePage * INVOICES_PER_PAGE + 1}–
                    {Math.min((invoicePage + 1) * INVOICES_PER_PAGE, filteredInvoices.length)} sur{' '}
                    {filteredInvoices.length}
                  </span>
                  <button
                    onClick={() => setInvoicePage((p) => Math.min(invoicePageCount - 1, p + 1))}
                    disabled={invoicePage >= invoicePageCount - 1}
                    className="px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    →
                  </button>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Action Drawer — managed by ActionDrawerContext */}

      {viewActionId && (
        <ActionDetailDrawer
          action={{ id: viewActionId }}
          open={!!viewActionId}
          onClose={() => setViewActionId(null)}
          onUpdate={() => fetchData()}
        />
      )}

      <InsightDrawer
        open={!!drawerInsightId}
        onClose={() => setDrawerInsightId(null)}
        insightId={drawerInsightId}
      />

      {/* Dossier print view (Étape 5) */}
      <DossierPrintView
        open={!!dossierSource}
        onClose={() => {
          setDossierSource(null);
          setDossierInsightDetail(null);
        }}
        sourceType={dossierSource?.sourceType}
        sourceId={dossierSource?.sourceId}
        sourceLabel={dossierSource?.label}
        insightDetail={dossierInsightDetail}
      />
    </PageShell>
  );
}

function SummaryCard({ icon: Icon, label, value, color }) {
  const bg =
    {
      blue: 'bg-blue-50',
      indigo: 'bg-indigo-50',
      purple: 'bg-purple-50',
      red: 'bg-red-50',
      orange: 'bg-orange-50',
    }[color] || 'bg-gray-50';
  const textColor =
    {
      blue: 'text-blue-700',
      indigo: 'text-indigo-700',
      purple: 'text-purple-700',
      red: 'text-red-700',
      orange: 'text-orange-700',
    }[color] || 'text-gray-700';
  const iconColor =
    {
      blue: 'text-blue-500',
      indigo: 'text-indigo-500',
      purple: 'text-purple-500',
      red: 'text-red-500',
      orange: 'text-orange-500',
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
