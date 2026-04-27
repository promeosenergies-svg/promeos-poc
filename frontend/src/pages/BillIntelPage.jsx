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
// Sprint 2 Vague B ét6' — labels FR centralisés (label_registries cross-vue).
import {
  BILLING_INSIGHT_TYPE_LABELS,
  BILLING_INSIGHT_STATUS_LABELS,
  BILLING_INVOICE_STATUS_LABELS,
  BILLING_SEVERITY_LABELS,
  BILLING_SEVERITY_BADGE,
} from '../domain/billing/billingLabels.fr';
// Sprint 1.5 — grammaire Sol industrialisée (ADR-001) sur /bill-intel
import SolPageHeader from '../ui/sol/SolPageHeader';
import SolNarrative from '../ui/sol/SolNarrative';
import SolWeekCards from '../ui/sol/SolWeekCards';
import SolPageFooter from '../ui/sol/SolPageFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';
import { scopeKicker } from '../utils/format';
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

const SEVERITY_BADGE = BILLING_SEVERITY_BADGE;

// Sprint 2 Vague A ét2 — récit Bill-Intel (doctrine v2 §5 + ADR-004).
// Sprint 2 Vague B ét6' — texte canonique migré dans
// `domain/billing/billingLabels.fr.js`. Cette table local ne porte que les
// 5 wrappers JSX qui encapsulent un `<Explain>` inline (kWh/TTC/TURPE/
// accise/shadow). Les 10 entrées plain-text sont consommées telles quelles
// depuis le registry — pas de duplication de wording.
const TYPE_LABELS = {
  ...BILLING_INSIGHT_TYPE_LABELS,
  shadow_gap: (
    <>
      Cette facture coûte plus que la <Explain term="shadow_billing">facturation théorique</Explain>
    </>
  ),
  unit_price_high: (
    <>
      Le prix au <Explain term="kwh">kWh</Explain> dépasse vos repères
    </>
  ),
  negative_kwh: (
    <>
      Une consommation négative en <Explain term="kwh">kWh</Explain> est apparue
    </>
  ),
  ttc_coherence: (
    <>
      Le total <Explain term="ttc">TTC</Explain> ne se reconstitue pas
    </>
  ),
  reseau_mismatch: (
    <>
      L'acheminement réseau dépasse le tarif <Explain term="turpe">TURPE</Explain> attendu
    </>
  ),
  taxes_mismatch: (
    <>
      Les taxes dépassent l'<Explain term="accise">accise</Explain> et la{' '}
      <Explain term="cta">CTA</Explain> en vigueur
    </>
  ),
  reconciliation_mismatch: (
    <>
      <Explain term="reconciliation_auto">Écart compteur / facture</Explain> détecté
    </>
  ),
};

const STATUS_COLORS = {
  imported: 'bg-gray-100 text-gray-700',
  validated: 'bg-blue-100 text-blue-700',
  audited: 'bg-green-100 text-green-700',
  anomaly: 'bg-red-100 text-red-700',
  archived: 'bg-gray-100 text-gray-500',
};

const STATUS_LABELS = BILLING_INVOICE_STATUS_LABELS;

const SEVERITY_LABELS = BILLING_SEVERITY_LABELS;

// Sprint 1.5bis P0-4 — palette migrée tokens warm Sol (audit Visual/UX 26/04 :
// arc-en-ciel yellow/blue/green/gray cassait la signature « journal en
// terrasse »). Inline style cf. Tailwind v4 bug arbitrary CSS variables.
const INSIGHT_STATUS_STYLES = {
  open: { background: 'var(--sol-attention-bg)', color: 'var(--sol-attention-fg)' },
  ack: { background: 'var(--sol-afaire-bg)', color: 'var(--sol-afaire-fg)' },
  resolved: { background: 'var(--sol-succes-bg)', color: 'var(--sol-succes-fg)' },
  false_positive: { background: 'var(--sol-ink-100)', color: 'var(--sol-ink-500)' },
};

