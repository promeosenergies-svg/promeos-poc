/**
 * PROMEOS — TimeseriesPanel (Sprint V14.3)
 * Premium timeseries chart — dates on X-axis, consumption over time.
 * This is the DEFAULT view in Classic mode and the first Expert tab.
 *
 * Uses useEmsTimeseries() → /api/ems/timeseries
 * Handles all states: loading / empty / insufficient / error / ready
 *
 * Props:
 *   siteIds      {number[]}
 *   energyType   {string}    'electricity' | 'gas'
 *   days         {number|string}
 *   startDate    {string|null}
 *   endDate      {string|null}
 *   unit         {string}    'kwh' | 'kw' | 'eur'
 *   mode         {string}    'agrege' | 'superpose' | 'empile' | 'separe'
 *   sites        {object[]}  [{id, nom}]
 *   siteColors   {object}    { siteId: color }
 *   availability {object}    from useExplorerMotor
 */
import { Database, BarChart3, AlertTriangle, RefreshCw, Zap } from 'lucide-react';
import { Button, SkeletonCard } from '../../ui';
import ExplorerChart from './ExplorerChart';
import useEmsTimeseries from './useEmsTimeseries';
import { colorForSite } from './helpers';

const UNIT_LABELS = { kwh: 'kWh', kw: 'kW', eur: 'EUR' };

// ── Insufficient data placeholder ─────────────────────────────────────────────

function InsufficientPoints({ count }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mb-4">
        <BarChart3 size={28} className="text-amber-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 mb-1">
        Données insuffisantes pour tracer une courbe
      </h3>
      <p className="text-sm text-gray-500 max-w-sm">
        {count} point{count !== 1 ? 's' : ''} disponible{count !== 1 ? 's' : ''}.
        Élargissez la période ou importez davantage de données.
      </p>
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

// ── Empty state by reason ──────────────────────────────────────────────────────

function EmptyByReason({ availability, onNavigate }) {
  const reasons = availability?.reasons || [];
  const primary = reasons[0];

  const CONFIGS = {
    no_site: { icon: AlertTriangle, title: 'Site introuvable', text: 'Vérifiez votre sélection.' },
    no_meter: { icon: Zap, title: 'Aucun compteur configuré', text: 'Connectez un compteur pour voir les consommations.', cta: 'Connecter', path: '/connectors' },
    no_readings: { icon: Database, title: 'Aucun relevé disponible', text: 'Importez des données de consommation.', cta: 'Importer', path: '/consommations/import' },
    insufficient_readings: { icon: BarChart3, title: 'Données insuffisantes', text: 'Moins de 48 relevés. Importez davantage.', cta: 'Importer', path: '/consommations/import' },
    wrong_energy_type: { icon: Zap, title: 'Énergie non disponible', text: 'Basculez vers un autre type d\'énergie.' },
  };

  const cfg = CONFIGS[primary] || { icon: Database, title: 'Aucune donnée', text: 'Configurez un site et importez des relevés.' };
  const Icon = cfg.icon;

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={28} className="text-gray-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700 mb-1">{cfg.title}</h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm">{cfg.text}</p>
      {cfg.cta && onNavigate && (
        <Button size="sm" onClick={() => onNavigate(cfg.path)}>{cfg.cta}</Button>
      )}
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
  sites = [],
  siteColors = {},
  availability = null,
  onNavigate,
}) {
  const { status, chartData, seriesData, meta, granularity, error } = useEmsTimeseries({
    siteIds,
    energyType,
    days,
    startDate,
    endDate,
    unit,
    mode,
  });

  // Build siteColors map for multi-series overlay
  const effectiveSiteColors = { ...siteColors };
  siteIds.forEach((sid, idx) => {
    if (!effectiveSiteColors[sid]) {
      effectiveSiteColors[sid] = colorForSite(sid, idx);
    }
  });

  // Compute per-site value keys for overlay mode (key = "site_<id>")
  const overlayValueKeys = seriesData
    .filter(s => s.key && s.key !== 'agg')
    .map(s => s.key);

  // ── Loading ──
  if (status === 'loading') {
    return <SkeletonCard rows={6} />;
  }

  // ── Error ──
  if (status === 'error') {
    return <ErrorState message={error} />;
  }

  // ── Empty (no data from API) ──
  if (status === 'empty') {
    return <EmptyByReason availability={availability} onNavigate={onNavigate} />;
  }

  // ── Insufficient points (< 2) ──
  const validPoints = chartData.filter(p => p.value != null && !isNaN(p.value));
  if (validPoints.length < 2) {
    return <InsufficientPoints count={validPoints.length} />;
  }

  // ── Ready: render chart ──
  const unitLabel = UNIT_LABELS[unit] || 'kWh';
  const n_points = meta?.n_points ?? chartData.length;
  const n_meters = meta?.n_meters ?? null;
  const qualityPct = availability?.readings_count
    ? Math.min(100, Math.round(availability.readings_count / 500 * 100))
    : null;

  // For multi-series overlay, ExplorerChart uses `superpose` mode with site keys
  const chartMode = seriesData.length > 1 && mode === 'superpose' ? 'superpose' : 'agrege';
  const chartSiteIds = overlayValueKeys.length
    ? overlayValueKeys.map(k => parseInt(k.replace('site_', ''), 10))
    : siteIds.slice(0, 1);

  return (
    <div className="space-y-2">
      {/* Chart */}
      <ExplorerChart
        data={chartData}
        xKey="date"
        valueKey={overlayValueKeys.length ? overlayValueKeys[0] : 'value'}
        mode={chartMode}
        unit={unit}
        siteIds={chartSiteIds}
        siteColors={effectiveSiteColors}
        height={360}
        showBrush
        summaryData={{
          points: n_points,
          series: seriesData.length,
          meters: n_meters,
          source: 'EMS',
          quality: qualityPct,
        }}
      />

      {/* Granularity info */}
      {granularity && (
        <p className="text-xs text-gray-400 text-right">
          Granularité\u00a0: {granularity === 'daily' ? 'Journalière' : granularity === 'monthly' ? 'Mensuelle' : granularity === 'hourly' ? 'Horaire' : granularity}
          {meta?.date_from && meta?.date_to && (
            <span className="ml-2">
              · {new Date(meta.date_from).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })}
              {' '}→{' '}
              {new Date(meta.date_to).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })}
            </span>
          )}
        </p>
      )}
    </div>
  );
}
