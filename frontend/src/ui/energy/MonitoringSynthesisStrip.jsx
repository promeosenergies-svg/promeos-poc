/**
 * PROMEOS — MonitoringSynthesisStrip (Sprint P1.S3b).
 *
 * Composant Synthèse Énergie 30 secondes branché sur
 * `/api/energy/synthesis`. Affiche :
 * - narrative (briefing 2-3 phrases)
 * - 10 KPI canoniques via KpiCardWithProvenance
 * - recommendations si fournies par le backend
 *
 * Doctrine :
 * - Aucun calcul métier frontend.
 * - Tous les KPI proviennent du payload `synthesis.kpis`.
 * - estimated_impact_eur agrégé backend (retire la dette historique
 *   reduce post-filtre scope FE).
 * - Score data_quality_score borné [0, 100] côté backend (clamp_score).
 *
 * Props :
 * - scope         : { kind, id, org_id } — auto-fourni par la page hôte
 * - period        : '7d' | '30d' | '90d' | '12m' | 'ytd' (défaut '30d')
 * - compare       : 'none' | 'n-1' | 'baseline' | 'contract' (défaut 'none')
 * - testId        : préfixe data-testid (défaut 'monitoring-synthesis')
 */
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Sparkles } from 'lucide-react';
import { getEnergySynthesis } from '../../services/api/energy';
import KpiCardWithProvenance from './KpiCardWithProvenance';
import { EmptyState, SkeletonCard } from '../index';

// Ordre canonique d'affichage des KPI (cf. contrat /api/energy/synthesis).
const KPI_ORDER = [
  'consumption_kwh',
  'cost_eur',
  'co2_kg',
  'peak_kw',
  'weighted_price_eur_mwh',
  'data_quality_score',
  'sites_coverage_pct',
  'alerts_open',
  'actions_open',
  'estimated_impact_eur',
];

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
      data-testid="synthesis-error"
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

function NarrativeBanner({ narrative }) {
  if (!narrative) return null;
  return (
    <div
      className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 flex items-start gap-3"
      data-testid="synthesis-narrative"
    >
      <div className="w-8 h-8 rounded-full bg-white border border-blue-100 flex items-center justify-center text-blue-600 shrink-0">
        <Sparkles size={14} aria-hidden="true" />
      </div>
      <p className="text-sm text-blue-900 leading-relaxed">{narrative}</p>
    </div>
  );
}

function WarningsBanner({ warnings }) {
  if (!Array.isArray(warnings) || warnings.length === 0) return null;
  return (
    <div
      className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 space-y-0.5"
      role="status"
      data-testid="synthesis-warnings"
    >
      {warnings.map((w, i) => (
        <p key={i}>{w}</p>
      ))}
    </div>
  );
}

function LoadingStrip() {
  return (
    <div className="space-y-3" data-testid="synthesis-loading">
      <SkeletonCard />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}

export default function MonitoringSynthesisStrip({
  scope,
  period = '30d',
  compare = 'none',
  className = '',
  testId = 'monitoring-synthesis',
}) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  const scopeKind = scope?.kind || 'org';
  const scopeId = scope?.id ?? null;
  const orgId = scope?.org_id ?? null;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = {
      scope: scopeKind,
      period,
      compare,
    };
    if (scopeId != null) params.scope_id = scopeId;
    if (orgId != null) params.org_id = orgId;
    getEnergySynthesis(params)
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
  }, [scopeKind, scopeId, orgId, period, compare, reloadToken]);

  const kpis = payload?.kpis || {};

  // Tri ordre canonique : on conserve uniquement les clés fournies par
  // le backend, dans l'ordre KPI_ORDER. Pas de calcul ni filtre métier.
  const orderedKpis = useMemo(() => {
    return KPI_ORDER.filter((key) => kpis[key]).map((key) => ({ key, kpi: kpis[key] }));
  }, [kpis]);

  if (loading && !payload) {
    return (
      <div className={`space-y-3 ${className}`} data-testid={testId}>
        <LoadingStrip />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`space-y-3 ${className}`} data-testid={testId}>
        <ApiErrorState error={error} onRetry={() => setReloadToken((t) => t + 1)} />
      </div>
    );
  }

  if (!payload || orderedKpis.length === 0) {
    return (
      <div className={`space-y-3 ${className}`} data-testid={testId}>
        <EmptyState
          title="Aucune synthèse énergétique disponible sur la période sélectionnée."
          text="Vérifier la connexion compteur ou élargir la période."
        />
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`} data-testid={testId}>
      <NarrativeBanner narrative={payload.narrative} />
      <WarningsBanner warnings={payload.warnings} />
      <div
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3"
        data-testid="synthesis-kpis-grid"
      >
        {orderedKpis.map(({ key, kpi }) => (
          <KpiCardWithProvenance
            key={key}
            label={kpi.label}
            value={kpi.value}
            unit={kpi.unit}
            state={kpi.state}
            provenance={kpi.provenance}
            testId={`synthesis-kpi-${key}`}
          />
        ))}
      </div>
    </div>
  );
}

export { KPI_ORDER };