const INSIGHT_STATUS_LABELS = BILLING_INSIGHT_STATUS_LABELS;

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
  const { org, scopedSites, selectedSiteId: scopeSiteId, scope } = useScope();
  const [searchParams] = useSearchParams();

  // Sprint 1.5 — briefing éditorial Sol §5 vue Bill-Intel (ADR-001).
  // Backend orchestre KPIs + narrative + week-cards via /api/pages/bill_intel/briefing.
  // Différenciateur §4.4 : shadow billing v4.2 décomposé TURPE/ATRD/accise/CTA/TVA.
  const {
    briefing: solBriefing,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('bill_intel', { persona: 'daily' });
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
      editorialHeader={
        <SolPageHeader
          kicker={solBriefing?.kicker || scopeKicker('FACTURATION', org?.nom, scopedSites?.length)}
          title={solBriefing?.title || 'Vos factures'}
          italicHook={solBriefing?.italicHook || 'shadow billing v4.2'}
          subtitle="Vérifiez vos factures : PROMEOS recalcule le montant attendu et détecte les écarts."
        />
      }
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
      {/* ── Préambule éditorial Sol §5 vue Bill-Intel (S1.5 — ADR-001) ──
          Shadow billing v4.2 — différenciateur §4.4 doctrine. KPIs CFO :
          Anomalies à traiter / Pertes à récupérer / Récupérations YTD.
          Audit fin S1.4 demandait Bill-Intel pour démontrer scaling
          au-delà du régulatoire (Investisseur P0). */}
      {solBriefingError && !solBriefing && (
        <SolNarrative error={solBriefingError} onRetry={solBriefingRefetch} />
      )}
      {solBriefing && (
        <SolNarrative
          kicker={null /* déjà rendu dans SolPageHeader éditorialHeader */}
          title={null /* idem — éviter doublon */}
          narrative={solBriefing.narrative}
          kpis={solBriefing.kpis}
        />
      )}
      {solBriefing && (
        <SolWeekCards
          cards={solBriefing.weekCards}
          fallbackBody={solBriefing.fallbackBody}
          tone={solBriefing.narrativeTone}
          onNavigate={navigate}
        />
      )}

      {/* CTA vers achat énergie — Sprint 1.5bis P0-4 token calme Sol */}
      <button
        onClick={() => navigate('/achat-energie')}
        className="text-sm hover:underline flex items-center gap-1"
        style={{ color: 'var(--sol-calme-fg)' }}
      >
        Optimiser l'achat énergie →
      </button>

      {/* Navigation interne Facturation — Sprint 1.5bis P0-4 token calme actif */}
      <div
        className="flex items-center gap-1 rounded-lg p-1 w-fit"
        style={{ background: 'var(--sol-ink-100)' }}
      >
        <span
          className="px-3 py-1.5 text-sm font-medium rounded-md shadow-sm"
          style={{ background: 'var(--sol-bg-paper)', color: 'var(--sol-calme-fg)' }}
        >
          Anomalies & Audit
        </span>
        <Link
          to={`/billing${siteFilter ? `?site_id=${siteFilter}` : ''}`}
          className="px-3 py-1.5 text-sm font-medium rounded-md hover:bg-white/60 transition"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          <span className="flex items-center gap-1.5">
            <CalendarRange size={14} />
            Chronologie & Couverture
          </span>
        </Link>
      </div>

      {/* Breadcrumb filtres actifs — Sprint 1.5bis P0-4 tokens warm Sol */}
      {(siteFilter || monthFilter) && (
        <div
          className="flex items-center gap-2 text-xs flex-wrap"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {siteFilter && (
            <span
              className="px-2 py-1 rounded-full"
              style={{ background: 'var(--sol-calme-bg)', color: 'var(--sol-calme-fg)' }}
            >
              Site : {siteFilter}
            </span>
          )}
          {monthFilter && (
            <span
              className="px-2 py-1 rounded-full"
              style={{ background: 'var(--sol-attention-bg)', color: 'var(--sol-attention-fg)' }}
            >
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

      {/* Shadow billing explainer — methodology block.
          Sprint 1.5bis P0-4 : palette migrée tokens calme Sol §6.2 (audit
          Visual 26/04 : bleu corporate cassait signature warm). */}
      <div
        className="border rounded-lg px-4 py-3 text-sm"
        style={{
          background: 'var(--sol-calme-bg)',
          borderColor: 'var(--sol-calme-fg)',
          color: 'var(--sol-calme-fg-hover)',
        }}
      >
        <div className="flex items-start gap-3">
          <Zap size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--sol-calme-fg)' }} />
          <div>
            <span className="font-semibold">Comment ça marche ?</span> PROMEOS recalcule le montant
            attendu de chaque facture à partir de votre consommation réelle, de votre contrat et des
            tarifs réglementaires (TURPE, accise, TVA). Si l'écart dépasse 10 %, une anomalie est
            signalée.
          </div>
        </div>
        {isExpert && (
          <details className="mt-2 ml-7">
            <summary
              className="cursor-pointer text-[11px] font-medium"
              style={{ color: 'var(--sol-calme-fg)' }}
            >
              Méthodologie détaillée
            </summary>
            <div
              className="mt-1.5 text-[11px] space-y-1.5 leading-relaxed"
              style={{ color: 'var(--sol-calme-fg)' }}
            >
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div>
                  <span className="font-semibold">Données réelles</span>
                  <p style={{ color: 'var(--sol-ink-700)' }}>
                    Consommation (kWh) issue des compteurs ou factures importées.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Données contractuelles</span>
                  <p style={{ color: 'var(--sol-ink-700)' }}>
                    Prix fourniture, puissance souscrite, option tarifaire — extraits de votre
                    contrat.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Tarifs réglementaires</span>
                  <p style={{ color: 'var(--sol-ink-700)' }}>
                    TURPE (C5 BT), accise électricité, CTA, TVA — catalogue PROMEOS versionné.
                  </p>
                </div>
                <div>
                  <span className="font-semibold">Valeurs par défaut</span>
                  <p style={{ color: 'var(--sol-ink-700)' }}>
                    Si le contrat est absent, un prix moyen marché est utilisé (indiqué « estimé »).
                  </p>
                </div>
              </div>
              <p
                className="pt-1.5"
                style={{ borderTop: '1px solid var(--sol-calme-fg)', opacity: 0.9 }}
              >
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

      {/* Top anomalie — hero card.
          Sprint 1.5bis P1 (audit a11y) : <div onClick> → role="button" tabIndex
          + keyboard handler Enter/Space + tokens warm Sol refuse (palette §6.2). */}
      {topInsight && (
        <div
          className="flex items-center gap-4 p-4 border rounded-lg cursor-pointer transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-refuse-fg)]"
          style={{
            background: 'var(--sol-refuse-bg)',
            borderColor: 'var(--sol-refuse-line)',
          }}
          onClick={() => setDrawerInsightId(topInsight.id)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setDrawerInsightId(topInsight.id);
            }
          }}
          role="button"
          tabIndex={0}
          aria-label={`Anomalie prioritaire : ${topInsight.message}, écart estimé ${topInsight.estimated_loss_eur.toLocaleString('fr-FR')} euros`}
          data-testid="top-anomaly-hero"
        >
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background: 'var(--sol-refuse-bg)',
              border: '1px solid var(--sol-refuse-line)',
            }}
          >
            <AlertTriangle size={20} style={{ color: 'var(--sol-refuse-fg)' }} />
          </div>
          <div className="flex-1 min-w-0">
            <p
              className="text-xs font-medium uppercase tracking-wide"
              style={{ color: 'var(--sol-refuse-fg)' }}
            >
              Anomalie prioritaire
            </p>
            <p
              className="text-sm font-semibold mt-0.5 truncate"
              style={{ color: 'var(--sol-ink-900)' }}
            >
              {topInsight.message}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--sol-ink-500)' }}>
              {TYPE_LABELS[topInsight.type] || topInsight.type}
              {topInsight.site_label && ` · ${topInsight.site_label}`}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p
              className="font-mono font-semibold tabular-nums"
              style={{ fontSize: '1.25rem', color: 'var(--sol-refuse-fg)' }}
            >
              {topInsight.estimated_loss_eur.toLocaleString('fr-FR')} €
            </p>
            <p className="text-xs" style={{ color: 'var(--sol-ink-500)' }}>
              écart estimé
            </p>
          </div>
          <ArrowRight size={16} className="shrink-0" style={{ color: 'var(--sol-refuse-fg)' }} />
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
            {/* Sprint 1.5bis P1 (audit a11y) : aria-pressed sur filter pills
                + tokens calme actif Sol §6.2. */}
            <div
              className="flex items-center gap-1"
              role="group"
              aria-label="Filtres anomalies par statut"
            >
              {INSIGHT_FILTER_OPTIONS.map((opt) => {
                const count =
                  opt.value === 'all'
                    ? allInsights.length
                    : allInsights.filter((i) => (i.insight_status || i.status) === opt.value)
                        .length;
                const isActive = insightFilter === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setInsightFilter(opt.value)}
                    aria-pressed={isActive}
                    className="px-2.5 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
                    style={
                      isActive
                        ? { background: 'var(--sol-calme-fg)', color: 'var(--sol-bg-paper)' }
                        : { background: 'var(--sol-ink-100)', color: 'var(--sol-ink-700)' }
                    }
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
                          {TYPE_LABELS[insight.type] || insight.type}
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
                          className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                          style={INSIGHT_STATUS_STYLES[istatus] || INSIGHT_STATUS_STYLES.open}
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
              {/* Sprint 1.5bis P1 (audit a11y) : <caption sr-only> + scope="col"
                  pour lecteurs d'écran. */}
              <table className="w-full text-sm">
                <caption className="sr-only">
                  Liste des factures importées avec montant, consommation, statut d'audit et type
                  d'énergie. Cliquez sur une ligne pour ouvrir le détail.
                </caption>
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th
                      scope="col"
                      className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      N° facture
                    </th>
                    <th
                      scope="col"
                      className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      Période
                    </th>
                    <th
                      scope="col"
                      className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      Total EUR
                    </th>
                    <th
                      scope="col"
                      className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      <Explain term="kwh">kWh</Explain>
                    </th>
                    <th
                      scope="col"
                      className="text-center px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      Statut
                    </th>
                    <th
                      scope="col"
                      className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
                      Source
                    </th>
                    {isExpert && (
                      <th
                        scope="col"
                        className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                      >
                        €/kWh
                      </th>
                    )}
                    <th
                      scope="col"
                      className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase"
                    >
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

      {/* Sprint 1.5 — SolPageFooter §5 (ADR-001).
          Source · Confiance · Mis à jour. Methodology URL pointe vers
          /methodologie/bill-intel-shadow (17 mécanismes audités). */}
      {solBriefing?.provenance && (
        <SolPageFooter
          source={solBriefing.provenance.source}
          confidence={solBriefing.provenance.confidence}
          updatedAt={solBriefing.provenance.updated_at}
          methodologyUrl={solBriefing.provenance.methodology_url}
        />
      )}
    </PageShell>
  );
}

// Sprint 1.5bis P0-4 — palette migrée tokens warm Sol §6.2 (audit Visual/UX
// 26/04 : 5 couleurs arc-en-ciel cassaient la signature « journal en
// terrasse »). Mapping sémantique :
//  · blue (Factures) → calme bleu-vert (volume neutre)
//  · indigo (Total €) → ink slate (statement comptable)
//  · purple (Total kWh) → ink slate (statement énergie)
//  · red (Anomalies) → attention ambre (signal)
//  · orange (Pertes €) → afaire corail (à-récupérer)
const SUMMARY_TONE = {
  blue: { bg: 'var(--sol-calme-bg)', fg: 'var(--sol-calme-fg)' },
  indigo: { bg: 'var(--sol-ink-100)', fg: 'var(--sol-ink-700)' },
  purple: { bg: 'var(--sol-ink-100)', fg: 'var(--sol-ink-700)' },
  red: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  orange: { bg: 'var(--sol-afaire-bg)', fg: 'var(--sol-afaire-fg)' },
};

function SummaryCard({ icon: Icon, label, value, color }) {
  const tone = SUMMARY_TONE[color] || SUMMARY_TONE.indigo;
  return (
    <Card>
      <CardBody style={{ background: tone.bg }}>
        <div className="flex items-center gap-2 mb-1">
          <Icon size={16} style={{ color: tone.fg, opacity: 0.75 }} />
          <p className="text-xs font-medium" style={{ color: 'var(--sol-ink-500)' }}>
            {label}
          </p>
        </div>
        <p
          className="font-mono font-semibold tabular-nums"
          style={{ fontSize: '1.875rem', lineHeight: '1.1', color: tone.fg }}
        >
          {value}
        </p>
      </CardBody>
    </Card>
  );
}
