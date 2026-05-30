/**
 * PROMEOS — CostContractTab (Sprint P1.S5).
 *
 * Onglet « Coût & contrat » sous `/consommations/cout-contrat`. Branché
 * sur `/api/energy/cost-vs-contract` (livré P1.S2c).
 *
 * Affiche :
 * - hook produit FR (« Comparez le coût estimé, les composantes
 *   tarifaires et les scénarios contractuels. ») ;
 * - 6 KPI canoniques via KpiCardWithProvenance :
 *     total_cost_eur, consumption_kwh, weighted_price_eur_mwh,
 *     supply_cost_eur, network_cost_eur, taxes_cost_eur
 * - contrat actif (résumé) ;
 * - 4 scénarios via CostVsContractCard ;
 * - décomposition prix via PriceDecompositionTable ;
 * - warning « Simulation indicative — ne constitue pas une promesse
 *   d'économie. » (obligatoire).
 *
 * Doctrine : zéro calcul métier frontend. Tout (KPI, deltas, share_pct,
 * scénario gagnant, risk_level) vient de `/api/energy/cost-vs-contract`.
 */
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, AlertTriangle, ReceiptText } from 'lucide-react';
import { useScope } from '../../contexts/ScopeContext';
import { getCostVsContract } from '../../services/api/energy';
import KpiCardWithProvenance from '../../ui/energy/KpiCardWithProvenance';
import CostVsContractCard from '../../ui/energy/CostVsContractCard';
import PriceDecompositionTable from '../../ui/energy/PriceDecompositionTable';
import SiteRequiredState from '../../ui/energy/SiteRequiredState';
import { EmptyState, SkeletonCard } from '../../ui';

const KPI_ORDER = [
  'total_cost_eur',
  'consumption_kwh',
  'weighted_price_eur_mwh',
  'supply_cost_eur',
  'network_cost_eur',
  'taxes_cost_eur',
];

const DEFAULT_PERIOD = '12m';
const DEFAULT_SCENARIOS = 'fixed,indexed,mixed,ths';

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
      data-testid="cost-contract-error"
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
      data-testid="cost-contract-partial"
    >
      <AlertTriangle size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-0.5">
        <p className="font-semibold">
          Simulation partielle — certaines composantes tarifaires reposent sur des hypothèses.
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

function TabHeader() {
  return (
    <div className="px-1 pt-2 pb-3 border-b border-gray-100" data-testid="cost-contract-header">
      <div className="flex items-center gap-2 text-gray-800">
        <ReceiptText size={16} className="text-blue-600" aria-hidden="true" />
        <h2 className="text-sm font-semibold">Coût & contrat</h2>
      </div>
      <p className="text-xs text-gray-500 mt-1">Votre coût réel selon le contrat actif</p>
      <p className="text-xs text-gray-400 mt-0.5">
        Comparez le coût estimé, les composantes tarifaires et les scénarios contractuels.
      </p>
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="space-y-4 mt-4" data-testid="cost-contract-loading">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <SkeletonCard />
    </div>
  );
}

export default function CostContractTab({
  period = DEFAULT_PERIOD,
  scenarios = DEFAULT_SCENARIOS,
}) {
  const { selectedSiteId, scope, setSite } = useScope();
  const orgId = scope?.orgId;
  const siteId = selectedSiteId;
  // Sprint P1.S6 — la vue Coût & contrat n'est servie qu'au niveau
  // site/meter (un contrat est rattaché à un site). Si pas de site
  // sélectionné, on n'appelle pas l'API et on affiche SiteRequiredState.
  const hasSite = siteId != null;

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

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
      period,
      scenarios,
    };
    if (orgId != null) params.org_id = orgId;
    getCostVsContract(params)
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
  }, [hasSite, siteId, orgId, period, scenarios, reloadToken]);

  const kpis = payload?.kpis || {};
  const orderedKpis = useMemo(
    () => KPI_ORDER.filter((key) => kpis[key]).map((key) => ({ key, kpi: kpis[key] })),
    [kpis]
  );

  if (!hasSite) {
    return (
      <div data-testid="cost-contract-tab">
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
      <div data-testid="cost-contract-tab">
        <TabHeader />
        <LoadingBlock />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="cost-contract-tab">
        <TabHeader />
        <div className="mt-4">
          <ApiErrorState error={error} onRetry={() => setReloadToken((t) => t + 1)} />
        </div>
      </div>
    );
  }

  const scenarioList = payload?.scenarios || [];
  const priceDecomp = payload?.price_decomposition || [];
  const hasAnyKpi = orderedKpis.length > 0;
  const hasScenarios = scenarioList.length > 0;
  const hasContract = Boolean(payload?.active_contract?.contract_id);

  if (!hasAnyKpi && !hasScenarios && !hasContract) {
    return (
      <div data-testid="cost-contract-tab">
        <TabHeader />
        <div className="mt-4">
          <EmptyState
            variant="empty"
            icon={ReceiptText}
            title="Aucun contrat actif disponible pour ce site."
            text={
              payload?.empty_state ||
              'Importez un contrat ou sélectionnez un autre site pour démarrer la simulation.'
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="cost-contract-tab">
      <TabHeader />
      <div className="mt-4 space-y-4">
        <PartialDataBanner warnings={payload?.warnings} />

        {hasAnyKpi && (
          <div
            className="grid grid-cols-2 lg:grid-cols-3 gap-3"
            data-testid="cost-contract-kpis-grid"
          >
            {orderedKpis.map(({ key, kpi }) => (
              <KpiCardWithProvenance
                key={key}
                label={kpi.label}
                value={kpi.value}
                unit={kpi.unit}
                state={kpi.state}
                provenance={kpi.provenance}
                testId={`cost-contract-kpi-${key}`}
              />
            ))}
          </div>
        )}

        {hasScenarios && (
          <CostVsContractCard
            scenarios={scenarioList}
            recommendation={payload?.recommendation}
            activeContract={payload?.active_contract}
          />
        )}

        {Array.isArray(priceDecomp) && priceDecomp.length > 0 && (
          <PriceDecompositionTable priceDecomposition={priceDecomp} />
        )}
      </div>
    </div>
  );
}

export { KPI_ORDER, DEFAULT_PERIOD, DEFAULT_SCENARIOS };
