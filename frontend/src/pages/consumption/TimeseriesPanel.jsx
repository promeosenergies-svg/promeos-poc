/**
 * PROMEOS — TimeseriesPanel (Sprint V14.3 / V15)
 * Premium timeseries chart — dates on X-axis, consumption over time.
 * This is the DEFAULT view in Classic mode and the first Expert tab.
 *
 * Uses useEmsTimeseries() → /api/ems/timeseries
 * Handles all states: loading / empty / insufficient / error / ready
 *
 * Props:
 *   siteIds        {number[]}
 *   energyType     {string}    'electricity' | 'gas'
 *   days           {number|string}
 *   startDate      {string|null}
 *   endDate        {string|null}
 *   unit           {string}    'kwh' | 'kw' | 'eur'
 *   mode           {string}    'agrege' | 'superpose' | 'empile' | 'separe'
 *   sites          {object[]}  [{id, nom}]
 *   siteColors     {object}    { siteId: color }
 *   availability   {object}    from useExplorerMotor
 *   onNavigate     {fn}        navigate to path
 *   onRetry        {fn}        optional — retry on error (defaults to reload)
 *   onExtendPeriod {fn}        optional — extend period to 12 months
 */
import { useEffect } from 'react';
import { Database, BarChart3, AlertTriangle, RefreshCw, Zap } from 'lucide-react';
import { Button, SkeletonCard, TrustBadge } from '../../ui';
import ExplorerChart from './ExplorerChart';
import ExplorerDebugPanel from './ExplorerDebugPanel';
import useEmsTimeseries from './useEmsTimeseries';
import { colorForSite } from './helpers';
import { useScope } from '../../contexts/ScopeContext';

const _UNIT_LABELS = { kwh: 'kWh', kw: 'kW', eur: '€' };

const GRAN_LABELS = {
  daily: 'Journalière',
  monthly: 'Mensuelle',
  hourly: 'Horaire',
  '15min': '15 min',
  '30min': '30 min',
};

// ── DataCoverageBadge ──────────────────────────────────────────────────────────

/** Format ISO date string (YYYY-MM-DD) to DD/MM/YYYY */
function formatDateFR(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split('T')[0].split('-');
  return `${d}/${m}/${y}`;
}

function DataCoverageBadge({ meta, siteCount, qualityPct, startDate, endDate }) {
  const dateRange =
    startDate || endDate
      ? `${formatDateFR(startDate) || '…'} → ${formatDateFR(endDate) || '…'}`
      : null;

  const parts = [
    dateRange,
    siteCount > 1 ? `${siteCount} sites` : null,
    meta?.n_meters ? `${meta.n_meters}\u00a0compteur${meta.n_meters > 1 ? 's' : ''}` : null,
    meta?.n_points ? `${meta.n_points.toLocaleString('fr-FR')}\u00a0mesures` : null,
    meta?.granularity
      ? `Granularité\u00a0: ${GRAN_LABELS[meta.granularity] || meta.granularity}`
      : null,
    qualityPct != null ? `Qualité\u00a0: ${qualityPct}\u00a0%` : null,
    'Source\u00a0: Compteurs',
  ].filter(Boolean);

  if (!parts.length) return null;

  return (
    <div
      className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-400 px-1 select-none"
      aria-label="Couverture des données"
    >
      {parts.map((p, i) => (
        <span key={i}>{p}</span>
      ))}
    </div>
  );
}

// ── Insufficient data placeholder ─────────────────────────────────────────────

function InsufficientPoints({ count, onGenerateDemo }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mb-4">
        <BarChart3 size={28} className="text-amber-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 mb-1">
        Données insuffisantes pour tracer une courbe
      </h3>
      <p className="text-sm text-gray-500 max-w-sm">
        {count} point{count !== 1 ? 's' : ''} disponible{count !== 1 ? 's' : ''}. Élargissez la
        période ou importez davantage de données.
      </p>
      {onGenerateDemo && (
        <Button size="sm" variant="outline" onClick={onGenerateDemo} className="mt-3">
          <Zap size={12} className="mr-1.5" />
          Générer conso démo
        </Button>
      )}
    </div>
  );
}

