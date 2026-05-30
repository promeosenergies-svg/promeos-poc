/**
 * PROMEOS — MarketExposureTab (Sprint P1.S6).
 *
 * Onglet « Marché & exposition » sous `/consommations/marche`. Branché
 * sur `/api/energy/market-exposure` (livré P1.S2d).
 *
 * Affiche :
 * - hook produit FR (« Repérez les heures chères, les prix négatifs et
 *   l'écart vs un ruban baseload. ») ;
 * - 8 KPI canoniques via KpiCardWithProvenance :
 *     spot_cost_theoretical_eur, spot_avg_simple_eur_mwh,
 *     spot_avg_weighted_eur_mwh, baseload_cost_eur,
 *     delta_vs_baseload_eur, top_10pct_expensive_hours_cost_pct,
 *     negative_price_consumption_pct, exposure_score
 * - ExposureScoreGauge (score [0,100] borné backend) ;
 * - BaseloadComparisonCard (delta_eur, delta_eur_mwh, formule) ;
 * - TopExpensiveHoursTable (rang + action conseillée backend) ;
 * - FavorableHoursPanel (prix bas / prix négatif / heure solaire) ;
 * - DisplacementSimulationCard avec warning obligatoire si fournie.
 *
 * UX scope-site-required :
 * - si pas de site sélectionné → SiteRequiredState (pas d'appel API).
 *
 * Doctrine : zéro calcul métier frontend.
 */
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, AlertTriangle, LineChart } from 'lucide-react';
import { useScope } from '../../contexts/ScopeContext';
import { getMarketExposure } from '../../services/api/energy';
import KpiCardWithProvenance from '../../ui/energy/KpiCardWithProvenance';
import ExposureScoreGauge from '../../ui/energy/ExposureScoreGauge';
import TopExpensiveHoursTable from '../../ui/energy/TopExpensiveHoursTable';
import FavorableHoursPanel from '../../ui/energy/FavorableHoursPanel';
import BaseloadComparisonCard from '../../ui/energy/BaseloadComparisonCard';
import DisplacementSimulationCard from '../../ui/energy/DisplacementSimulationCard';
import SiteRequiredState from '../../ui/energy/SiteRequiredState';
import EnergyCrossLinks from '../../ui/energy/EnergyCrossLinks';
import { EmptyState, SkeletonCard } from '../../ui';

const CROSS_LINKS = [
  { kind: 'achat', to: '/achat-energie', label: 'Simuler une offre alternative' },
  { kind: 'action', to: '/action-center-v4', label: 'Créer une action' },
];

const KPI_ORDER = [
  'spot_cost_theoretical_eur',
  'spot_avg_simple_eur_mwh',
  'spot_avg_weighted_eur_mwh',
  'baseload_cost_eur',
  'delta_vs_baseload_eur',
  'top_10pct_expensive_hours_cost_pct',
  'negative_price_consumption_pct',
  'exposure_score',
];

const DEFAULT_PERIOD = '12m';
const DEFAULT_MARKET = 'day_ahead';
const DEFAULT_ZONE = 'FR';

function ApiErrorState({ error, onRetry }) {
  const detail = error?.response?.data?.detail || {};
  const code = detail.code || 'ENERGY_UNKNOWN';
  const message = detail.message || error?.message || 'Erreur inconnue';
  const hint = detail.hint;
  const correlationId = detail.correlation_id;
  return (
    <div
      className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-2"
      role="alert"
      data-testid="market-exposure-error"
    >
      <div className="flex items-start gap-2">
        <AlertCircle size={16} className="text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1 space-y-1">
          <p className="text-sm font-semibold text-red-800" data-testid="error-message">
            {message}
          </p>
          {hint && (
            <p className="text-xs text-red-700" data-testid="error-hint">
              {hint}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 text-[10px] text-red-500 mt-1">
            <span data-testid="error-code">code: {code}</span>
            {correlationId && (
              <span data-testid="error-correlation-id">correlation_id: {correlationId}</span>
            )}
          </div>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-xs font-medium text-red-700 hover:underline"
        >
          Réessayer
        </button>
      )}
    </div>
  );
}

function PartialDataBanner({ warnings }) {
  if (!Array.isArray(warnings) || warnings.length === 0) return null;
  return (
    <div
      className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-start gap-2"
      role="status"
      data-testid="market-exposure-partial"
    >
      <AlertTriangle size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-0.5">
        <p className="font-semibold">
          Analyse partielle — certaines heures n'ont pas de prix marché ou de mesure alignée.
        </p>
        {warnings.slice(0, 3).map((w, i) => (
          <p key={i} className="text-amber-700">
            {w}
          </p>
        ))}
      </div>
    </div>
  );
}

