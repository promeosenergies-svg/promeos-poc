/**
 * PROMEOS — LoadCurveTab (Sprint Énergie P1.S3a).
 *
 * Onglet "Courbe de charge" sous /consommations/courbe.
 * Branché sur GET /api/energy/loadcurve (helper getEnergyLoadCurve).
 *
 * Doctrine :
 * - Aucun calcul métier frontend. Tout vient de l'API :
 *   - kpis (total_kwh, peak_kw, baseload_kw, average_kw) avec provenance
 *   - series points avec quality_status
 *   - warnings, empty_state, provenance racine
 * - États UX : loading (SkeletonCard) / empty / error (avec hint +
 *   correlation_id si fourni) / partial (warnings backend).
 * - Filtres dans URL search params (period, granularity, compare, display).
 */
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useScope } from '../../contexts/ScopeContext';
import { getEnergyLoadCurve } from '../../services/api/energy';
import EnergyFilterBar from '../../ui/energy/EnergyFilterBar';
import KpiCardWithProvenance from '../../ui/energy/KpiCardWithProvenance';
import LoadCurveChart from '../../ui/energy/LoadCurveChart';
import TopPeaksTable from '../../ui/energy/TopPeaksTable';
// Sprint Énergie P3.1 — section Profil moyen par jour
import WeekdayOverlayChart from '../../ui/energy/WeekdayOverlayChart';
import WeekdayDecompositionBar from '../../ui/energy/WeekdayDecompositionBar';
// Sprint P2.5 audit final — helper canonique label site (jamais technique).
import { formatSiteLabel } from '../../ui/energy/scopeLabel';
// Sprint Énergie P2.2 (2026-05-30) — cross-link Centre d'action V4.
// Wording générique car TopPeaksTable est indisponible côté API
// pour cette version (cf. brief P1.S3a).
import EnergyCrossLinks from '../../ui/energy/EnergyCrossLinks';
import { ErrorState } from '../../ui';

const LOAD_CURVE_CROSS_LINKS = [
  { kind: 'action', to: '/action-center-v4', label: "Créer une action d'analyse" },
];

const DEFAULT_PERIOD = '30d';
const DEFAULT_GRANULARITY = 'hour';
const DEFAULT_COMPARE = 'none';
const DEFAULT_DISPLAY = 'kwh';

const PERIOD_TO_DAYS = { '7d': 7, '30d': 30, '90d': 90 };

/** Convertit period label → (from, to) ISO sans calcul métier. */
function periodToRange(periodLabel) {
  const days = PERIOD_TO_DAYS[periodLabel] || 30;
  const now = new Date();
  const from = new Date(now.getTime() - days * 86400000);
  return { from: from.toISOString(), to: now.toISOString() };
}

function readFilters(searchParams) {
  return {
    period: searchParams.get('period') || DEFAULT_PERIOD,
    granularity: searchParams.get('granularity') || DEFAULT_GRANULARITY,
    compare: searchParams.get('compare') || DEFAULT_COMPARE,
    display: searchParams.get('display') || DEFAULT_DISPLAY,
  };
}

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
      data-testid="loadcurve-error"
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

