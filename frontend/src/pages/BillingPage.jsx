/**
 * PROMEOS — BillingPage (V67)
 * Timeline & Couverture Facturation : suivi mensuel, détection périodes manquantes.
 * Route: /billing (alias /facturation)
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CalendarRange, AlertTriangle, CheckCircle, XCircle, RefreshCw, Upload, Zap } from 'lucide-react';
import {
  getBillingPeriods,
  getCoverageSummary,
  getMissingPeriods,
  createActionFromBillingInsight,
  getSites,
} from '../services/api';
import { Card, CardBody, Button, Badge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import CoverageBar from '../components/CoverageBar';
import BillingTimeline from '../components/BillingTimeline';

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

  // Filtre depuis l'URL (?site_id=X)
  const [siteFilter, setSiteFilter] = useState(searchParams.get('site_id') || '');
  const [sites, setSites] = useState([]);

  const [summary, setSummary] = useState(null);
  const [periods, setPeriods] = useState([]);
  const [periodsTotal, setPeriodsTotal] = useState(0);
  const [periodsOffset, setPeriodsOffset] = useState(0);
  const [missingPeriods, setMissingPeriods] = useState([]);

  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const [createdActions, setCreatedActions] = useState(new Set());

  const LIMIT = 24;

  // Sync filtre → URL
  useEffect(() => {
    if (siteFilter) {
      setSearchParams({ site_id: siteFilter }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [siteFilter]);

  const fetchAll = useCallback(async (siteId, offset = 0, append = false) => {
    if (!append) setLoading(true);
    else setLoadingMore(true);
    setError(null);

    const params = {};
    if (siteId) params.site_id = siteId;

    try {
      const [summaryData, periodsData, missingData] = await Promise.all([
        getCoverageSummary(params),
        getBillingPeriods({ ...params, limit: LIMIT, offset }),
        offset === 0 ? getMissingPeriods({ limit: 10 }) : Promise.resolve(null),
      ]);

      setSummary(summaryData);
      setPeriodsTotal(periodsData.total);
      setPeriodsOffset(offset + periodsData.periods.length);

      if (append) {
        setPeriods(prev => [...prev, ...periodsData.periods]);
      } else {
        setPeriods(periodsData.periods);
      }

      if (missingData) setMissingPeriods(missingData.items || []);
    } catch {
      setError('Impossible de charger les données de facturation.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchAll(siteFilter, 0, false);
  }, [siteFilter]);

  // Charger la liste des sites pour le filtre
  useEffect(() => {
    getSites({ limit: 200 }).catch(() => []).then(data => {
      setSites(Array.isArray(data?.sites) ? data.sites : Array.isArray(data) ? data : []);
    });
  }, []);

  const handleLoadMore = () => {
    fetchAll(siteFilter, periodsOffset, true);
  };

  const handleCreateAction = async (actionKey, period) => {
    if (createdActions.has(actionKey)) return;
    try {
      await createActionFromBillingInsight(
        `missing-${period.month_key}-${siteFilter || 'all'}`,
        `Période manquante : ${period.month_key}${period.missing_reason ? ' — ' + period.missing_reason : ''}`,
        siteFilter ? parseInt(siteFilter) : null,
      );
      setCreatedActions(prev => new Set([...prev, actionKey]));
    } catch { /* ignore */ }
  };

  const hasMore = periodsOffset < periodsTotal;

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

      {/* Filtres */}
      <div className="flex flex-wrap gap-2">
        <select
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700"
          value={siteFilter}
          onChange={e => { setSiteFilter(e.target.value); setPeriodsOffset(0); }}
        >
          <option value="">Tous les sites</option>
          {sites.map(s => (
            <option key={s.id} value={s.id}>{s.nom}</option>
          ))}
        </select>
        {siteFilter && (
          <Button size="sm" variant="ghost" onClick={() => setSiteFilter('')}>
            Réinitialiser
          </Button>
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
                value={summary.covered}
                color="text-green-600"
              />
              <KpiChip
                icon={AlertTriangle}
                label="Partiels"
                value={summary.partial}
                color="text-orange-500"
              />
              <KpiChip
                icon={XCircle}
                label="Manquants"
                value={summary.missing}
                color="text-red-500"
              />
            </div>
            <CoverageBar
              covered={summary.covered}
              partial={summary.partial}
              missing={summary.missing}
              total={summary.months_total}
              minMonth={summary.range?.min_month}
              maxMonth={summary.range?.max_month}
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
              {missingPeriods.slice(0, 5).map(item => (
                <div
                  key={`${item.site_id}-${item.month_key}`}
                  className="flex items-center justify-between gap-3 px-3 py-2 bg-red-50 border border-red-100 rounded-lg"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={item.coverage_status === 'missing' ? 'danger' : 'warning'} size="xs">
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
                      onClick={() => navigate(item.cta_url)}
                    >
                      <Upload size={11} /> Importer
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      disabled={createdActions.has(`missing-${item.month_key}-${item.site_id}`)}
                      onClick={() => {
                        const key = `missing-${item.month_key}-${item.site_id}`;
                        if (!createdActions.has(key)) {
                          createActionFromBillingInsight(
                            `missing-${item.month_key}-${item.site_id}`,
                            `Période manquante : ${item.month_key} — ${item.site_name}`,
                            item.site_id,
                          ).then(() => setCreatedActions(prev => new Set([...prev, key]))).catch(() => {});
                        }
                      }}
                    >
                      {createdActions.has(`missing-${item.month_key}-${item.site_id}`) ? '✓' : <Zap size={11} />}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Timeline complète */}
      <Card>
        <CardBody>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Timeline complète
            {periodsTotal > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                {periods.length}/{periodsTotal} mois
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
                periods={periods}
                siteId={siteFilter}
                onCreateAction={handleCreateAction}
                createdActions={createdActions}
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
    </div>
  );
}