// ── Error state ────────────────────────────────────────────────────────────────

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <AlertTriangle size={28} className="text-red-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 mb-1">Erreur de chargement</h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm">{message}</p>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          <RefreshCw size={14} className="mr-1.5" />
          Réessayer
        </Button>
      )}
    </div>
  );
}

// ── Empty state by reason (enhanced V16-B) ────────────────────────────────────

function EmptyByReason({
  availability,
  noSiteSelected,
  onNavigate,
  onExtendPeriod,
  onSelectAll,
  onGenerateDemo,
}) {
  const reasons = availability?.reasons || [];
  const primary = reasons[0];
  const firstTs = availability?.first_ts;
  const lastTs = availability?.last_ts;

  // V16-B / V17-C: no site selected = first-priority reason
  if (noSiteSelected) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-4">
          <BarChart3 size={28} className="text-blue-400" />
        </div>
        <h3 className="text-base font-semibold text-gray-700 mb-1">Aucun site sélectionné</h3>
        <p className="text-sm text-gray-500 max-w-xs mb-3">
          Sélectionnez un ou plusieurs sites dans la barre de filtres pour afficher les courbes de
          consommation.
        </p>
        {onSelectAll && (
          <Button size="sm" onClick={onSelectAll}>
            Tout sélectionner
          </Button>
        )}
      </div>
    );
  }

  // Build smart causes list from availability data
  const causes = [];
  if (primary === 'no_site') {
    causes.push({ icon: AlertTriangle, text: 'Site introuvable — vérifiez votre sélection.' });
  }
  if (primary === 'no_meter') {
    causes.push({
      icon: Zap,
      text: 'Aucun compteur configuré sur ce site.',
      cta: 'Connecter',
      path: '/connectors',
    });
  }
  if (primary === 'no_readings' || primary === 'insufficient_readings') {
    causes.push({
      icon: Database,
      text: 'Peu de relevés importés sur cette période.',
      cta: 'Importer',
      path: '/consommations/import',
    });
  }
  if (primary === 'wrong_energy_type') {
    causes.push({ icon: Zap, text: "Aucune donnée pour ce type d'énergie sur ce site." });
  }
  if (firstTs && lastTs) {
    const from = new Date(firstTs).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
    const to = new Date(lastTs).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
    causes.push({
      icon: BarChart3,
      text: `Données disponibles\u00a0: ${from} → ${to}`,
      cta: onExtendPeriod ? 'Étendre à 12 mois' : null,
      onCta: onExtendPeriod,
    });
  }
  if (!causes.length) {
    causes.push({
      icon: Database,
      text: 'Configurez un site et importez des relevés.',
      cta: 'Importer',
      path: '/consommations/import',
    });
  }

  const FirstIcon = causes[0]?.icon || Database;

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <FirstIcon size={28} className="text-gray-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 mb-2">
        Aucune donnée sur cette période
      </h3>

      {causes.length > 0 && (
        <div className="space-y-2 mb-4">
          {causes.map((c, i) => (
            <div key={i} className="flex items-center justify-center gap-2">
              <p className="text-sm text-gray-500 max-w-sm">{c.text}</p>
              {c.cta && c.onCta && (
                <Button size="sm" variant="ghost" onClick={c.onCta}>
                  {c.cta}
                </Button>
              )}
              {c.cta && c.path && onNavigate && (
                <Button size="sm" variant="ghost" onClick={() => onNavigate(c.path)}>
                  {c.cta}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
      {/* V20-D: Demo generation CTA when no real data */}
      {onGenerateDemo && (
        <Button size="sm" variant="outline" onClick={onGenerateDemo}>
          <Zap size={12} className="mr-1.5" />
          Générer conso démo
        </Button>
      )}
    </div>
  );
}

// ── ChartFrame: guaranteed height wrapper for ALL states ──────────────────────

function ChartFrame({ children, minHeight = 360 }) {
  return (
    <div className="w-full rounded-xl border border-gray-100 bg-white" style={{ minHeight }}>
      {children}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function TimeseriesPanel({
  siteIds = [],
  energyType = 'electricity',
  days = 30,
  startDate = null,
  endDate = null,
  unit = 'kwh',
  mode = 'agrege',
  sites: _sites = [],
  siteColors = {},
  availability = null,
  granularityOverride = null, // V21-C: user-selected granularity or null for auto
  onNavigate,
  onRetry,
  onExtendPeriod,
  onSelectAll,
  onGenerateDemo, // V20-D: optional — triggers demo data generation + refetch
  onMeta, // V22-B: optional — called with meta object when data arrives
  compareYoy = false, // Step 10 — F1: YoY comparison
}) {
  const tsState = useEmsTimeseries({
    siteIds,
    energyType,
    days,
    startDate,
    endDate,
    unit,
    mode,
    granularityOverride,
    compareYoy,
  });

  const { status, chartData, seriesData, meta, granularity, error, debugInfo } = tsState;

  // V22-B: report meta (sampling_minutes, available_granularities) upward for pill filtering
  useEffect(() => {
    if (meta && onMeta) onMeta(meta);
  }, [meta, onMeta]);

  // Scope for debug overlay (V16-A)
  const { scope: globalScope, selectedSiteId, scopeLabel, sitesCount } = useScope();

  // Effective retry handler
  const handleRetry = onRetry || (() => window.location.reload());

  // Build siteColors map for multi-series overlay
  const effectiveSiteColors = { ...siteColors };
  siteIds.forEach((sid, idx) => {
    if (!effectiveSiteColors[sid]) {
      effectiveSiteColors[sid] = colorForSite(sid, idx);
    }
  });

  // V20-B (RC1 fix): overlayValueKeys only for genuine multi-series; 'total'/'agg'/'others' are
  // aggregate series — their value is always in chartData[i].value, not chartData[i][key].
  const overlayValueKeys =
    seriesData.length <= 1
      ? []
      : seriesData
          .filter(
            (s) =>
              s.key &&
              s.key !== 'agg' &&
              s.key !== 'total' &&
              s.key !== 'others' &&
              !s.key.endsWith('_prev')
          )
          .map((s) => s.key);

  // V20-B (RC3 fix): effectiveValueKey must match what ExplorerChart will use
  const effectiveValueKey = overlayValueKeys.length ? overlayValueKeys[0] : 'value';

  // Issue #33: site name labels for SepareGrid sub-graph titles
  // Clean technical suffixes like "— 43707 (elec_gaz, electricity)" from labels
  const cleanLabel = (lbl) => lbl?.replace(/\s*[—–-]\s*\d+\s*\(.*?\)\s*$/, '').trim() || lbl;
  const siteLabels = Object.fromEntries(
    seriesData
      .filter((s) => s.key?.startsWith('site_'))
      .map((s) => [parseInt(s.key.replace('site_', ''), 10), cleanLabel(s.label)])
  );

  // Debug panel — shown in ALL states when ?debug=1 (after overlayValueKeys so chartMeta is available)
  const isDebug =
    typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('debug');
  const debugPanel = isDebug ? (
    <ExplorerDebugPanel
      params={{ siteIds, energyType, days, unit, mode, startDate, endDate }}
      tsState={{ status, meta, granularity, error, debugInfo }}
      availability={availability}
      scope={{ orgId: globalScope?.orgId, selectedSiteId, scopeLabel, sitesCount }}
      chartMeta={{ overlayValueKeys, effectiveValueKey }}
    />
  ) : null;

  // ── Loading ──
  if (status === 'loading') {
    return (
      <ChartFrame>
        {debugPanel}
        <div className="p-4">
          <SkeletonCard rows={6} />
        </div>
      </ChartFrame>
    );
  }

  // ── Error ──
  if (status === 'error') {
    return (
      <ChartFrame>
        {debugPanel}
        <ErrorState message={error} onRetry={handleRetry} />
      </ChartFrame>
    );
  }

  // ── Empty (no data from API or no site selected) ──
  if (status === 'empty') {
    return (
      <ChartFrame>
        {debugPanel}
        <EmptyByReason
          availability={availability}
          noSiteSelected={!siteIds.length}
          onNavigate={onNavigate}
          onExtendPeriod={onExtendPeriod}
          onSelectAll={onSelectAll}
          onGenerateDemo={onGenerateDemo}
        />
      </ChartFrame>
    );
  }

  // ── Insufficient points (< 2) ──
  // V20-B (RC3 fix): use effectiveValueKey to match ExplorerChart's perspective
  const validPoints = chartData.filter(
    (p) => p[effectiveValueKey] != null && !isNaN(p[effectiveValueKey])
  );
  if (validPoints.length < 2) {
    return (
      <ChartFrame>
        {debugPanel}
        <InsufficientPoints count={validPoints.length} onGenerateDemo={onGenerateDemo} />
      </ChartFrame>
    );
  }

  // ── Ready: render chart ──
  const _n_points = meta?.n_points ?? chartData.length;
  const _n_meters = meta?.n_meters ?? null;
  const qualityPct = availability?.readings_count
    ? Math.min(100, Math.round((availability.readings_count / 500) * 100))
    : null;

  // For multi-series, pass empile/separe/superpose through; single-site always agrege
  const MULTI_SITE_MODES = ['superpose', 'empile', 'separe'];
  const chartMode = seriesData.length > 1 && MULTI_SITE_MODES.includes(mode) ? mode : 'agrege';
  const overlayKeySet = new Set(overlayValueKeys);
  const chartSiteIds = overlayValueKeys.length
    ? siteIds.filter((sid) => overlayKeySet.has(`site_${sid}`))
    : siteIds.slice(0, 1);
  // When a single site is displayed in agrege mode, show its name instead of "Agrégé"
  const aggregateLabel =
    siteIds.length === 1
      ? (_sites.find((s) => s.id === siteIds[0])?.nom ??
        cleanLabel(siteLabels[siteIds[0]]) ??
        'Agrégé')
      : 'Agrégé';

  // Confidence level for TrustBadge — same logic previously in StickyFilterBar
  const confidence =
    availability?.has_data && availability.readings_count > 0
      ? availability.readings_count > 1000
        ? 'high'
        : availability.readings_count > 200
          ? 'medium'
          : 'low'
      : null;

  return (
    <ChartFrame>
      <div className="space-y-2 p-3">
        {debugPanel}

        {/* DataCoverageBadge + TrustBadge — same row, badge pushed right */}
        <div className="flex items-center gap-2">
          <DataCoverageBadge
            meta={meta}
            siteCount={siteIds.length}
            qualityPct={qualityPct}
            startDate={
              startDate || new Date(Date.now() - days * 86400000).toISOString().split('T')[0]
            }
            endDate={endDate || new Date().toISOString().split('T')[0]}
          />
          {confidence && <TrustBadge confidence={confidence} className="ml-auto shrink-0" />}
        </div>

        {/* Chart */}
        <div>
          <ExplorerChart
            data={chartData}
            xKey="date"
            valueKey={overlayValueKeys.length ? overlayValueKeys[0] : 'value'}
            mode={chartMode}
            unit={unit}
            siteIds={chartSiteIds}
            siteColors={effectiveSiteColors}
            siteLabels={siteLabels}
            aggregateLabel={aggregateLabel}
            height={360}
            showBrush
          />
        </div>
      </div>
    </ChartFrame>
  );
}