export default function LoadCurveTab() {
  const { selectedSiteId, sitesById } = useScope();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  const scope = useMemo(() => {
    const site = selectedSiteId && sitesById ? sitesById[selectedSiteId] : null;
    // Sprint P2.5 audit final — `formatSiteLabel` retourne le nom métier
    // du site ou un fallback FR métier, jamais un identifiant technique.
    return {
      kind: 'site',
      id: selectedSiteId,
      label: formatSiteLabel(site ? { ...site, id: selectedSiteId } : { id: selectedSiteId }),
    };
  }, [selectedSiteId, sitesById]);

  useEffect(() => {
    if (!selectedSiteId) {
      setPayload(null);
      setError(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const { from, to } = periodToRange(filters.period);
    const params = {
      scope: 'site',
      scope_id: selectedSiteId,
      from,
      to,
      granularity: filters.granularity,
      compare: filters.compare,
    };
    getEnergyLoadCurve(params)
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
  }, [selectedSiteId, filters.period, filters.granularity, filters.compare, reloadToken]);

  const handleFilterChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next.period && next.period !== filters.period) params.set('period', next.period);
    if (next.granularity && next.granularity !== filters.granularity)
      params.set('granularity', next.granularity);
    if (next.compare && next.compare !== filters.compare) params.set('compare', next.compare);
    if (next.display && next.display !== filters.display) params.set('display', next.display);
    setSearchParams(params, { replace: true });
  };

  const kpis = payload?.kpis || {};

  return (
    <div className="space-y-4" data-testid="loadcurve-tab">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Courbe de charge</h2>
        <p className="text-sm text-gray-500 italic">
          Votre consommation électrique heure par heure — agréger · désagréger · comparer.
        </p>
      </div>

      <EnergyFilterBar
        scope={scope}
        period={filters.period}
        granularity={filters.granularity}
        compare={filters.compare}
        display={filters.display}
        onChange={handleFilterChange}
      />

      {!selectedSiteId ? (
        <ErrorState
          title="Aucun site sélectionné"
          text="Sélectionnez un site dans le sélecteur de scope pour afficher la courbe de charge."
        />
      ) : error ? (
        <ApiErrorState error={error} onRetry={() => setReloadToken((t) => t + 1)} />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCardWithProvenance
              label={kpis.total_kwh?.label || 'Consommation période'}
              value={kpis.total_kwh?.value}
              unit={kpis.total_kwh?.unit || 'kWh'}
              state={kpis.total_kwh?.state}
              provenance={kpis.total_kwh?.provenance}
              testId="kpi-total-kwh"
            />
            <KpiCardWithProvenance
              label={kpis.peak_kw?.label || 'Puissance max'}
              value={kpis.peak_kw?.value}
              unit={kpis.peak_kw?.unit || 'kW'}
              state={kpis.peak_kw?.state}
              provenance={kpis.peak_kw?.provenance}
              testId="kpi-peak-kw"
            />
            <KpiCardWithProvenance
              label={kpis.average_kw?.label || 'Puissance moyenne'}
              value={kpis.average_kw?.value}
              unit={kpis.average_kw?.unit || 'kW'}
              state={kpis.average_kw?.state}
              provenance={kpis.average_kw?.provenance}
              testId="kpi-average-kw"
            />
            <KpiCardWithProvenance
              label={kpis.baseload_kw?.label || 'Talon'}
              value={kpis.baseload_kw?.value}
              unit={kpis.baseload_kw?.unit || 'kW'}
              state={kpis.baseload_kw?.state}
              provenance={kpis.baseload_kw?.provenance}
              testId="kpi-baseload-kw"
            />
          </div>

          <LoadCurveChart
            series={payload?.series || []}
            seriesCompare={payload?.series_compare || []}
            granularity={filters.granularity}
            display={filters.display}
            compare={filters.compare}
            loading={loading}
            emptyState={payload?.empty_state}
            warnings={payload?.warnings || []}
          />

          <TopPeaksTable
            points={payload?.top_peaks || []}
            granularity={filters.granularity}
            loading={loading}
          />

          {/* Sprint Énergie P3.1 — section Profil moyen par jour
              (7 courbes lundi → dimanche + décomposition + comparaison
              jours ouvrés/week-end). */}
          {Array.isArray(payload?.weekday_overlay) && payload.weekday_overlay.length > 0 && (
            <WeekdayOverlayChart curves={payload.weekday_overlay} display={filters.display} />
          )}
          {Array.isArray(payload?.weekday_decomposition) &&
            payload.weekday_decomposition.length > 0 && (
              <WeekdayDecompositionBar
                decomposition={payload.weekday_decomposition}
                comparison={payload.weekday_weekend_comparison}
              />
            )}

          {/* Sprint Énergie P2.2 (2026-05-30) — cross-link Action V4. */}
          <EnergyCrossLinks links={LOAD_CURVE_CROSS_LINKS} testId="loadcurve-cross-links" />
        </>
      )}
    </div>
  );
}
