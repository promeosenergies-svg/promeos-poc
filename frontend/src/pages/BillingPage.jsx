/**
 * PROMEOS — BillingPage (V70)
 * Timeline & Couverture Facturation : suivi mensuel, détection périodes manquantes.
 * Scope unifié via ScopeContext, filtres avancés, import contextuel.
 * Route: /billing (alias /facturation)
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CalendarRange,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Upload,
  Zap,
  Search,
} from 'lucide-react';
import {
  getBillingPeriods,
  getCoverageSummary,
  getMissingPeriods,
  importInvoicesCsv,
  importInvoicesPdf,
} from '../services/api';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { Card, CardBody, Button, Badge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import CoverageBar from '../components/CoverageBar';
import BillingTimeline from '../components/BillingTimeline';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useScope } from '../contexts/ScopeContext';
import { useToast } from '../ui/ToastProvider';

const PAGE_TITLE = 'Timeline & Couverture Facturation';

function KpiChip({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-gray-100 shadow-sm">
      <Icon size={16} className={color} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className={`text-lg font-bold ${color}`}>{value}</p>
      </div>
    </div>
  );
}

export default function BillingPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isExpert } = useExpertMode();
  const { selectedSiteId: scopeSiteId, scopeLabel, orgSites } = useScope();
  const { toast } = useToast();

  // Filtres depuis l'URL (?site_id=X&month=YYYY-MM) — init depuis scope global
  const [siteFilter, setSiteFilter] = useState(
    searchParams.get('site_id') || (scopeSiteId ? String(scopeSiteId) : '')
  );
  const [activeMonth, _setActiveMonth] = useState(searchParams.get('month') || '');

  const [summary, setSummary] = useState(null);
  const [periods, setPeriods] = useState([]);
  const [periodsTotal, setPeriodsTotal] = useState(0);
  const [periodsOffset, setPeriodsOffset] = useState(0);
  const [missingPeriods, setMissingPeriods] = useState([]);

  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const [actionMap, setActionMap] = useState(new Map());
  const { openActionDrawer } = useActionDrawer();

  // Filtres avancés
  const [statusFilter, setStatusFilter] = useState('all');
  const [periodPreset, setPeriodPreset] = useState('all');
  const [timelineSearch, setTimelineSearch] = useState('');
  const [sortMode, setSortMode] = useState('date_desc');

  // Import contextuel
  const [importContext, setImportContext] = useState(null);
  const csvInputRef = useRef(null);
  const pdfInputRef = useRef(null);

  const LIMIT = 24;

  // Scope indicators
  const scopeHasSite = !!scopeSiteId;
  const localFilterActive = siteFilter && String(siteFilter) !== String(scopeSiteId || '');

  // Sync scope global → local
  useEffect(() => {
    setSiteFilter(scopeSiteId ? String(scopeSiteId) : '');
    setPeriodsOffset(0);
  }, [scopeSiteId]);

  // Sync filtre → URL
  useEffect(() => {
    if (siteFilter) {
      setSearchParams({ site_id: siteFilter }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteFilter]);

  const fetchAll = useCallback(
    async (siteId, offset = 0, append = false) => {
      if (!append) setLoading(true);
      else setLoadingMore(true);
      setError(null);

      const params = {};
      if (siteId) params.site_id = siteId;

      // Critical: periods — si ça échoue, rien à afficher
      try {
        const periodsData = await getBillingPeriods({ ...params, limit: LIMIT, offset });
        setPeriodsTotal(periodsData.total);
        setPeriodsOffset(offset + periodsData.periods.length);
        if (append) {
          setPeriods((prev) => [...prev, ...periodsData.periods]);
        } else {
          setPeriods(periodsData.periods);
        }
      } catch (err) {
        const status = err?.response?.status;
        // Build comprehensive debug payload for Expert mode
        const debugPayload = {
          endpoint: err?.config?.url || '/billing/periods',
          params: err?.config?.params || params,
          status: status || 0,
          contentType: err?.response?.headers?.['content-type'] || 'N/A',
          bodySnippet:
            typeof err?.response?.data === 'string'
              ? err.response.data.slice(0, 120)
              : JSON.stringify(err?.response?.data || err?.message || 'no body').slice(0, 120),
          orgHeader: err?.config?.headers?.['X-Org-Id'] || 'missing',
        };
        if (isExpert) console.error('[BillingPage] getBillingPeriods FAILED:', debugPayload, err);

        if (status === 404 && siteId) {
          // P0: purge stale siteId from localStorage scope
          try {
            const raw = localStorage.getItem('promeos_scope');
            if (raw) {
              const scope = JSON.parse(raw);
              scope.siteId = null;
              localStorage.setItem('promeos_scope', JSON.stringify(scope));
            }
          } catch {
            /* ignore storage errors */
          }
          setSiteFilter('');
          const baseMsg = 'Site introuvable. Retour à la vue tous les sites.';
          if (isExpert) {
            setError(
              `${baseMsg} [debug: endpoint=${debugPayload.endpoint}, status=404, site_id=${siteId}, org=${debugPayload.orgHeader}, ct=${debugPayload.contentType}]`
            );
          } else {
            setError(baseMsg);
          }
        } else {
          const baseMsg = 'Impossible de charger les données de facturation.';
          if (isExpert) {
            setError(
              `${baseMsg} [debug: endpoint=${debugPayload.endpoint}, status=${debugPayload.status}, org=${debugPayload.orgHeader}, ct=${debugPayload.contentType}, body=${debugPayload.bodySnippet}]`
            );
          } else {
            setError(baseMsg);
          }
        }
        setLoading(false);
        setLoadingMore(false);
        return;
      }

      setLoading(false);
      setLoadingMore(false);

      // Non-bloquant : coverage-summary (best-effort, ne casse pas la timeline)
      if (offset === 0) {
        try {
          const summaryData = await getCoverageSummary(params);
          setSummary(summaryData);
        } catch (err) {
          if (isExpert) console.warn('[BillingPage] coverage-summary failed (non-bloquant):', err);
          setSummary(null);
        }
      }

      // Non-bloquant : missing-periods (best-effort)
      if (offset === 0) {
        try {
          const missingData = await getMissingPeriods({ limit: 10 });
          setMissingPeriods(missingData.items || []);
        } catch (err) {
          if (isExpert) console.warn('[BillingPage] getMissingPeriods failed (non-bloquant):', err);
          setMissingPeriods([]);
        }
      }
    },
    [isExpert]
  );

  useEffect(() => {
    fetchAll(siteFilter, 0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteFilter]);

  const handleLoadMore = () => {
    fetchAll(siteFilter, periodsOffset, true);
  };

  const handleCreateAction = (actionKey, period) => {
    if (actionMap.has(actionKey)) return;
    openActionDrawer(
      {
        prefill: {
          titre: `Période manquante : ${period.month_key}${period.missing_reason ? ' — ' + period.missing_reason : ''}`,
          type: 'facture',
          description: `Période manquante : ${period.month_key}`,
        },
        siteId: siteFilter ? parseInt(siteFilter, 10) : null,
        sourceType: 'billing',
        sourceId: actionKey,
      },
      {
        onSave: (result) => {
          setActionMap((prev) => new Map([...prev, [actionKey, result?.id || true]]));
        },
      }
    );
  };

  const hasMore = periodsOffset < periodsTotal;

  // Client-side filtering
  const filteredPeriods = useMemo(() => {
    let result = [...periods];

    // Period preset filter
    if (periodPreset !== 'all') {
      const now = new Date();
      const months = periodPreset === 'last3' ? 3 : periodPreset === 'last6' ? 6 : 12;
      const cutoff = new Date(now.getFullYear(), now.getMonth() - months, 1);
      const cutoffKey = `${cutoff.getFullYear()}-${String(cutoff.getMonth() + 1).padStart(2, '0')}`;
      result = result.filter((p) => p.month_key >= cutoffKey);
    }

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter((p) => p.coverage_status === statusFilter);
    }

    // Text search
    if (timelineSearch.trim()) {
      const q = timelineSearch.trim().toLowerCase();
      result = result.filter(
        (p) =>
          p.month_key?.toLowerCase().includes(q) ||
          p.pdl_prm?.toLowerCase().includes(q) ||
          p.site_name?.toLowerCase().includes(q) ||
          p.invoice_number?.toLowerCase().includes(q) ||
          p.missing_reason?.toLowerCase().includes(q)
      );
    }

    // Sort
    if (sortMode === 'date_desc') {
      result.sort((a, b) => (b.month_key || '').localeCompare(a.month_key || ''));
    } else if (sortMode === 'date_asc') {
      result.sort((a, b) => (a.month_key || '').localeCompare(b.month_key || ''));
    } else if (sortMode === 'amount_desc') {
      result.sort((a, b) => (b.total_amount ?? 0) - (a.total_amount ?? 0));
    } else if (sortMode === 'amount_asc') {
      result.sort((a, b) => (a.total_amount ?? 0) - (b.total_amount ?? 0));
    } else if (sortMode === 'priority_missing') {
      const order = { missing: 0, partial: 1, covered: 2 };
      result.sort((a, b) => {
        const diff = (order[a.coverage_status] ?? 3) - (order[b.coverage_status] ?? 3);
        return diff !== 0 ? diff : (b.month_key || '').localeCompare(a.month_key || '');
      });
    }

    return result;
  }, [periods, periodPreset, statusFilter, timelineSearch, sortMode]);

  const statusCounts = useMemo(
    () => ({
      all: periods.length,
      covered: periods.filter((p) => p.coverage_status === 'covered').length,
      partial: periods.filter((p) => p.coverage_status === 'partial').length,
      missing: periods.filter((p) => p.coverage_status === 'missing').length,
    }),
    [periods]
  );

  // Import contextuel handlers
  const handleImportClick = (siteId, monthKey, type) => {
    setImportContext({ siteId, monthKey });
    if (isExpert) console.log('[BillingPage] import click:', { siteId, monthKey, type });
    if (type === 'csv') csvInputRef.current?.click();
    else pdfInputRef.current?.click();
  };

  async function handleContextualCsvImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (isExpert) console.log('[BillingPage] CSV file selected:', file.name, importContext);
    try {
      await importInvoicesCsv(file);
      toast('Import CSV réussi', 'success');
      fetchAll(siteFilter, 0, false);
    } catch (err) {
      if (isExpert) console.error('[BillingPage] CSV import failed:', err);
      toast('Échec import CSV', 'error');
    }
    setImportContext(null);
    e.target.value = '';
  }

  async function handleContextualPdfImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (isExpert) console.log('[BillingPage] PDF file selected:', file.name, importContext);
    try {
      await importInvoicesPdf(importContext?.siteId, file);
      toast('Import PDF réussi', 'success');
      fetchAll(siteFilter, 0, false);
    } catch (err) {
      if (isExpert) console.error('[BillingPage] PDF import failed:', err);
      toast('Échec import PDF', 'error');
    }
    setImportContext(null);
    e.target.value = '';
  }

  if (loading) {
    return (
      <div className="p-6 space-y-4 max-w-4xl mx-auto">
        <SkeletonCard lines={1} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={6} />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <CalendarRange size={20} className="text-amber-600" />
          <h1 className="text-lg font-bold text-gray-900">{PAGE_TITLE}</h1>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => fetchAll(siteFilter, 0, false)}
          disabled={loading}
        >
          <RefreshCw size={14} /> Actualiser
        </Button>
      </div>

      {/* Filtres — scope-aware */}
      <div className="flex flex-wrap gap-2 items-center">
        {scopeHasSite ? (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
            Hérité : {orgSites.find((s) => s.id === scopeSiteId)?.nom || `Site ${scopeSiteId}`}
          </div>
        ) : (
          <select
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700"
            value={siteFilter}
            onChange={(e) => {
              setSiteFilter(e.target.value);
              setPeriodsOffset(0);
            }}
          >
            <option value="">Tous les sites</option>
            {orgSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nom}
              </option>
            ))}
          </select>
        )}
        {siteFilter && !scopeHasSite && (
          <Button size="sm" variant="ghost" onClick={() => setSiteFilter('')}>
            Réinitialiser
          </Button>
        )}
        {localFilterActive && (
          <div className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
            Vue filtrée : Site{' '}
            {orgSites.find((s) => String(s.id) === String(siteFilter))?.nom || siteFilter}
            <span className="text-amber-500">
              (scope global : {scopeLabel || 'Tous les sites'})
            </span>
          </div>
        )}
      </div>

      {/* Erreur */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-center gap-2">
          <AlertTriangle size={14} />
          {error}
          <Button size="xs" variant="ghost" onClick={() => fetchAll(siteFilter, 0, false)}>
            Réessayer
          </Button>
        </div>
      )}

      {/* KPIs + CoverageBar */}
      {summary && (
        <Card>
          <CardBody>
            <div className="flex flex-wrap gap-3 mb-4">
              <KpiChip
                icon={CheckCircle}
                label="Couverts"
                value={summary?.covered ?? 0}
                color="text-green-600"
              />
              <KpiChip
                icon={AlertTriangle}
                label="Partiels"
                value={summary?.partial ?? 0}
                color="text-orange-500"
              />
              <KpiChip
                icon={XCircle}
                label="Manquants"
                value={summary?.missing ?? 0}
                color="text-red-500"
              />
            </div>
            <CoverageBar
              covered={summary?.covered ?? 0}
              partial={summary?.partial ?? 0}
              missing={summary?.missing ?? 0}
              total={summary?.months_total ?? 0}
              minMonth={summary?.range?.min_month ?? '—'}
              maxMonth={summary?.range?.max_month ?? '—'}
            />
          </CardBody>
        </Card>
      )}

      {/* Périodes manquantes / partielles */}
      {missingPeriods.length > 0 && (
        <Card>
          <CardBody>
            <h2 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
              <AlertTriangle size={14} />
              Périodes manquantes ou incomplètes ({missingPeriods.length})
            </h2>
            <div className="space-y-2">
              {missingPeriods.slice(0, 5).map((item) => (
                <div
                  key={`${item.site_id}-${item.month_key}`}
                  className="flex items-center justify-between gap-3 px-3 py-2 bg-red-50 border border-red-100 rounded-lg"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant={item.coverage_status === 'missing' ? 'danger' : 'warning'}
                        size="xs"
                      >
                        {item.coverage_status === 'missing' ? 'Manquant' : 'Partiel'}
                      </Badge>
                      <span className="text-sm font-medium text-gray-800">{item.month_key}</span>
                      {item.site_name && (
                        <span className="text-xs text-gray-500">— {item.site_name}</span>
                      )}
                    </div>
                    {item.missing_reason && (
                      <p className="text-xs text-gray-500 mt-0.5">{item.missing_reason}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <Button
                      size="xs"
                      variant="secondary"
                      type="button"
                      onClick={() => handleImportClick(item.site_id, item.month_key, 'csv')}
                    >
                      <Upload size={11} /> CSV
                    </Button>
                    <Button
                      size="xs"
                      variant="secondary"
                      type="button"
                      onClick={() => handleImportClick(item.site_id, item.month_key, 'pdf')}
                    >
                      <Upload size={11} /> PDF
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      disabled={actionMap.has(`missing-${item.month_key}-${item.site_id}`)}
                      onClick={() =>
                        handleCreateAction(`missing-${item.month_key}-${item.site_id}`, item)
                      }
                    >
                      {actionMap.has(`missing-${item.month_key}-${item.site_id}`) ? (
                        '✓'
                      ) : (
                        <Zap size={11} />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Barre de filtres timeline */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white text-gray-700"
          value={periodPreset}
          onChange={(e) => setPeriodPreset(e.target.value)}
        >
          <option value="all">Toutes périodes</option>
          <option value="last3">3 derniers mois</option>
          <option value="last6">6 derniers mois</option>
          <option value="last12">12 derniers mois</option>
        </select>
        {[
          { key: 'all', label: 'Tous' },
          { key: 'covered', label: 'Couverts' },
          { key: 'partial', label: 'Partiels' },
          { key: 'missing', label: 'Manquants' },
        ].map((opt) => (
          <button
            key={opt.key}
            type="button"
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              statusFilter === opt.key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            onClick={() => setStatusFilter(opt.key)}
          >
            {opt.label} ({statusCounts[opt.key]})
          </button>
        ))}
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Mois, PDL, site..."
            value={timelineSearch}
            onChange={(e) => setTimelineSearch(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg pl-6 pr-2 py-1.5 bg-white text-gray-700 w-36"
          />
        </div>
        <select
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white text-gray-700"
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value)}
        >
          <option value="date_desc">Date desc</option>
          <option value="date_asc">Date asc</option>
          <option value="amount_desc">Montant desc</option>
          <option value="amount_asc">Montant asc</option>
          <option value="priority_missing">Priorité manquants</option>
        </select>
      </div>

      {/* Timeline complète */}
      <Card>
        <CardBody>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Timeline complète
            {periodsTotal > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                {filteredPeriods.length}/{periods.length} affichées ({periodsTotal} total)
              </span>
            )}
          </h2>
          {periods.length === 0 && !loading ? (
            <EmptyState
              icon={CalendarRange}
              title="Aucune facture"
              description="Importez des factures CSV ou PDF dans le module Facturation pour voir la timeline."
              action={
                <Button size="sm" onClick={() => navigate('/bill-intel')}>
                  Aller à la Facturation
                </Button>
              }
            />
          ) : (
            <>
              <BillingTimeline
                periods={filteredPeriods}
                siteId={siteFilter}
                activeMonth={activeMonth}
                onCreateAction={handleCreateAction}
                createdActions={new Set(actionMap.keys())}
                onImport={handleImportClick}
              />
              {hasMore && (
                <div className="mt-4 text-center">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                  >
                    {loadingMore ? 'Chargement...' : `Charger ${LIMIT} mois de plus`}
                  </Button>
                </div>
              )}
            </>
          )}
        </CardBody>
      </Card>

      {/* Hidden file inputs for contextual import */}
      <input
        ref={csvInputRef}
        type="file"
        accept=".csv"
        className="sr-only"
        onChange={handleContextualCsvImport}
      />
      <input
        ref={pdfInputRef}
        type="file"
        accept=".pdf"
        className="sr-only"
        onChange={handleContextualPdfImport}
      />

      {/* Action creation handled by ActionDrawerContext */}
    </div>
  );
}
