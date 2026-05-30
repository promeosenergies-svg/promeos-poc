/**
 * PROMEOS — WeekProfileTab (Sprint P1.S4).
 *
 * Onglet « Semaine type » dans `/usages?tab=semaine-type`. Branché sur
 * `/api/energy/week-profile` (livré P1.S2b).
 *
 * Affiche :
 * - hook produit FR (« Repérez les pics, le talon de nuit et les usages
 *   hors horaires. ») ;
 * - 4 KPI canoniques via KpiCardWithProvenance :
 *     highest_day, highest_hour, night_baseload_kw, weekend_consumption_pct
 * - heatmap 7 jours × 24 heures via WeekProfileHeatmap ;
 * - bandeau « Données partielles » si warnings backend ;
 * - empty / error states documentés.
 *
 * Doctrine : zéro calcul métier frontend. Tout (KPI agrégés, statut
 * cellule, qualité) vient de `/api/energy/week-profile`.
 */
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, AlertTriangle, CalendarDays } from 'lucide-react';
import { useScope } from '../../contexts/ScopeContext';
import { getWeekProfile } from '../../services/api/energy';
import KpiCardWithProvenance from '../../ui/energy/KpiCardWithProvenance';
import WeekProfileHeatmap from '../../ui/energy/WeekProfileHeatmap';
import SiteRequiredState from '../../ui/energy/SiteRequiredState';
import { EmptyState, SkeletonCard } from '../../ui';

const KPI_ORDER = ['highest_day', 'highest_hour', 'night_baseload_kw', 'weekend_consumption_pct'];

const DEFAULT_DAYS = 90;

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
      data-testid="week-profile-error"
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
      data-testid="week-profile-partial"
    >
      <AlertTriangle size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-0.5">
        <p className="font-semibold">
          Données partielles — certaines heures sont estimées ou manquantes.
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
    <div className="px-5 pt-5 pb-3 border-b border-gray-100" data-testid="week-profile-header">
      <div className="flex items-center gap-2 text-gray-800">
        <CalendarDays size={16} className="text-blue-600" aria-hidden="true" />
        <h2 className="text-sm font-semibold">Semaine type</h2>
      </div>
      <p className="text-xs text-gray-500 mt-1">Votre comportement du lundi au dimanche</p>
      <p className="text-xs text-gray-400 mt-0.5">
        Repérez les pics, le talon de nuit et les usages hors horaires.
      </p>
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="p-5 space-y-4" data-testid="week-profile-loading">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <SkeletonCard />
    </div>
  );
}

export default function WeekProfileTab({ days = DEFAULT_DAYS, daysOverride }) {
  const { selectedSiteId, scope, setSite } = useScope();
  const orgId = scope?.orgId;
  const siteId = selectedSiteId;
  const effectiveDays = daysOverride ?? days;
  // Sprint P1.S6 — la vue Semaine type n'est servie qu'au niveau site/meter.
  // Si pas de site sélectionné, on n'appelle pas l'API (évite remontée
  // ENERGY_SCOPE_INVALID en rouge) et on affiche un SiteRequiredState métier.
  const hasSite = siteId != null;

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [requestedDays, setRequestedDays] = useState(effectiveDays);

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
      days: requestedDays,
    };
    if (orgId != null) params.org_id = orgId;
    getWeekProfile(params)
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
  }, [hasSite, siteId, orgId, requestedDays, reloadToken]);

  const kpis = payload?.kpis || {};
  const orderedKpis = useMemo(
    () => KPI_ORDER.filter((key) => kpis[key]).map((key) => ({ key, kpi: kpis[key] })),
    [kpis]
  );

  if (!hasSite) {
    return (
      <div data-testid="week-profile-tab">
        <TabHeader />
        <div className="p-5">
          <SiteRequiredState
            onChooseSite={typeof setSite === 'function' ? () => setSite(null) : undefined}
          />
        </div>
      </div>
    );
  }

  if (loading && !payload) {
    return (
      <div data-testid="week-profile-tab">
        <TabHeader />
        <LoadingBlock />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="week-profile-tab">
        <TabHeader />
        <div className="p-5">
          <ApiErrorState error={error} onRetry={() => setReloadToken((t) => t + 1)} />
        </div>
      </div>
    );
  }

  const matrix = payload?.matrix || [];
  const hasMatrixData = matrix.some((c) => c && c.kwh != null);
  const hasAnyKpi = orderedKpis.length > 0;

  if (!hasMatrixData && !hasAnyKpi) {
    return (
      <div data-testid="week-profile-tab">
        <TabHeader />
        <div className="p-5">
          <EmptyState
            variant="empty"
            icon={CalendarDays}
            title="Données insuffisantes pour afficher une semaine type."
            text={
              payload?.empty_state || 'Élargissez la période ou vérifiez la connexion compteur.'
            }
            ctaLabel="Élargir la période"
            onCta={() => setRequestedDays((d) => Math.min(365, d + 90))}
          />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="week-profile-tab">
      <TabHeader />
      <div className="p-5 space-y-4">
        <PartialDataBanner warnings={payload?.warnings} />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="week-profile-kpis-grid">
          {orderedKpis.map(({ key, kpi }) => (
            <KpiCardWithProvenance
              key={key}
              label={kpi.label}
              value={kpi.value}
              unit={kpi.unit}
              state={kpi.state}
              provenance={kpi.provenance}
              testId={`week-profile-kpi-${key}`}
            />
          ))}
        </div>

        <WeekProfileHeatmap
          matrix={matrix}
          provenance={payload?.provenance}
          ariaLabel="Semaine type — heatmap consommation lundi à dimanche × 0h à 23h"
        />
      </div>
    </div>
  );
}

export { KPI_ORDER, DEFAULT_DAYS };