function TabHeader({ market }) {
  return (
    <div className="px-1 pt-2 pb-3 border-b border-gray-100" data-testid="market-exposure-header">
      <div className="flex items-center gap-2 text-gray-800">
        <LineChart size={16} className="text-blue-600" aria-hidden="true" />
        <h2 className="text-sm font-semibold">Marché & exposition</h2>
      </div>
      <p className="text-xs text-gray-500 mt-1">Votre profil face aux prix spot</p>
      <p className="text-xs text-gray-400 mt-0.5">
        Repérez les heures chères, les prix négatifs et l'écart vs un ruban baseload.
      </p>
      {market?.source && (
        <p className="text-[10px] text-gray-400 mt-1 font-mono" data-testid="market-context">
          Marché : {market.type} · Zone : {market.zone} · Source : {market.source}
        </p>
      )}
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="space-y-4 mt-4" data-testid="market-exposure-loading">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <SkeletonCard />
      <SkeletonCard />
    </div>
  );
}

export default function MarketExposureTab({
  period = DEFAULT_PERIOD,
  market = DEFAULT_MARKET,
  zone = DEFAULT_ZONE,
}) {
  const { selectedSiteId, scope, setSite } = useScope();
  const orgId = scope?.orgId;
  const siteId = selectedSiteId;
  const hasSite = siteId != null;

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [requestedPeriod, setRequestedPeriod] = useState(period);

  useEffect(() => {
    if (!hasSite) {
      setPayload(null);
      setError(null);
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = {
      scope: 'site',
      scope_id: siteId,
      period: requestedPeriod,
      market,
      zone,
      baseload: true,
    };
    if (orgId != null) params.org_id = orgId;
    getMarketExposure(params)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasSite, siteId, orgId, requestedPeriod, market, zone, reloadToken]);

  const kpis = payload?.kpis || {};
  const orderedKpis = useMemo(
    () => KPI_ORDER.filter((key) => kpis[key]).map((key) => ({ key, kpi: kpis[key] })),
    [kpis]
  );

  if (!hasSite) {
    return (
      <div data-testid="market-exposure-tab">
        <TabHeader />
        <div className="mt-4">
          <SiteRequiredState
            onChooseSite={typeof setSite === 'function' ? () => setSite(null) : undefined}
          />
        </div>
      </div>
    );
  }

  if (loading && !payload) {
    return (
      <div data-testid="market-exposure-tab">
        <TabHeader />
        <LoadingBlock />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="market-exposure-tab">
        <TabHeader />
        <div className="mt-4">
          <ApiErrorState error={error} onRetry={() => setReloadToken((t) => t + 1)} />
        </div>
      </div>
    );
  }

  const exposureKpi = kpis.exposure_score;
  const hasAnyKpi = orderedKpis.length > 0;
  const hasTopHours = (payload?.top_expensive_hours?.length || 0) > 0;
  const hasFavorable = (payload?.favorable_hours?.length || 0) > 0;
  const hasBaseload = Boolean(payload?.baseload_comparison);
  const hasContent = hasAnyKpi || hasTopHours || hasFavorable || hasBaseload;

  if (!hasContent) {
    return (
      <div data-testid="market-exposure-tab">
        <TabHeader market={payload?.market} />
        <div className="mt-4">
          <EmptyState
            variant="empty"
            icon={LineChart}
            title="Aucune exposition marché disponible pour ce site sur la période."
            text={
              payload?.empty_state ||
              "Élargissez la période ou vérifiez l'alignement courbe de charge ↔ prix spot."
            }
            ctaLabel="Élargir la période"
            onCta={() => setRequestedPeriod((p) => (p === '12m' ? '90d' : '12m'))}
          />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="market-exposure-tab">
      <TabHeader market={payload?.market} />
      <div className="mt-4 space-y-4">
        <PartialDataBanner warnings={payload?.warnings} />

        {/* Score d'exposition mis en avant + baseload comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <ExposureScoreGauge
            score={exposureKpi?.value}
            state={exposureKpi?.state}
            provenance={exposureKpi?.provenance}
            label={exposureKpi?.label || "Score d'exposition spot"}
          />
          {hasBaseload && (
            <div className="lg:col-span-2">
              <BaseloadComparisonCard baseloadComparison={payload.baseload_comparison} />
            </div>
          )}
        </div>

        {hasAnyKpi && (
          <div
            className="grid grid-cols-2 lg:grid-cols-4 gap-3"
            data-testid="market-exposure-kpis-grid"
          >
            {orderedKpis.map(({ key, kpi }) => (
              <KpiCardWithProvenance
                key={key}
                label={kpi.label}
                value={kpi.value}
                unit={kpi.unit}
                state={kpi.state}
                provenance={kpi.provenance}
                testId={`market-exposure-kpi-${key}`}
              />
            ))}
          </div>
        )}

        {hasTopHours && <TopExpensiveHoursTable topExpensiveHours={payload.top_expensive_hours} />}

        {hasFavorable && <FavorableHoursPanel favorableHours={payload.favorable_hours} />}

        {payload?.simulation && <DisplacementSimulationCard simulation={payload.simulation} />}

        <EnergyCrossLinks links={CROSS_LINKS} />
      </div>
    </div>
  );
}

export { KPI_ORDER, DEFAULT_PERIOD, DEFAULT_MARKET, DEFAULT_ZONE };
