/**
 * PROMEOS - MonitoringPage V3 (/monitoring)
 * Performance Électrique — premium dashboard.
 * 5 KPI cards, 4 graphs (signature, heatmap, climate scatter, bar chart),
 * InsightDrawer, CreateActionModal, demo profile selector.
 * V79: + Tarif Heures Solaires KPI card, cross-brique CTA vers Achats.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Zap,
  BarChart3,
  CheckCircle,
  Clock,
  Shield,
  TrendingUp,
  ChevronDown,
  Eye,
  PlayCircle,
  Database,
  RefreshCw,
  Thermometer,
  Sun,
  Info,
  UserCheck,
  CheckCircle2,
  ExternalLink,
  Leaf,
  Loader2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
  ComposedChart,
  Area,
  ScatterChart,
  Scatter,
  Legend,
} from 'recharts';
import {
  Card,
  CardBody,
  Badge,
  Button,
  EmptyState,
  TrustBadge,
  Skeleton,
  PageShell,
  KpiCard,
  Drawer,
  Tabs,
  Tooltip,
  Explain,
  GLOSSARY,
} from '../ui';
import { SkeletonCard } from '../ui';
import ErrorState from '../ui/ErrorState';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { track } from '../services/tracker';
import { getKpiMessage } from '../services/kpiMessaging';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { fmtDateFR } from '../utils/format';
import {
  toConsoExplorer,
  toConsoDiag,
  toActionsList,
  toPatrimoine,
  toPurchase,
} from '../services/routes';
import {
  getMonitoringKpis,
  runMonitoring,
  getMonitoringSnapshots,
  getMonitoringAlerts,
  ackMonitoringAlert,
  resolveMonitoringAlert,
  generateMonitoringDemo,
  getUsageSuggest,
  getEmsBenchmark,
  getActionsList,
  getScheduleSuggest,
  putSiteSchedule,
  getMonitoringKpisCompare,
  getDataQualityScore,
  getSiteFreshness,
} from '../services/api';
import DataQualityBadge from '../components/DataQualityBadge';
import FreshnessIndicator from '../components/FreshnessIndicator';

// --- Constants ---

const SEVERITY_BADGE = {
  critical: 'crit',
  high: 'warn',
  warning: 'warn',
  info: 'info',
};

const SEVERITY_LABEL_FR = {
  critical: 'Critique',
  high: 'Élevée',
  warning: 'Moyenne',
  info: 'Info',
};

const STATUS_CONFIG = {
  open: { label: 'Ouvert', badge: 'crit' },
  ack: { label: 'En cours', badge: 'warn' },
  resolved: { label: 'Résolu', badge: 'ok' },
};

const ALERT_TYPE_LABELS = {
  BASE_NUIT_ELEVEE: 'Base nuit élevée',
  WEEKEND_ANORMAL: 'Week-end anormal',
  DERIVE_TALON: 'Dérive talon',
  PIC_ANORMAL: 'Pic anormal',
  P95_HAUSSE: 'Hausse P95',
  DEPASSEMENT_PUISSANCE: 'Dépassement puissance',
  RUPTURE_PROFIL: 'Rupture de profil',
  HORS_HORAIRES: 'Consommation hors horaires',
  COURBE_PLATE: 'Courbe plate',
  DONNEES_MANQUANTES: 'Données manquantes',
  DOUBLONS_DST: 'Doublons DST',
  VALEURS_NEGATIVES: 'Valeurs négatives',
  SENSIBILITE_CLIMATIQUE: 'Sensibilité climatique',
  // snake_case variants from monitoring engine
  off_hours_consumption: 'Consommation hors horaires',
  high_night_base: 'Base nuit élevée',
  power_risk: 'Risque puissance souscrite',
  weekend_anomaly: 'Anomalie week-end',
  high_base_load: 'Talon élevé',
  peak_anomaly: 'Pic anormal',
  profile_break: 'Rupture de profil',
  flat_curve: 'Courbe plate',
  missing_data: 'Données manquantes',
  climate_sensitivity: 'Sensibilité climatique',
};

const KPI_THRESHOLDS = {
  quality: { ok: 80, warn: 60 },
  risk: { ok: 35, warn: 60 },
  loadFactor: { ok: 85, warn: 50 },
  climate: { ok: 2, warn: 4 },
};

const KPI_TOOLTIPS = {
  pmax: 'Puissance max atteinte (P = E / dt). P95 = 95e centile.',
  loadFactor: 'E_totale / (Pmax x heures). Élevé = courbe plate.',
  risk: 'Risque dépassement Psub. 4 facteurs: P95/Psub, fréquence, volatilité, pics.',
  quality: 'Qualité données: complétude, trous, doublons, négatifs, outliers.',
  climate: 'Pente (kWh/j)/°C de la signature énergétique. Élevé = forte dépendance climatique.',
};

const DAYS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const HOURS_24 = Array.from({ length: 24 }, (_, i) => `${i}h`);

const DRAWER_TABS = [
  { id: 'evidence', label: 'Preuve' },
  { id: 'methode', label: 'Méthode' },
  { id: 'actions', label: 'Actions' },
];

const PROFILE_OPTIONS = [
  { value: 'office', label: 'Bureau' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'retail', label: 'Commerce' },
  { value: 'warehouse', label: 'Logistique' },
  { value: 'school', label: 'École' },
  { value: 'hospital', label: 'Hôpital' },
];

// --- Exported helpers (testable) ---

export function buildHeatmapGrid(weekdayProfile, weekendProfile) {
  if (!weekdayProfile) return null;
  return Array.from({ length: 7 }, (_, d) =>
    Array.from({ length: 24 }, (_, h) =>
      Number(((d >= 5 ? weekendProfile || weekdayProfile : weekdayProfile)[h] || 0).toFixed(1))
    )
  );
}

export function kpiStatus(value, thresholds, invert = false) {
  if (value == null) return 'no_data';
  if (invert) {
    if (value <= thresholds.ok) return 'ok';
    if (value <= thresholds.warn) return 'surveiller';
    return 'critique';
  }
  if (value >= thresholds.ok) return 'ok';
  if (value >= thresholds.warn) return 'surveiller';
  return 'critique';
}

/**
 * Compute confidence level for a KPI.
 * @param {object} opts - { r2, nPoints, coveragePct, reason }
 * @returns {{ level: 'low'|'medium'|'high', pct: number, reason: string }}
 */
export function computeConfidence({ r2, nPoints, coveragePct, reason } = {}) {
  if (reason) return { level: 'low', pct: 0, reason };

  let score = 50; // baseline
  if (r2 != null) score = r2 * 100; // R² dominates for climate
  if (nPoints != null) {
    if (nPoints < 10) score = Math.min(score, 15);
    else if (nPoints < 30) score = Math.min(score, 40);
  }
  if (coveragePct != null) score = Math.min(score, coveragePct);

  score = Math.max(0, Math.min(100, Math.round(score)));
  const level = score >= 60 ? 'high' : score >= 30 ? 'medium' : 'low';
  const reasons = [];
  if (r2 != null && r2 < 0.3) reasons.push(`R² faible (${fmtNum(r2, 2)})`);
  if (nPoints != null && nPoints < 30) reasons.push(`${nPoints} jours de données`);
  if (coveragePct != null && coveragePct < 60) reasons.push(`Couverture ${coveragePct}%`);
  return { level, pct: score, reason: reasons.join(' · ') || 'Données suffisantes' };
}

/**
 * Load factor thresholds by archetype.
 * lower ok = LF below ok is OK (LF is "high=ok" for some, "high=warn" for others).
 * Seuils: if LF >= ok → ok, >= warn → surveiller, else critique.
 */
export const LF_THRESHOLDS_BY_ARCHETYPE = {
  office: { ok: 40, warn: 25 },
  hotel: { ok: 55, warn: 35 },
  retail: { ok: 45, warn: 30 },
  warehouse: { ok: 50, warn: 35 },
  school: { ok: 35, warn: 20 },
  hospital: { ok: 60, warn: 40 },
  default: { ok: 35, warn: 20 },
};

/**
 * Estimate off-hours cost in EUR/year.
 * Extrapolates from a 90-day measurement period to annual.
 * @param {number|null} kwh - off-hours kWh over the measurement period
 * @param {number} price - EUR/kWh (default 0.18)
 * @returns {{ eur: number, label: string, price: number }}
 */
export function computeOffHoursEstimate(kwh, price = 0.18) {
  if (kwh == null || kwh <= 0) return { eur: 0, label: '-', price };
  const annualized = kwh * (365 / 90);
  const eur = Math.round(annualized * price);
  return { eur, label: `~${fmtNum(eur, 0)} EUR/an`, price };
}

/**
 * Compute KPI delta for comparison.
 * @param {number} current
 * @param {number} previous
 * @param {boolean} lowerIsBetter - true for risk/off-hours metrics (lower = improvement)
 * @returns {{ pct: number, direction: 'up'|'down'|'flat', isGood: boolean }}
 */
export function computeKpiDelta(current, previous, lowerIsBetter = false) {
  if (current == null || previous == null || previous === 0) return null;
  const pct = ((current - previous) / Math.abs(previous)) * 100;
  const direction = pct > 1 ? 'up' : pct < -1 ? 'down' : 'flat';
  const isGood = lowerIsBetter ? direction === 'down' : direction === 'up';
  return { pct: Math.round(pct), direction, isGood };
}

function KpiDelta({ current, previous, lowerIsBetter = false }) {
  const delta = computeKpiDelta(current, previous, lowerIsBetter);
  if (!delta || delta.direction === 'flat') return null;
  const arrow = delta.direction === 'up' ? '↑' : '↓';
  const color = delta.isGood ? 'text-emerald-600' : 'text-red-600';
  return (
    <span className={`text-[10px] font-semibold ${color}`}>
      {arrow} {Math.abs(delta.pct)}%
    </span>
  );
}

const MODE_COLORS = {
  CONTRAT: 'bg-green-100 text-green-700',
  TARIF: 'bg-blue-100 text-blue-700',
  DEMO: 'bg-amber-100 text-amber-700',
};

function ModeBadge({ mode }) {
  if (!mode) return null;
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${MODE_COLORS[mode] || MODE_COLORS.DEMO}`}
    >
      {mode}
    </span>
  );
}

const ACTION_STATUS_BADGE = { open: 'warn', in_progress: 'info', done: 'success', blocked: 'crit' };

function ActionMiniList({ actions, siteId, navigate }) {
  if (!actions || actions.length === 0) return null;
  return (
    <Card>
      <CardBody>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Actions du site</h3>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => navigate(toActionsList({ site_id: siteId }))}
          >
            Voir tout
          </Button>
        </div>
        <div className="space-y-1.5">
          {actions.map((a) => (
            <div key={a.id} className="flex items-center gap-2 text-xs">
              <Badge variant={ACTION_STATUS_BADGE[a.status] || 'info'} size="sm">
                {a.status}
              </Badge>
              <span className="truncate flex-1 text-gray-700">{a.title}</span>
              {a.estimated_gain_eur > 0 && (
                <span className="text-emerald-600 font-medium">
                  {fmtNum(a.estimated_gain_eur, 0)} EUR
                </span>
              )}
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

/**
 * Enhanced kpiStatus that accounts for confidence.
 * If confidence is low, caps status at 'a_confirmer' (both critique & surveiller).
 * Rule: low confidence => no alarm — only "A confirmer".
 */
export function kpiStatusWithConfidence(value, thresholds, invert, confidence) {
  const raw = kpiStatus(value, thresholds, invert);
  if (confidence && confidence.level === 'low' && (raw === 'critique' || raw === 'surveiller')) {
    return 'a_confirmer';
  }
  return raw;
}

/**
 * Aggregate duplicate insights by alert_type + site_id (site-level).
 * Merges across meters: tracks _meters set, _count, impact sums, worst severity.
 * Returns grouped rows sorted by total impact desc.
 */
export function groupInsights(alerts) {
  const map = new Map();
  for (const a of alerts) {
    const key = `${a.alert_type}:${a.site_id || 0}`;
    if (!map.has(key)) {
      map.set(key, {
        ...a,
        _count: 1,
        _totalEur: a.estimated_impact_eur || 0,
        _totalKwh: a.estimated_impact_kwh || 0,
        _maxSeverity: a.severity,
        _ids: [a.id],
        _meters: new Set([a.meter_id]),
      });
    } else {
      const g = map.get(key);
      g._count += 1;
      g._totalEur += a.estimated_impact_eur || 0;
      g._totalKwh += a.estimated_impact_kwh || 0;
      g._ids.push(a.id);
      if (a.meter_id) g._meters.add(a.meter_id);
      // Keep worst severity
      const order = { critical: 3, high: 2, warning: 1, info: 0 };
      if ((order[a.severity] || 0) > (order[g._maxSeverity] || 0)) {
        g._maxSeverity = a.severity;
      }
      // Keep longest explanation
      if ((a.explanation || '').length > (g.explanation || '').length) {
        g.explanation = a.explanation;
      }
    }
  }
  return [...map.values()].sort((a, b) => b._totalEur - a._totalEur);
}

// --- Helpers ---

function scoreColor(score) {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  if (score >= 40) return 'text-orange-600';
  return 'text-red-600';
}

function riskColor(score) {
  if (score >= 80) return 'text-red-600';
  if (score >= 60) return 'text-orange-600';
  if (score >= 35) return 'text-yellow-600';
  return 'text-green-600';
}

function fmtNum(v, digits = 1) {
  if (v == null) return '-';
  if (typeof v !== 'number') return String(v);
  // French format: space for thousands, comma for decimal
  const parts = v.toFixed(digits).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0');
  return parts.join(',');
}

// --- Sub-components ---

const STATUS_BADGES = {
  ok: { label: 'OK', badge: 'ok' },
  surveiller: { label: 'Surveiller', badge: 'warn' },
  critique: { label: 'Critique', badge: 'crit' },
  a_confirmer: { label: 'À confirmer', badge: 'info' },
  no_data: { label: 'Pas de données', badge: 'neutral' },
};

const CONFIDENCE_DOT = {
  high: 'bg-green-500',
  medium: 'bg-yellow-500',
  low: 'bg-red-400',
};

function StatusKpiCard({ icon, title, value, sub, tooltip, status, color, onClick, confidence, message }) {
  const st = STATUS_BADGES[status] || STATUS_BADGES.ok;
  const confTip = confidence
    ? `Confiance: ${confidence.level === 'high' ? 'Forte' : confidence.level === 'medium' ? 'Moyenne' : 'Faible'}${confidence.reason ? ' — ' + confidence.reason : ''}`
    : null;
  const fullTip = [tooltip, confTip].filter(Boolean).join('\n');
  return (
    <Tooltip text={fullTip} position="bottom">
      <div>
        <KpiCard
          icon={icon}
          title={title}
          value={value}
          sub={sub}
          color={color}
          onClick={onClick}
          badge={st.label}
          badgeStatus={st.badge}
        />
        {confidence && (
          <div className="flex items-center gap-1 px-3 pb-2 -mt-1 text-[10px] text-gray-400">
            <span
              className={`w-1.5 h-1.5 rounded-full ${CONFIDENCE_DOT[confidence.level] || CONFIDENCE_DOT.low}`}
            />
            Confiance:{' '}
            {confidence.level === 'high'
              ? 'Forte'
              : confidence.level === 'medium'
                ? 'Moyenne'
                : 'Faible'}
          </div>
        )}
        {message}
      </div>
    </Tooltip>
  );
}

/**
 * Executive summary v2: top risk, top waste, data confidence — each with CTAs.
 * Confidence downgrade: if qualityConf.level === 'low', risk card shows "(A confirmer)".
 */
function ExecutiveSummary({
  alerts,
  kpiData,
  _climate,
  _qualityScore,
  qualityConf,
  offHoursKwh,
  emissions,
  onOpenExplorer,
  onCreateAction,
  onInsight,
  onConfidenceDetail,
  navigate,
  siteId,
  isExpert,
}) {
  // Top risk: highest EUR impact open alert
  const topAlert = alerts
    .filter((a) => a.status === 'open' && a.estimated_impact_eur)
    .sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0))[0];

  const isLowConf = qualityConf?.level === 'low';

  // Top waste: off-hours or high base load
  const WASTE_TYPES = [
    'HORS_HORAIRES',
    'BASE_NUIT_ELEVEE',
    'WEEKEND_ANORMAL',
    'off_hours_consumption',
    'high_night_base',
    'weekend_anomaly',
  ];
  const wasteAlerts = alerts.filter(
    (a) => WASTE_TYPES.includes(a.alert_type) && a.status !== 'resolved'
  );
  const totalWasteEur = wasteAlerts.reduce((s, a) => s + (a.estimated_impact_eur || 0), 0);
  const totalWasteKwh = wasteAlerts.reduce((s, a) => s + (a.estimated_impact_kwh || 0), 0);
  const offHoursEst = computeOffHoursEstimate(offHoursKwh);

  // Data confidence
  const confOk = qualityConf?.level === 'high' || qualityConf?.level === 'medium';

  // V79: Solar hours adoption
  const offHoursRatio = kpiData?.off_hours_ratio ?? null;

  const cards = [
    {
      icon: AlertTriangle,
      iconColor: topAlert ? (isLowConf ? 'text-gray-400' : 'text-red-500') : 'text-gray-300',
      title: 'Risque principal',
      value: topAlert
        ? `${fmtNum(topAlert.estimated_impact_eur, 0)} EUR/an${isLowConf ? ' (À confirmer)' : ''}`
        : 'Aucun risque détecté',
      sub: topAlert
        ? ALERT_TYPE_LABELS[topAlert.alert_type] || topAlert.alert_type
        : 'Continuez le suivi',
      ctas: topAlert
        ? [
            { label: 'Comprendre', action: () => onInsight(topAlert) },
            { label: 'Créer action', action: () => onCreateAction(topAlert) },
          ]
        : [],
      expertDetail: topAlert
        ? `id=#${topAlert.id} · type=${topAlert.alert_type} · sev=${topAlert.severity} · kwh=${topAlert.estimated_impact_kwh || '-'}`
        : null,
    },
    {
      icon: Zap,
      iconColor: totalWasteEur > 0 ? 'text-orange-500' : 'text-gray-300',
      title: <Explain term="gaspillage_estime">Gaspillage estimé</Explain>,
      value: totalWasteEur > 0 ? `${fmtNum(totalWasteEur, 0)} EUR/an` : 'Non détecté',
      sub:
        wasteAlerts.length > 0
          ? `${fmtNum(totalWasteKwh, 0)} kWh · ${wasteAlerts.length} alerte${wasteAlerts.length > 1 ? 's' : ''}${offHoursEst.eur > 0 ? ` · Hors horaires: ${offHoursEst.label}` : ''}`
          : 'Aucune anomalie de gaspillage',
      ctas:
        totalWasteEur > 0
          ? [
              { label: 'Explorer', action: onOpenExplorer },
              { label: 'Créer action', action: () => onCreateAction(wasteAlerts[0]) },
            ]
          : [],
      expertDetail: wasteAlerts.length > 0
        ? `alertes=${wasteAlerts.length} · types=${[...new Set(wasteAlerts.map(a => a.alert_type))].join(',')} · kwh_total=${fmtNum(totalWasteKwh, 0)}`
        : null,
    },
    {
      icon: Database,
      iconColor: confOk ? 'text-green-600' : 'text-red-500',
      title: 'Confiance données',
      value: confOk ? 'OK' : 'À confirmer',
      sub: qualityConf?.reason || 'Données suffisantes',
      ctas: [{ label: 'Comprendre', action: onConfidenceDetail }],
      expertDetail: `level=${qualityConf?.level || '-'} · pct=${qualityConf?.pct ?? '-'}% · reason=${qualityConf?.reason || 'N/A'}`,
    },
    {
      icon: Leaf,
      iconColor: emissions?.annualized_co2e_tonnes > 0 ? 'text-emerald-600' : 'text-gray-300',
      title: 'Empreinte CO₂e',
      value:
        emissions?.annualized_co2e_tonnes != null
          ? `${fmtNum(emissions.annualized_co2e_tonnes)} t/an`
          : 'Non disponible',
      sub:
        (emissions?.off_hours_co2e_kg || 0) > 0
          ? `dont ${fmtNum(emissions.off_hours_co2e_kg, 0)} kg évitables (hors horaires)`
          : emissions?.factor?.source_label || 'Facteur non configuré',
      ctas:
        (emissions?.off_hours_co2e_kg || 0) > 0
          ? [
              {
                label: 'Créer action',
                action: () =>
                  onCreateAction({ alert_type: 'CO2E_REDUCTION', estimated_impact_eur: 0 }),
              },
            ]
          : [],
      expertDetail: emissions?.factor
        ? `factor=${emissions.factor.kgco2e_per_kwh} kgCO₂e/kWh · src=${emissions.factor.source_label || '-'} · quality=${emissions.factor.quality || '-'}`
        : null,
    },
    {
      icon: Sun,
      iconColor: 'text-amber-500',
      title: 'Tarif Heures Solaires',
      value:
        offHoursRatio != null ? `${Math.round((1 - offHoursRatio) * 100)}% solaire` : 'Non évalué',
      sub:
        offHoursRatio != null
          ? `${Math.round(offHoursRatio * 100)}% hors créneaux · Gain estimé ${offHoursEst.eur > 0 ? offHoursEst.label : '—'}`
          : 'Lancez une analyse pour évaluer',
      testId: 'kpi-tarif-heures-solaires',
      ctas: [
        {
          label: 'Simuler',
          action: () => navigate(toPurchase({ tab: 'simulation', site_id: siteId })),
        },
        ...(offHoursEst.eur > 0
          ? [
              {
                label: 'Créer action',
                action: () =>
                  onCreateAction({
                    alert_type: 'TARIF_HEURES_SOLAIRES',
                    estimated_impact_eur: offHoursEst.eur,
                  }),
              },
            ]
          : []),
      ],
      expertDetail: offHoursRatio != null
        ? `ratio=${fmtNum(offHoursRatio * 100)}% · kwh_90j=${offHoursKwh ?? '-'} · est=${offHoursEst.eur} EUR/an · prix=${offHoursEst.price} EUR/kWh`
        : null,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
      {cards.map((c, i) => (
        <Card key={i} data-testid={c.testId}>
          <CardBody className="p-4">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-gray-50 ${c.iconColor}`}>
                <c.icon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                  {c.title}
                </p>
                <p className="text-lg font-bold text-gray-800 mt-0.5">{c.value}</p>
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{c.sub}</p>
                {c.ctas && c.ctas.length > 0 && (
                  <div className="flex items-center gap-3 mt-2">
                    {c.ctas.map((cta, j) => (
                      <button
                        key={j}
                        onClick={cta.action}
                        className="text-xs font-medium text-blue-600 hover:text-blue-800 transition flex items-center gap-1"
                      >
                        {cta.label} <ExternalLink size={10} />
                      </button>
                    ))}
                  </div>
                )}
                {isExpert && c.expertDetail && (
                  <div className="text-[10px] text-gray-400 font-mono mt-1">
                    {c.expertDetail}
                  </div>
                )}
              </div>
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

/**
 * Quick actions bar: Explorer, Create Action, Compare
 */
function QuickActionsBar({
  onOpenExplorer,
  onCreateAction,
  compareEnabled,
  compareMode,
  onCompareChange,
  compareLoading,
}) {
  return (
    <div className="flex items-center gap-2 mb-6 flex-wrap">
      <Button variant="secondary" size="sm" onClick={onOpenExplorer}>
        <BarChart3 size={14} />
        Ouvrir dans Explorer
      </Button>
      <Button variant="primary" size="sm" onClick={onCreateAction}>
        <Zap size={14} />
        Créer une action
      </Button>
      {compareEnabled && (
        <div className="flex items-center gap-1">
          <select
            className="text-xs border border-gray-300 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:ring-2 focus:ring-blue-500"
            value={compareMode || ''}
            onChange={(e) => onCompareChange(e.target.value || null)}
          >
            <option value="">Comparer...</option>
            <option value="previous">vs période précédente</option>
            <option value="n-1">vs N-1</option>
          </select>
          {compareLoading && <RefreshCw size={12} className="animate-spin text-blue-400" />}
          {compareMode && (
            <button
              onClick={() => onCompareChange(null)}
              className="text-xs text-gray-400 hover:text-gray-600 px-1"
            >
              ✕
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function WeekdayWeekendChart({ weekdayProfile, weekendProfile }) {
  const data = useMemo(() => {
    if (!weekdayProfile) return null;
    return Array.from({ length: 24 }, (_, h) => ({
      hour: `${h}h`,
      semaine: Number((weekdayProfile[h] || 0).toFixed(1)),
      weekend: Number(((weekendProfile || weekdayProfile)[h] || 0).toFixed(1)),
    }));
  }, [weekdayProfile, weekendProfile]);

  if (!data) {
    return (
      <div className="text-center py-12">
        <Clock size={28} className="mx-auto text-gray-200 mb-2" />
        <p className="text-sm text-gray-400">
          Lancez une analyse pour générer le profil jour-type.
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
        <YAxis tick={{ fontSize: 11 }} unit=" kW" />
        <RTooltip />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Area
          type="monotone"
          dataKey="semaine"
          stroke="#3b82f6"
          fill="#bfdbfe"
          fillOpacity={0.5}
          name="Semaine"
        />
        <Area
          type="monotone"
          dataKey="weekend"
          stroke="#f59e0b"
          fill="#fde68a"
          fillOpacity={0.4}
          name="Weekend"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function HeatmapGrid({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8">
        <Sun size={24} className="mx-auto text-gray-200 mb-2" />
        <p className="text-xs text-gray-400">Pas de données heatmap. Lancez une analyse.</p>
      </div>
    );
  }

  const allValues = data.flat().filter((v) => v > 0);
  const maxVal = Math.max(...allValues, 1);

  const getColor = (val) => {
    if (val === 0) return 'bg-gray-100';
    const intensity = val / maxVal;
    if (intensity > 0.8) return 'bg-red-500';
    if (intensity > 0.6) return 'bg-orange-400';
    if (intensity > 0.4) return 'bg-amber-400';
    if (intensity > 0.2) return 'bg-yellow-300';
    return 'bg-green-200';
  };

  return (
    <div className="overflow-x-auto">
      <div className="grid grid-cols-[auto_repeat(24,1fr)] gap-px text-[9px]">
        <div />
        {HOURS_24.map((h) => (
          <div key={h} className="text-center text-gray-400 py-0.5">
            {h}
          </div>
        ))}
        {data.map((row, d) => (
          <div key={d} className="contents">
            <div className="text-gray-500 pr-1 flex items-center">{DAYS_FR[d]}</div>
            {row.map((val, h) => (
              <div
                key={h}
                className={`aspect-square rounded-sm ${getColor(val)} transition-colors`}
                title={`${DAYS_FR[d]} ${h}h: ${val} kW`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1 mt-2 text-[9px] text-gray-400 justify-end">
        <span>Bas</span>
        {['bg-green-200', 'bg-yellow-300', 'bg-amber-400', 'bg-orange-400', 'bg-red-500'].map(
          (c) => (
            <div key={c} className={`w-3 h-3 rounded-sm ${c}`} />
          )
        )}
        <span>Haut</span>
      </div>
    </div>
  );
}

export const CLIMATE_REASONS = {
  no_meter: "Aucun compteur associé au snapshot. Relancez l'analyse.",
  no_weather: 'Données météo indisponibles pour la période.',
  meter_not_found: 'Compteur introuvable.',
  insufficient_readings: 'Moins de 10 jours de données — insuffisant pour la régression.',
  computation_error: 'Erreur de calcul. Vérifiez les données sources.',
};

export const CLIMATE_LABEL_FR = {
  heating_dominant: 'Chauffage majoritaire',
  cooling_dominant: 'Climatisation majoritaire',
  mixed: 'Mixte (chauffage + clim.)',
  flat: 'Insensible au climat',
  unknown: 'Non déterminé',
};

// --- Usage Panel helpers ---

export const USAGE_DAYS_FR = {
  0: 'Lun',
  1: 'Mar',
  2: 'Mer',
  3: 'Jeu',
  4: 'Ven',
  5: 'Sam',
  6: 'Dim',
};

export function formatSchedule(sched) {
  if (!sched) return '-';
  if (sched.is_24_7) return '24/7';
  const days = (sched.open_days || '')
    .split(',')
    .map((d) => USAGE_DAYS_FR[d.trim()])
    .filter(Boolean);
  const daysStr =
    days.length === 7
      ? 'Tous les jours'
      : days.length === 5 && !days.includes('Sam')
        ? 'Lun-Ven'
        : days.join(', ');
  return `${daysStr} ${sched.open_time}-${sched.close_time}`;
}

const CONFIDENCE_LABEL_FR = { high: 'Forte', medium: 'Moyenne', low: 'Faible' };
const SOURCE_LABEL_FR = { naf: 'NAF', type_fallback: 'Type site', default: 'Defaut' };

function UsagePanel({
  usage,
  loading: usageLoading,
  scheduleSuggest,
  onSuggestSchedule,
  onApplySchedule,
  suggestLoading,
}) {
  if (usageLoading)
    return (
      <div className="bg-white border rounded-xl p-4 mb-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
        <div className="h-3 bg-gray-100 rounded w-2/3" />
      </div>
    );
  if (!usage) return null;

  const current = usage.schedule_current;
  const suggested = usage.schedule_suggested;
  const schedText = current ? formatSchedule(current) : null;
  const suggestText = formatSchedule(suggested);

  // Data-driven suggestion from consumption
  const dataSuggested = scheduleSuggest?.schedule_suggested;
  const dataSuggestText = dataSuggested ? formatSchedule(dataSuggested) : null;

  return (
    <Card className="mb-4">
      <CardBody className="p-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={16} className="text-blue-500 shrink-0" />
              <span className="font-semibold text-sm text-gray-800">Usages & Horaires</span>
              <Badge status="info">{usage.archetype_label || usage.archetype_code}</Badge>
              {usage.archetype_source === 'naf' && (
                <span className="text-[10px] text-gray-400">
                  NAF: {usage.reasons?.[0]?.split('→')[0]?.replace('NAF ', '').trim()}
                </span>
              )}
            </div>
            <div className="text-sm text-gray-600">
              {current ? (
                <span>{schedText} · Source: horaires site</span>
              ) : (
                <span className="text-yellow-600">Horaires suggérés: {suggestText}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
              <span>Confiance: {CONFIDENCE_LABEL_FR[usage.confidence] || usage.confidence}</span>
              <span>
                Source: {SOURCE_LABEL_FR[usage.archetype_source] || usage.archetype_source}
              </span>
              {usage.has_vacation && <span className="text-blue-500">Vacances actives</span>}
            </div>
            {/* Data-driven suggestion result */}
            {dataSuggested && (
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 text-xs">
                  <Database size={12} className="text-blue-500" />
                  <span className="font-medium text-blue-700">Suggestion depuis conso:</span>
                  <span className="text-blue-600">
                    {dataSuggested.is_24_7 ? '24/7' : dataSuggestText}
                  </span>
                  <Badge
                    status={
                      scheduleSuggest.confidence === 'high'
                        ? 'success'
                        : scheduleSuggest.confidence === 'medium'
                          ? 'info'
                          : 'warn'
                    }
                    size="sm"
                  >
                    {CONFIDENCE_LABEL_FR[scheduleSuggest.confidence] || scheduleSuggest.confidence}
                  </Badge>
                </div>
                {scheduleSuggest.reasons?.map((r, i) => (
                  <p key={i} className="text-[10px] text-blue-500 mt-0.5">
                    {r}
                  </p>
                ))}
                <Button
                  variant="primary"
                  size="xs"
                  className="mt-1.5"
                  onClick={() => onApplySchedule(dataSuggested)}
                >
                  Appliquer
                </Button>
              </div>
            )}
            {scheduleSuggest?.error && (
              <p className="mt-1 text-xs text-amber-600">
                {scheduleSuggest.reasons?.[0] || scheduleSuggest.error}
              </p>
            )}
          </div>
          <div className="shrink-0 flex flex-col gap-1">
            {current ? (
              <Button variant="ghost" size="sm" onClick={() => {}}>
                Modifier
              </Button>
            ) : (
              <Button variant="secondary" size="sm" onClick={() => {}}>
                Appliquer
              </Button>
            )}
            <Button variant="ghost" size="xs" onClick={onSuggestSchedule} disabled={suggestLoading}>
              <Database size={12} />
              {suggestLoading ? 'Analyse...' : 'Suggérer depuis conso'}
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

const CONFIDENCE_TABS = [
  { id: 'facteurs', label: 'Facteurs' },
  { id: 'recommandations', label: 'Recommandations' },
];

function ConfidenceDrawer({ open, onClose, qualityConf, qualityScore, climate }) {
  const [tab, setTab] = useState('facteurs');
  const r2 = climate?.r_squared;
  const nPoints = climate?.n_points;
  const coverage = qualityConf?.pct;

  const factors = [
    {
      label: 'Score qualité',
      value: qualityScore != null ? `${qualityScore}/100` : '-',
      level: qualityScore >= 80 ? 'ok' : qualityScore >= 60 ? 'warn' : 'crit',
    },
    {
      label: 'R² signature',
      value: r2 != null ? fmtNum(r2, 2) : '-',
      level: r2 >= 0.6 ? 'ok' : r2 >= 0.3 ? 'warn' : 'crit',
    },
    {
      label: 'Points de données',
      value: nPoints != null ? `${nPoints} jours` : '-',
      level: nPoints >= 30 ? 'ok' : nPoints >= 10 ? 'warn' : 'crit',
    },
    {
      label: 'Couverture',
      value: coverage != null ? `${coverage}%` : '-',
      level: coverage >= 60 ? 'ok' : coverage >= 30 ? 'warn' : 'crit',
    },
  ];

  const DOT_COLORS = { ok: 'bg-green-500', warn: 'bg-yellow-500', crit: 'bg-red-500' };

  return (
    <Drawer open={open} onClose={onClose} title="Confiance données — Détail" wide>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Badge
            status={
              qualityConf?.level === 'high'
                ? 'ok'
                : qualityConf?.level === 'medium'
                  ? 'warn'
                  : 'crit'
            }
          >
            {qualityConf?.level === 'high'
              ? 'Forte'
              : qualityConf?.level === 'medium'
                ? 'Moyenne'
                : 'Faible'}
          </Badge>
          {qualityConf?.reason && (
            <span className="text-xs text-gray-500">{qualityConf.reason}</span>
          )}
        </div>

        <Tabs tabs={CONFIDENCE_TABS} active={tab} onChange={setTab} />

        {tab === 'facteurs' && (
          <div className="space-y-2">
            {factors.map((f) => (
              <div
                key={f.label}
                className="flex items-center justify-between bg-gray-50 rounded-lg p-3"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${DOT_COLORS[f.level] || DOT_COLORS.crit}`}
                  />
                  <span className="text-sm text-gray-700">{f.label}</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{f.value}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'recommandations' && (
          <div className="space-y-3">
            {qualityScore != null && qualityScore < 80 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                Vérifiez la qualité des données source: complétude des relevés, absence de trous et
                de doublons.
              </div>
            )}
            {r2 != null && r2 < 0.3 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                R² faible — la signature climatique n'est pas fiable. Augmentez la période d'analyse
                ou vérifiez les données météo.
              </div>
            )}
            {nPoints != null && nPoints < 30 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                Seulement {nPoints} jours de données. Augmentez la période d'analyse pour une
                confiance plus élevée (minimum 30 jours recommandés).
              </div>
            )}
            {(qualityScore == null || qualityScore >= 80) &&
              (r2 == null || r2 >= 0.3) &&
              (nPoints == null || nPoints >= 30) && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
                  Tous les facteurs de confiance sont satisfaisants. Les KPIs sont fiables.
                </div>
              )}
          </div>
        )}
      </div>
    </Drawer>
  );
}

const OFF_HOURS_TABS = [
  { id: 'methode', label: 'Méthode' },
  { id: 'hypotheses', label: 'Hypothèses' },
  { id: 'actions', label: 'Actions' },
];

function OffHoursDrawer({
  open,
  onClose,
  offHoursRatio,
  offHoursKwh,
  schedule,
  emissions,
  onCreateAction,
  siteId: drawerSiteId,
}) {
  const [tab, setTab] = useState('methode');
  const estimate = computeOffHoursEstimate(offHoursKwh);
  const navTo = useNavigate();

  return (
    <Drawer open={open} onClose={onClose} title="Hors Horaires — Détail" wide>
      <div className="space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          {offHoursRatio != null && (
            <Badge status={offHoursRatio <= 0.2 ? 'ok' : offHoursRatio <= 0.4 ? 'warn' : 'crit'}>
              {fmtNum(offHoursRatio * 100)}%
            </Badge>
          )}
          {offHoursKwh > 0 && (
            <span className="text-sm text-orange-600 font-medium">
              {fmtNum(offHoursKwh, 0)} kWh (90j)
            </span>
          )}
          {estimate.eur > 0 && (
            <span className="text-sm text-red-600 font-medium">{estimate.label}</span>
          )}
        </div>

        <Tabs tabs={OFF_HOURS_TABS} active={tab} onChange={setTab} />

        {tab === 'methode' && (
          <div className="space-y-3">
            <DrawerSection title="Définition">
              <p className="text-sm text-gray-600">
                Énergie consommée en dehors des heures d'exploitation définies dans le planning du
                site.
              </p>
              <DrawerRow label="Ratio">
                {offHoursRatio != null ? `${fmtNum(offHoursRatio * 100)}%` : '-'}
              </DrawerRow>
              <DrawerRow label="kWh (90 jours)">
                {offHoursKwh != null ? fmtNum(offHoursKwh, 0) : '-'}
              </DrawerRow>
              {emissions?.off_hours_co2e_kg > 0 && (
                <DrawerRow label="CO₂e hors horaires">
                  {fmtNum(emissions.off_hours_co2e_kg, 0)} kgCO₂e
                </DrawerRow>
              )}
            </DrawerSection>
            <DrawerSection title="Horaires actuels">
              {schedule ? (
                <>
                  <DrawerRow label="Jours">{schedule.open_days || '-'}</DrawerRow>
                  <DrawerRow label="Heures">
                    {schedule.is_24_7 ? '24/7' : `${schedule.open_time}-${schedule.close_time}`}
                  </DrawerRow>
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-gray-400">
                    Horaires non définis — le ratio est basé sur un profil par défaut.
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      onClose();
                      navTo(toPatrimoine({ site_id: drawerSiteId }));
                    }}
                  >
                    <Clock size={14} />
                    Définir les horaires
                  </Button>
                </div>
              )}
            </DrawerSection>
            <DrawerSection title="Extrapolation">
              <DrawerRow label="Période mesurée">90 jours</DrawerRow>
              <DrawerRow label="Facteur annuel">x {fmtNum(365 / 90, 2)}</DrawerRow>
              <DrawerRow label="kWh annuel estimé">
                {offHoursKwh > 0 ? fmtNum(offHoursKwh * (365 / 90), 0) : '-'}
              </DrawerRow>
            </DrawerSection>
          </div>
        )}

        {tab === 'hypotheses' && (
          <div className="space-y-3">
            <DrawerSection title="Prix de référence">
              <DrawerRow label="Prix kWh">
                {estimate.price} EUR/kWh <ModeBadge mode={estimate.mode} />
              </DrawerRow>
              <DrawerRow label="Source">
                {estimate.mode === 'CONTRAT'
                  ? 'Contrat fournisseur'
                  : estimate.mode === 'TARIF'
                    ? 'Profil tarifaire site'
                    : 'Tarif moyen tertiaire France (estimation)'}
              </DrawerRow>
            </DrawerSection>
            {estimate.assumptions?.length > 0 && (
              <DrawerSection title="Détail du calcul">
                {estimate.assumptions.map((a, i) => (
                  <p key={i} className="text-xs text-gray-500">
                    {a}
                  </p>
                ))}
              </DrawerSection>
            )}
            {estimate.mode === 'DEMO' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                Les montants affichés sont des estimations. Renseignez vos tarifs réels pour un
                chiffrage précis.
              </div>
            )}
          </div>
        )}

        {tab === 'actions' && (
          <div className="space-y-3">
            <DrawerSection title="Action recommandée">
              <p className="text-sm text-gray-600">
                Réduire la consommation hors horaires d'exploitation par ajustement des équipements
                CVC, éclairage, et veilles.
              </p>
            </DrawerSection>
            {estimate.eur > 0 && (
              <Button
                variant="primary"
                size="sm"
                onClick={() =>
                  onCreateAction({
                    titre: `Réduction conso hors horaires — Site`,
                    type: 'conso',
                    impact_eur: estimate.eur,
                    description: `Hors horaires ${offHoursRatio != null ? fmtNum(offHoursRatio * 100) : '?'}% — ${fmtNum(offHoursKwh, 0)} kWh sur 90j. Estimation: ${estimate.label}.`,
                  })
                }
              >
                <Zap size={14} />
                Créer action ({estimate.label})
              </Button>
            )}
          </div>
        )}
      </div>
    </Drawer>
  );
}

function _filterOutliers(points) {
  if (points.length < 5) return points;
  const vals = points.map((p) => p.kwh).sort((a, b) => a - b);
  const q1 = vals[Math.floor(vals.length * 0.25)];
  const q3 = vals[Math.floor(vals.length * 0.75)];
  const iqr = q3 - q1;
  const upper = q3 + 3 * iqr;
  const lower = q1 - 3 * iqr;
  return points.filter((p) => p.kwh >= lower && p.kwh <= upper);
}

function ClimateScatter({ climate }) {
  if (!climate || !climate.scatter || climate.scatter.length === 0) {
    const reason = climate?.reason;
    const msg = reason ? CLIMATE_REASONS[reason] || reason : 'Pas de données climatiques.';
    return (
      <div className="text-center py-12">
        <Thermometer size={28} className="mx-auto text-gray-200 mb-2" />
        <p className="text-sm text-gray-400">{msg}</p>
        {reason && <p className="text-xs text-gray-300 mt-1">code: {reason}</p>}
      </div>
    );
  }

  const filtered = _filterOutliers(climate.scatter);
  const removed = climate.scatter.length - filtered.length;

  return (
    <div>
      <ResponsiveContainer width="100%" height={250}>
        <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="T"
            name="Température (°C)"
            unit=" °C"
            tick={{ fontSize: 11 }}
            type="number"
          />
          <YAxis
            dataKey="kwh"
            name="Conso. journalière"
            unit=" kWh/j"
            tick={{ fontSize: 11 }}
            type="number"
          />
          <RTooltip cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={filtered} fill="#0072B2" fillOpacity={0.55} r={3} name="Jours" />
          {climate.fit_line && climate.fit_line.length > 0 && (
            <Scatter
              data={climate.fit_line}
              fill="none"
              line={{ stroke: '#E69F00', strokeWidth: 2.5 }}
              shape={() => null}
              name="Régression"
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        {climate.slope_kw_per_c != null && (
          <span>Pente: {fmtNum(climate.slope_kw_per_c, 1)} (kWh/j)/°C</span>
        )}
        {climate.balance_point_c != null && (
          <span>Tb: {fmtNum(climate.balance_point_c, 1)} °C</span>
        )}
        {climate.r_squared != null && <span>R²: {fmtNum(climate.r_squared, 2)}</span>}
        {climate.label && <span>{CLIMATE_LABEL_FR[climate.label] || climate.label}</span>}
        {removed > 0 && (
          <span className="text-orange-400">
            {removed} outlier{removed > 1 ? 's' : ''} masqué{removed > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  );
}

// --- Drawer helpers ---

function DrawerSection({ title, children }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-1.5">
      <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{title}</h4>
      {children}
    </div>
  );
}

function DrawerRow({ label, children }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{children}</span>
    </div>
  );
}

function InsightDrawer({ alert, open, onClose, onAck, onResolve, onCreateAction, onOpenExplorer }) {
  const [tab, setTab] = useState('evidence');
  if (!alert) return null;

  const typeLabel = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type;
  const stCfg = STATUS_CONFIG[alert.status] || STATUS_CONFIG.open;
  const evidence = alert.evidence || {};
  const kbLink = alert.kb_link || {};

  return (
    <Drawer open={open} onClose={onClose} title={typeLabel} wide>
      <div className="space-y-4">
        {/* Header badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge status={stCfg.badge}>{stCfg.label}</Badge>
          <Badge status={SEVERITY_BADGE[alert.severity] || 'neutral'}>
            {SEVERITY_LABEL_FR[alert.severity] || alert.severity}
          </Badge>
          {alert.estimated_impact_kwh > 0 && (
            <span className="text-xs text-orange-600 font-medium">
              {alert.estimated_impact_kwh} kWh
            </span>
          )}
          {alert.estimated_impact_eur > 0 && (
            <span className="text-xs text-red-600 font-medium">
              {alert.estimated_impact_eur} EUR
            </span>
          )}
        </div>

        <p className="text-sm text-gray-700">{alert.explanation}</p>
        {alert.recommended_action && (
          <p className="text-sm text-blue-700 bg-blue-50 rounded-lg p-2">
            {alert.recommended_action}
          </p>
        )}

        <Tabs tabs={DRAWER_TABS} active={tab} onChange={setTab} />

        {/* Evidence tab */}
        {tab === 'evidence' && (
          <div className="space-y-3">
            {Object.keys(evidence).length > 0 ? (
              <DrawerSection title="Preuve">
                {Object.entries(evidence).map(([k, v]) => (
                  <DrawerRow key={k} label={k}>
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </DrawerRow>
                ))}
              </DrawerSection>
            ) : (
              <p className="text-sm text-gray-400 text-center py-4">Pas de preuve détaillée.</p>
            )}
            {Object.keys(kbLink).length > 0 && (
              <DrawerSection title="Base de connaissances">
                <DrawerRow label="Type">{kbLink.item_type}</DrawerRow>
                <DrawerRow label="Code">{kbLink.code}</DrawerRow>
              </DrawerSection>
            )}
          </div>
        )}

        {/* Methode tab */}
        {tab === 'methode' && (
          <div className="space-y-3">
            <DrawerSection title="Méthode de détection">
              <DrawerRow label="Type">{typeLabel}</DrawerRow>
              <DrawerRow label="Sévérité">
                {SEVERITY_LABEL_FR[alert.severity] || alert.severity}
              </DrawerRow>
              <DrawerRow label="Moteur">Moteur Monitoring v1.0</DrawerRow>
            </DrawerSection>
            <DrawerSection title="Seuils">
              <DrawerRow label="Seuil déclenchement">Calculé par le moteur d'alertes</DrawerRow>
              <DrawerRow label="Confiance">
                {alert.severity === 'critical' ? 'Haute' : 'Moyenne'}
              </DrawerRow>
            </DrawerSection>
          </div>
        )}

        {/* Actions tab */}
        {tab === 'actions' && (
          <div className="space-y-3">
            {alert.recommended_action ? (
              <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                <Zap size={16} className="text-blue-500 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-gray-800">{alert.recommended_action}</p>
                  {alert.estimated_impact_eur > 0 && (
                    <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded mt-1 inline-block">
                      Impact: {alert.estimated_impact_eur} EUR/an
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">Aucune action recommandée.</p>
            )}
          </div>
        )}

        {/* CTAs */}
        <div className="pt-3 border-t border-gray-100 space-y-2">
          <button
            onClick={() => onOpenExplorer(alert)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
          >
            <BarChart3 size={15} className="text-blue-600" />
            Ouvrir dans Explorer
            <ExternalLink size={12} className="ml-auto text-gray-300" />
          </button>
          <button
            onClick={() => onCreateAction(alert)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition"
          >
            <Zap size={15} />
            Créer une action
          </button>
          <div className="flex items-center gap-2">
            {alert.status === 'open' && (
              <button
                onClick={() => onAck(alert.id)}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-blue-200 text-sm font-medium text-blue-700 hover:bg-blue-50 transition"
              >
                <UserCheck size={14} /> Prendre en charge
              </button>
            )}
            {(alert.status === 'open' || alert.status === 'ack') && (
              <button
                onClick={() => onResolve(alert.id)}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-green-200 text-sm font-medium text-green-700 hover:bg-green-50 transition"
              >
                <CheckCircle2 size={14} /> Résolu
              </button>
            )}
          </div>
        </div>

        <div className="text-[10px] text-gray-400 pt-1">
          Alerte #{alert.id}
          {alert.created_at && ` · ${fmtDateFR(alert.created_at)}`}
        </div>
      </div>
    </Drawer>
  );
}

// --- Main component ---

export default function MonitoringPage() {
  const { scope, setSite, sitesLoading, orgSites } = useScope();
  const { isExpert } = useExpertMode();
  const navigate = useNavigate();
  const { toast } = useToast();
  const siteId = scope.siteId;

  const [kpis, setKpis] = useState(null);
  const [climate, setClimate] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [alertFilter, setAlertFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [demoProfile, setDemoProfile] = useState('office');

  // Usage suggest
  const [usageSuggest, setUsageSuggest] = useState(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [benchmark, setBenchmark] = useState(null);
  const [scheduleSuggest, setScheduleSuggest] = useState(null);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [compareMode, setCompareMode] = useState(null); // null|'previous'|'n-1'
  const [compareKpis, setCompareKpis] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // Drawer state
  const [drawerAlert, setDrawerAlert] = useState(null);
  const [showOffHoursDrawer, setShowOffHoursDrawer] = useState(false);
  const [showConfidenceDrawer, setShowConfidenceDrawer] = useState(false);
  const { openActionDrawer } = useActionDrawer();
  const [siteActions, setSiteActions] = useState([]);
  const [siteDq, setSiteDq] = useState(null);
  const [siteFreshness, setSiteFreshness] = useState(null);

  // D.1: Fetch site data quality
  useEffect(() => {
    if (!siteId) return;
    getDataQualityScore(siteId).then(setSiteDq).catch(() => setSiteDq(null));
  }, [siteId]);

  // D.2: Fetch site freshness
  useEffect(() => {
    if (!siteId) return;
    getSiteFreshness(siteId).then(setSiteFreshness).catch(() => setSiteFreshness(null));
  }, [siteId]);

  // --- Data loading ---

  const loadAll = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    try {
      const [kpiRes, alertRes, snapRes] = await Promise.allSettled([
        getMonitoringKpis(siteId).catch(() => null),
        getMonitoringAlerts(siteId),
        getMonitoringSnapshots(siteId),
      ]);
      const kpiData = kpiRes.status === 'fulfilled' ? kpiRes.value : null;
      setKpis(kpiData);
      setClimate(kpiData?.climate || null);
      setAlerts(alertRes.status === 'fulfilled' ? alertRes.value || [] : []);
      setSnapshots(snapRes.status === 'fulfilled' ? snapRes.value || [] : []);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }, [siteId]);

  const loadSiteActions = useCallback(async () => {
    if (!siteId) return;
    try {
      const list = await getActionsList({ site_id: siteId });
      setSiteActions(list.slice(0, 5));
    } catch {
      /* silent */
    }
  }, [siteId]);

  useEffect(() => {
    if (siteId) {
      loadAll();
      track('monitoring_view', { site_id: siteId });
      // Fetch usage suggestion + benchmark
      setUsageLoading(true);
      getUsageSuggest(siteId)
        .then(setUsageSuggest)
        .catch(() => setUsageSuggest(null))
        .finally(() => setUsageLoading(false));
      getEmsBenchmark(siteId)
        .then(setBenchmark)
        .catch(() => setBenchmark(null));
      loadSiteActions();
    }
  }, [siteId, loadAll, loadSiteActions]);

  // Compare period
  useEffect(() => {
    if (!siteId || !compareMode) {
      setCompareKpis(null);
      return;
    }
    setCompareLoading(true);
    getMonitoringKpisCompare(siteId, compareMode)
      .then((res) => setCompareKpis(res?.compare || null))
      .catch(() => setCompareKpis(null))
      .finally(() => setCompareLoading(false));
  }, [siteId, compareMode]);

  // --- Actions ---

  const handleRun = async () => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    try {
      await runMonitoring(siteId, 90);
      track('monitoring_run', { site_id: siteId });
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handleDemo = async () => {
    if (!siteId) return;
    setDemoLoading(true);
    setError(null);
    try {
      await generateMonitoringDemo(siteId, 90, demoProfile);
      track('monitoring_demo', { site_id: siteId, profile: demoProfile });
      await runMonitoring(siteId, 90);
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
    setDemoLoading(false);
  };

  const handleAck = async (id) => {
    try {
      await ackMonitoringAlert(id);
      track('monitoring_ack', { alert_id: id });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: 'ack' } : a)));
      if (drawerAlert?.id === id) setDrawerAlert((d) => ({ ...d, status: 'ack' }));
    } catch {
      toast("Erreur lors de l'acquittement", 'error');
    }
  };

  const handleResolve = async (id) => {
    try {
      await resolveMonitoringAlert(id, 'Résolu depuis UI');
      track('monitoring_resolve', { alert_id: id });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: 'resolved' } : a)));
      if (drawerAlert?.id === id) setDrawerAlert((d) => ({ ...d, status: 'resolved' }));
    } catch {
      toast('Erreur lors de la résolution', 'error');
    }
  };

  const openInsightDrawer = (alert) => {
    setDrawerAlert(alert);
    track('monitoring_drawer_open', { alert_type: alert.alert_type });
  };

  const handleCreateAction = (alert) => {
    openActionDrawer(
      {
        prefill: {
          titre: `${ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type} — Site ${siteId}`,
          type: 'conso',
          impact_eur: alert.estimated_impact_eur || '',
          description: alert.explanation || '',
        },
        siteId: siteId ? Number(siteId) : null,
        sourceType: 'insight',
      },
      {
        onSave: async () => {
          track('monitoring_action_created', { site_id: siteId });
          await loadSiteActions();
        },
      }
    );
  };

  const handleSuggestSchedule = async () => {
    if (!siteId) return;
    setSuggestLoading(true);
    try {
      const result = await getScheduleSuggest(siteId, 90);
      setScheduleSuggest(result);
      track('schedule_suggest', { site_id: siteId, confidence: result.confidence });
    } catch {
      setScheduleSuggest({ error: 'request_failed', reasons: ["Erreur lors de l'analyse"] });
    }
    setSuggestLoading(false);
  };

  const handleApplySchedule = async (suggested) => {
    if (!siteId || !suggested) return;
    try {
      await putSiteSchedule(siteId, suggested);
      toast('Horaires appliqués avec succès', 'success');
      track('schedule_apply', { site_id: siteId });
      setScheduleSuggest(null);
      // Reload to reflect new schedule
      await loadAll();
    } catch {
      toast("Erreur lors de l'application des horaires", 'error');
    }
  };

  const handleOpenExplorer = (_alert) => {
    const explorerOpts = { site_id: siteId };
    if (kpis?.period) {
      const parts = kpis.period.split(' - ');
      if (parts[0]) explorerOpts.date_from = parts[0];
      if (parts[1]) explorerOpts.date_to = parts[1];
    }
    navigate(toConsoExplorer(explorerOpts));
  };

  // --- Helpers ---

  const benchmarkLabel = (key) => {
    if (!benchmark || benchmark.insufficient || !benchmark.benchmarks?.[key]) return '';
    const b = benchmark.benchmarks[key];
    return ` · Bench: P${b.percentile}`;
  };
  const benchmarkTip = (key) => {
    if (!benchmark || benchmark.insufficient || !benchmark.benchmarks?.[key])
      return 'Benchmark: données insuffisantes';
    const b = benchmark.benchmarks[key];
    return `Benchmark (${benchmark.peer_count} pairs): P25=${b.p25} P50=${b.p50} P75=${b.p75} — votre P${b.percentile}`;
  };

  // --- Derived data ---

  const kpiData = kpis?.kpis || {};
  const qualityScore = kpis?.data_quality_score ?? null;
  const riskScore = kpis?.risk_power_score ?? null;
  const schedule = kpis?.schedule || null;
  const offHoursRatio = kpiData.off_hours_ratio ?? null;
  const offHoursKwh = kpiData.off_hours_kwh ?? null;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const impact = useMemo(() => kpis?.impact || {}, [kpis]);
  const emissions = kpis?.emissions || {};
  const offHoursEstimate = useMemo(() => {
    // Use server-side impact if available, fallback to client-side
    if (impact?.off_hours?.eur_year != null) {
      const eur = impact.off_hours.eur_year;
      return {
        eur,
        label: `~${fmtNum(eur, 0)} EUR/an`,
        price: impact.off_hours.price_eur_kwh,
        mode: impact.off_hours.mode,
        confidence: impact.off_hours.confidence,
        assumptions: impact.off_hours.assumptions,
      };
    }
    return computeOffHoursEstimate(offHoursKwh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offHoursKwh, impact]);

  const weekdayProfile = kpiData.weekday_profile_kw;
  const weekendProfile = kpiData.weekend_profile_kw;

  const weekdayBarData = useMemo(() => {
    if (!weekdayProfile || !Array.isArray(weekdayProfile)) return null;
    return weekdayProfile.map((kw, hour) => ({
      hour: `${hour}h`,
      kw: kw != null ? Number(kw.toFixed(1)) : 0,
    }));
  }, [weekdayProfile]);

  const heatmapData = useMemo(
    () => buildHeatmapGrid(weekdayProfile, weekendProfile),
    [weekdayProfile, weekendProfile]
  );

  const filteredAlerts = useMemo(() => {
    let filtered = alerts;
    if (alertFilter !== 'all') filtered = filtered.filter((a) => a.status === alertFilter);
    if (severityFilter !== 'all') filtered = filtered.filter((a) => a.severity === severityFilter);
    return filtered;
  }, [alerts, alertFilter, severityFilter]);

  const groupedAlerts = useMemo(() => groupInsights(filteredAlerts), [filteredAlerts]);

  const openCount = alerts.filter((a) => a.status === 'open').length;

  const allOrgSites = orgSites;

  // Confidence
  const climateConf = useMemo(
    () =>
      computeConfidence({
        r2: climate?.r_squared,
        nPoints: climate?.n_points,
        reason: climate?.reason,
      }),
    [climate]
  );

  const qualityConf = useMemo(
    () =>
      computeConfidence({
        coveragePct: kpis?.data_quality_details?.completeness_pct,
      }),
    [kpis]
  );

  // Load factor: archetype-aware thresholds
  const archetype = demoProfile || 'default';
  const archetypeLabel =
    PROFILE_OPTIONS.find((p) => p.value === archetype)?.label || 'Tertiaire (défaut)';
  const isDefaultArchetype = !demoProfile || !LF_THRESHOLDS_BY_ARCHETYPE[demoProfile];
  const lfThresholds = useMemo(() => {
    return LF_THRESHOLDS_BY_ARCHETYPE[archetype] || LF_THRESHOLDS_BY_ARCHETYPE.default;
  }, [archetype]);

  // KPI statuses (all confidence-aware)
  const qualityStatus = kpiStatusWithConfidence(
    qualityScore,
    KPI_THRESHOLDS.quality,
    false,
    qualityConf
  );
  const riskStatus = kpiStatusWithConfidence(riskScore, KPI_THRESHOLDS.risk, true, qualityConf);
  const lfStatus = kpiStatusWithConfidence(
    kpiData.load_factor != null ? kpiData.load_factor * 100 : null,
    lfThresholds,
    false,
    qualityConf
  );
  const climateStatus = kpiStatusWithConfidence(
    climate?.slope_kw_per_c,
    KPI_THRESHOLDS.climate,
    true,
    climateConf
  );

  // V18-B: guard — don't show empty state while sites are loading
  if (sitesLoading) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Électrique"
        subtitle="Synchronisation du périmètre…"
      >
        <div className="p-8 flex items-center justify-center text-gray-400 text-sm gap-2">
          <Loader2 size={16} className="animate-spin" />
          Synchronisation du périmètre…
        </div>
      </PageShell>
    );
  }

  // --- No site selected ---

  if (!siteId) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Électrique"
        subtitle="KPIs, puissance, qualité de données & alertes"
        actions={
          <select
            className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
            value=""
            onChange={(e) => setSite(Number(e.target.value))}
          >
            <option value="">Choisir un site...</option>
            {allOrgSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nom || `Site ${s.id}`}
              </option>
            ))}
          </select>
        }
      >
        <EmptyState
          icon={Activity}
          title="Sélectionnez un site"
          text="Choisissez un site dans le sélecteur ci-dessus pour voir les KPIs de performance électrique."
        />
      </PageShell>
    );
  }

  // --- Loading skeleton ---

  if (loading && !kpis && alerts.length === 0) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Électrique"
        subtitle="KPIs, puissance, qualité de données & alertes"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <Skeleton rows={6} />
      </PageShell>
    );
  }

  if (error && !kpis) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Électrique"
        subtitle="KPIs, puissance, qualité de données & alertes"
      >
        <ErrorState
          message={error || 'Erreur de chargement'}
          onRetry={loadAll}
        />
      </PageShell>
    );
  }

  const hasData = kpis || alerts.length > 0 || snapshots.length > 0;

  return (
    <PageShell
      icon={Activity}
      title="Performance Électrique"
      subtitle="KPIs, puissance, qualité de données & alertes"
      actions={
        <>
          <select
            className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
            value={siteId || ''}
            onChange={(e) => setSite(Number(e.target.value))}
          >
            {allOrgSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nom || `Site ${s.id}`}
              </option>
            ))}
          </select>
          {siteDq && <DataQualityBadge score={siteDq.score} size="sm" />}
          {siteFreshness && <FreshnessIndicator freshness={siteFreshness} size="sm" />}
          <Link
            to={toConsoExplorer({ site_id: siteId })}
            className="flex items-center gap-1 px-3 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition"
          >
            <ExternalLink size={14} />
            Explorer
          </Link>
          <Button variant="secondary" size="sm" onClick={handleRun} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Analyse...' : 'Lancer Analyse'}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleOpenExplorer(null)}>
            <BarChart3 size={14} />
            Explorer
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(toConsoDiag({ site_id: siteId }))}
          >
            <Eye size={14} />
            Diagnostics
          </Button>
        </>
      }
    >
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Empty state with demo CTA */}
      {!hasData && (
        <div>
          <EmptyState
            icon={Database}
            title="Aucune donnée de monitoring"
            text="Générez des données de démo pour explorer les KPIs de performance électrique, les profils jour-type et les alertes automatiques."
            ctaLabel={demoLoading ? 'Génération...' : 'Générer Données Démo'}
            onCta={handleDemo}
          />
          <div className="flex items-center justify-center gap-2 mt-4">
            <label className="text-sm text-gray-500">Profil:</label>
            <select
              className="border rounded-lg px-2 py-1 text-sm"
              value={demoProfile}
              onChange={(e) => setDemoProfile(e.target.value)}
            >
              {PROFILE_OPTIONS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {hasData && (
        <>
          {/* ═══ SECTION A — Header pilotage ═══ */}
          <div data-section="header-pilotage" className="mb-6">
            {/* Usage Panel */}
            <UsagePanel
              usage={usageSuggest}
              loading={usageLoading}
              scheduleSuggest={scheduleSuggest}
              onSuggestSchedule={handleSuggestSchedule}
              onApplySchedule={handleApplySchedule}
              suggestLoading={suggestLoading}
            />

            {/* Quick Actions Bar with primary CTA */}
            <QuickActionsBar
              onOpenExplorer={() => handleOpenExplorer(null)}
              onCreateAction={() => {
                openActionDrawer(
                  {
                    prefill: { titre: `Action — Site ${siteId}`, type: 'conso' },
                    siteId: siteId ? Number(siteId) : null,
                    sourceType: 'insight',
                  },
                  {
                    onSave: async () => {
                      track('monitoring_action_created', { site_id: siteId });
                      await loadSiteActions();
                    },
                  }
                );
              }}
              compareEnabled={!!kpis?.period}
              compareMode={compareMode}
              onCompareChange={setCompareMode}
              compareLoading={compareLoading}
            />

            {/* Confidence badge */}
            {qualityConf && (
              <div className="flex items-center gap-2 mb-3">
                <button
                  onClick={() => setShowConfidenceDrawer(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition hover:shadow-sm"
                  style={{
                    borderColor:
                      qualityConf.level === 'high'
                        ? '#bbf7d0'
                        : qualityConf.level === 'medium'
                          ? '#fde68a'
                          : '#fecaca',
                    backgroundColor:
                      qualityConf.level === 'high'
                        ? '#f0fdf4'
                        : qualityConf.level === 'medium'
                          ? '#fffbeb'
                          : '#fef2f2',
                    color:
                      qualityConf.level === 'high'
                        ? '#15803d'
                        : qualityConf.level === 'medium'
                          ? '#a16207'
                          : '#dc2626',
                  }}
                >
                  <Database size={12} />
                  <Explain term="data_confidence">Confiance données</Explain> :{' '}
                  {qualityConf.level === 'high'
                    ? 'Forte'
                    : qualityConf.level === 'medium'
                      ? 'Moyenne'
                      : 'Faible'}
                </button>
                {impact?.price?.mode && (
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <ModeBadge mode={impact.price.mode} />
                  </span>
                )}
              </div>
            )}
          </div>

          {/* ═══ SECTION B — À retenir ═══ */}
          <div data-section="a-retenir" className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <Info size={16} className="text-blue-500" />À retenir
            </h2>
            <ExecutiveSummary
              alerts={alerts}
              kpiData={kpiData}
              climate={climate}
              qualityScore={qualityScore}
              qualityConf={qualityConf}
              offHoursKwh={offHoursKwh}
              emissions={emissions}
              navigate={navigate}
              siteId={siteId}
              isExpert={isExpert}
              onOpenExplorer={() => handleOpenExplorer(null)}
              onCreateAction={(a) => {
                if (a) handleCreateAction(a);
                else {
                  openActionDrawer(
                    {
                      prefill: { titre: `Action — Site ${siteId}`, type: 'conso' },
                      siteId: siteId ? Number(siteId) : null,
                      sourceType: 'insight',
                    },
                    {
                      onSave: async () => {
                        track('monitoring_action_created', { site_id: siteId });
                        await loadSiteActions();
                      },
                    }
                  );
                }
              }}
              onInsight={(a) => openInsightDrawer(a)}
              onConfidenceDetail={() => setShowConfidenceDrawer(true)}
            />
          </div>

          {/* ═══ SECTION C — Plan d'action ═══ */}
          <div data-section="plan-action" className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <Zap size={16} className="text-orange-500" />
              Plan d'action
              {openCount > 0 && <Badge status="crit">{openCount} à traiter</Badge>}
            </h2>
            {(() => {
              const topPriorities = alerts
                .filter((a) => a.status === 'open' && a.estimated_impact_eur > 0)
                .sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0))
                .slice(0, 3);
              if (topPriorities.length === 0) {
                return (
                  <Card>
                    <CardBody className="py-6 text-center">
                      <CheckCircle size={24} className="mx-auto text-green-300 mb-2" />
                      <p className="text-sm text-gray-500">
                        Aucune priorité détectée. Lancez une analyse pour identifier des
                        opportunités.
                      </p>
                    </CardBody>
                  </Card>
                );
              }
              return (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {topPriorities.map((a, i) => (
                    <Card key={a.id}>
                      <CardBody className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-orange-50 text-orange-600 font-bold text-sm shrink-0">
                            {i + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-800">
                              {ALERT_TYPE_LABELS[a.alert_type] || a.alert_type}
                            </p>
                            <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">
                              {a.explanation}
                            </p>
                            {a.estimated_impact_eur > 0 && (
                              <p className="text-sm font-bold text-red-600 mt-1">
                                {fmtNum(a.estimated_impact_eur, 0)} EUR/an
                              </p>
                            )}
                            <div className="flex items-center gap-2 mt-2">
                              <button
                                onClick={() => openInsightDrawer(a)}
                                className="text-xs font-medium text-gray-500 hover:text-gray-700 flex items-center gap-1"
                              >
                                <Eye size={10} /> Preuve
                              </button>
                              <button
                                onClick={() => handleCreateAction(a)}
                                className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
                              >
                                <Zap size={10} /> Créer action
                              </button>
                            </div>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Actions mini-list */}
          <ActionMiniList actions={siteActions} siteId={siteId} navigate={navigate} />

          {/* ═══ SECTION D — Détails ═══ */}
          <div data-section="details" className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <BarChart3 size={16} className="text-indigo-500" />
              Détails
            </h2>

            {/* Compare period banner */}
            {compareKpis && (
              <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                <TrendingUp size={12} />
                <span>
                  Comparaison: <strong>{compareKpis.period}</strong>
                </span>
                <button
                  onClick={() => setCompareMode(null)}
                  className="ml-auto text-blue-400 hover:text-blue-600"
                >
                  Fermer
                </button>
              </div>
            )}

            {/* KPI Strip — 4 cols × 2 rows for readability */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
              <StatusKpiCard
                icon={Zap}
                title="Pmax / P95"
                value={kpiData.pmax_kw != null ? `${fmtNum(kpiData.pmax_kw)} kW` : '-'}
                sub={`P95: ${fmtNum(kpiData.p95_kw)} kW${benchmarkLabel('pmax_kw')}`}
                tooltip={`${KPI_TOOLTIPS.pmax}\n${benchmarkTip('pmax_kw')}`}
                status="ok"
                color="bg-yellow-500"
              />
              <StatusKpiCard
                icon={TrendingUp}
                title="Talon / Base"
                value={kpiData.pbase_kw != null ? `${fmtNum(kpiData.pbase_kw)} kW` : '-'}
                sub={`Nuit: ${fmtNum(kpiData.pbase_night_kw)} kW${benchmarkLabel('pbase_kw')}`}
                tooltip={`Talon = consommation mini hors périodes d'activité.\n${benchmarkTip('pbase_kw')}`}
                status="ok"
                color="bg-blue-500"
              />
              <StatusKpiCard
                icon={Activity}
                title="Facteur de charge"
                value={kpiData.load_factor != null ? `${fmtNum(kpiData.load_factor * 100)}%` : '-'}
                sub={`Pic/Moy: ${fmtNum(kpiData.peak_to_average)}x · ${archetypeLabel}${benchmarkLabel('load_factor')}`}
                tooltip={`${KPI_TOOLTIPS.loadFactor}\nProfil: ${archetypeLabel} (OK >= ${lfThresholds.ok}%, Attention >= ${lfThresholds.warn}%)${isDefaultArchetype ? '\n⚠ Profil par défaut — choisissez un profil pour des seuils adaptés.' : ''}\n${benchmarkTip('load_factor')}`}
                status={lfStatus}
                color="bg-indigo-500"
                message={(() => {
                  const msg = getKpiMessage('load_factor', kpiData.load_factor != null ? kpiData.load_factor * 100 : null, { archetype: archetypeLabel });
                  if (!msg) return null;
                  return (
                    <p className={`text-[11px] mt-1 px-3 pb-2 ${
                      msg.severity === 'crit' ? 'text-red-600' : msg.severity === 'warn' ? 'text-amber-600' : 'text-gray-500'
                    }`} data-testid="kpi-message-load-factor">
                      {isExpert ? msg.expert : msg.simple}
                    </p>
                  );
                })()}
              />
              <StatusKpiCard
                icon={Shield}
                title="Risque Puissance"
                value={riskScore != null ? `${riskScore}/100` : '-'}
                sub={
                  riskScore != null
                    ? riskScore < 35
                      ? 'Marge confortable'
                      : riskScore < 60
                        ? 'À surveiller'
                        : 'Dépassement probable'
                    : ''
                }
                tooltip={KPI_TOOLTIPS.risk}
                status={riskStatus}
                color={
                  riskScore >= 60
                    ? 'bg-red-500'
                    : riskScore >= 35
                      ? 'bg-orange-500'
                      : 'bg-green-500'
                }
                confidence={qualityConf}
              />
              <StatusKpiCard
                icon={CheckCircle}
                title="Qualité Données"
                value={qualityScore != null ? `${qualityScore}/100` : '-'}
                sub={
                  qualityScore != null
                    ? qualityScore >= 80
                      ? 'Excellente'
                      : qualityScore >= 60
                        ? 'Correcte'
                        : 'Dégradée'
                    : ''
                }
                tooltip={KPI_TOOLTIPS.quality}
                status={qualityStatus}
                color={
                  qualityScore >= 80
                    ? 'bg-green-500'
                    : qualityScore >= 60
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                }
                confidence={qualityConf}
                message={(() => {
                  const msg = getKpiMessage('data_quality_score', qualityScore);
                  if (!msg) return null;
                  return (
                    <p className={`text-[11px] mt-1 px-3 pb-2 ${
                      msg.severity === 'crit' ? 'text-red-600' : msg.severity === 'warn' ? 'text-amber-600' : 'text-gray-500'
                    }`} data-testid="kpi-message-data-quality">
                      {isExpert ? msg.expert : msg.simple}
                    </p>
                  );
                })()}
              />
              <StatusKpiCard
                icon={Clock}
                title={<Explain term="off_hours_ratio">Hors Horaires</Explain>}
                value={offHoursRatio != null ? `${fmtNum(offHoursRatio * 100)}%` : '-'}
                sub={
                  schedule
                    ? schedule.is_24_7
                      ? '24/7 — pas de hors horaires'
                      : `${schedule.open_time}-${schedule.close_time}${offHoursEstimate.eur > 0 ? ` · ${offHoursEstimate.label}` : ''}`
                    : `Horaires non définis${offHoursEstimate.eur > 0 ? ` · ${offHoursEstimate.label}` : ''}`
                }
                tooltip={`Part d'énergie consommée en dehors des heures d'exploitation. Un ratio élevé signale un talon ou des équipements actifs la nuit/week-end.\nPrix: ${offHoursEstimate.price} EUR/kWh (${offHoursEstimate.mode || 'estimation'})`}
                status={
                  offHoursRatio != null
                    ? offHoursRatio <= 0.2
                      ? 'ok'
                      : offHoursRatio <= 0.4
                        ? 'surveiller'
                        : 'critique'
                    : 'no_data'
                }
                color={
                  offHoursRatio != null
                    ? offHoursRatio <= 0.2
                      ? 'bg-green-500'
                      : offHoursRatio <= 0.4
                        ? 'bg-orange-500'
                        : 'bg-red-500'
                    : 'bg-slate-400'
                }
                confidence={qualityConf}
                onClick={() => setShowOffHoursDrawer(true)}
                message={(() => {
                  const msg = getKpiMessage('off_hours_ratio', offHoursRatio);
                  if (!msg) return null;
                  return (
                    <p className={`text-[11px] mt-1 px-3 pb-2 ${
                      msg.severity === 'crit' ? 'text-red-600' : msg.severity === 'warn' ? 'text-amber-600' : 'text-gray-500'
                    }`} data-testid="kpi-message-off-hours">
                      {isExpert ? msg.expert : msg.simple}
                    </p>
                  );
                })()}
              />
              <StatusKpiCard
                icon={Leaf}
                title="CO₂e"
                value={
                  emissions.annualized_co2e_tonnes != null
                    ? `${fmtNum(emissions.annualized_co2e_tonnes)} t/an`
                    : '-'
                }
                sub={
                  emissions.total_co2e_kg != null
                    ? `${fmtNum(emissions.total_co2e_kg, 0)} kg sur ${emissions.days_covered || 90}j${emissions.off_hours_co2e_kg > 0 ? ` · Hors horaires: ${fmtNum(emissions.off_hours_co2e_kg, 0)} kg` : ''}`
                    : 'Facteur non disponible'
                }
                tooltip={`Émissions CO₂e estimées sur la période d'analyse.\nFacteur: ${emissions.factor?.kgco2e_per_kwh || '-'} kgCO₂e/kWh\nSource: ${emissions.factor?.source_label || '-'}\nQualité: ${emissions.factor?.quality || '-'}`}
                status={emissions.annualized_co2e_tonnes != null ? 'ok' : 'no_data'}
                color="bg-emerald-600"
              />
              {/* Climate KPI — 8th card in the same grid */}
              {climate && (
                <StatusKpiCard
                  icon={Thermometer}
                  title="Sensibilité Climatique"
                  value={
                    climate.slope_kw_per_c != null
                      ? `${fmtNum(climate.slope_kw_per_c, 1)} (kWh/j)/°C`
                      : '-'
                  }
                  sub={
                    climate.slope_kw_per_c != null
                      ? `R²: ${climate.r_squared != null ? fmtNum(climate.r_squared, 2) : '-'} | ${CLIMATE_LABEL_FR[climate.label] || climate.label || 'Non determine'}`
                      : CLIMATE_REASONS[climate.reason] || 'Analyse climatique non disponible'
                  }
                  tooltip={KPI_TOOLTIPS.climate}
                  status={climateStatus}
                  color={climate.slope_kw_per_c != null ? 'bg-cyan-500' : 'bg-slate-400'}
                  confidence={climateConf}
                />
              )}
            </div>

            {/* Expert: KPI technical details */}
            {isExpert && kpis && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 -mt-2">
                <div className="text-[10px] text-gray-400 font-mono">
                  Pmax: src={kpis.source || 'engine'} · period={kpis.period || '-'}
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  LF seuils: ok≥{lfThresholds.ok}% warn≥{lfThresholds.warn}% · arch={archetype}
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  Qualité: raw={qualityScore ?? 'null'} · conf={qualityConf?.pct ?? '-'}% · {qualityConf?.level || '-'}
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  Risque: raw={riskScore ?? 'null'} · status={riskStatus}
                  {climate?.r_squared != null ? ` · R²=${fmtNum(climate.r_squared, 3)}` : ''}
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  HH: ratio={offHoursRatio ?? 'null'} · kwh={offHoursKwh ?? 'null'}
                  · prix={offHoursEstimate.price} EUR/kWh ({offHoursEstimate.mode || 'est.'})
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  CO₂e: factor={emissions.factor?.kgco2e_per_kwh ?? '-'} · src={emissions.factor?.source_label || '-'}
                </div>
                {climate && (
                  <div className="text-[10px] text-gray-400 font-mono">
                    Climat: slope={climate.slope_kw_per_c ?? '-'} · Tb={climate.balance_point_c ?? '-'}°C
                    · n={climate.n_points ?? '-'}pts · label={climate.label || '-'}
                  </div>
                )}
                <div className="text-[10px] text-gray-400 font-mono">
                  Site ID: {siteId} · snap_count={snapshots.length} · alerts_total={alerts.length}
                </div>
              </div>
            )}

            {/* Compare deltas row */}
            {compareKpis?.kpis && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 -mt-2">
                <div className="text-center text-[10px] text-gray-400">
                  Pmax{' '}
                  <KpiDelta
                    current={kpiData.pmax_kw}
                    previous={compareKpis.kpis.pmax_kw}
                    lowerIsBetter
                  />
                </div>
                <div className="text-center text-[10px] text-gray-400">
                  Talon{' '}
                  <KpiDelta
                    current={kpiData.pbase_kw}
                    previous={compareKpis.kpis.pbase_kw}
                    lowerIsBetter
                  />
                </div>
                <div className="text-center text-[10px] text-gray-400">
                  LF{' '}
                  <KpiDelta current={kpiData.load_factor} previous={compareKpis.kpis.load_factor} />
                </div>
                <div className="text-center text-[10px] text-gray-400">
                  Risque{' '}
                  <KpiDelta
                    current={riskScore}
                    previous={compareKpis.risk_power_score}
                    lowerIsBetter
                  />
                </div>
                <div className="text-center text-[10px] text-gray-400">
                  Qualité{' '}
                  <KpiDelta current={qualityScore} previous={compareKpis.data_quality_score} />
                </div>
                <div className="text-center text-[10px] text-gray-400">
                  HH{' '}
                  <KpiDelta
                    current={offHoursRatio}
                    previous={compareKpis.kpis.off_hours_ratio}
                    lowerIsBetter
                  />
                </div>
              </div>
            )}

            {/* Graphs — 2x2 grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Signature jour-type: Semaine vs Weekend */}
              <Card>
                <CardBody>
                  <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <Clock size={18} /> Signature Jour-Type
                    <span className="text-[10px] text-gray-400 font-normal ml-auto">
                      Puissance moyenne (kW)
                    </span>
                  </h2>
                  <WeekdayWeekendChart
                    weekdayProfile={weekdayProfile}
                    weekendProfile={weekendProfile}
                  />
                  {isExpert && weekdayProfile && (
                    <details className="mt-3">
                      <summary className="text-[10px] text-gray-400 font-mono cursor-pointer hover:text-gray-600">
                        Données brutes (24h)
                      </summary>
                      <div className="mt-1 text-[10px] text-gray-400 font-mono leading-relaxed overflow-x-auto">
                        <div>Semaine: [{weekdayProfile.map((v, i) => `${i}h:${fmtNum(v, 1)}`).join(' · ')}]</div>
                        {weekendProfile && (
                          <div>Weekend: [{weekendProfile.map((v, i) => `${i}h:${fmtNum(v, 1)}`).join(' · ')}]</div>
                        )}
                      </div>
                    </details>
                  )}
                </CardBody>
              </Card>

              {/* Heatmap 7x24 */}
              <Card>
                <CardBody>
                  <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <Sun size={18} /> Heatmap 7j x 24h
                    <span className="text-[10px] text-gray-400 font-normal ml-auto">
                      kW moyen / creneau
                    </span>
                  </h2>
                  <HeatmapGrid data={heatmapData} />
                  {isExpert && heatmapData && (
                    <details className="mt-3">
                      <summary className="text-[10px] text-gray-400 font-mono cursor-pointer hover:text-gray-600">
                        Données brutes (7x24)
                      </summary>
                      <div className="mt-1 text-[10px] text-gray-400 font-mono leading-relaxed overflow-x-auto max-h-32 overflow-y-auto">
                        {heatmapData.map((row, d) => (
                          <div key={d}>{DAYS_FR[d]}: [{row.map((v) => fmtNum(v, 1)).join(', ')}]</div>
                        ))}
                      </div>
                    </details>
                  )}
                </CardBody>
              </Card>

              {/* Conso. vs Temperature */}
              <Card>
                <CardBody>
                  <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <Thermometer size={18} /> Conso. vs Température
                    <span className="text-[10px] text-gray-400 font-normal ml-auto">
                      kWh/jour vs °C
                    </span>
                  </h2>
                  <ClimateScatter climate={climate} />
                  {isExpert && climate?.scatter && climate.scatter.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-[10px] text-gray-400 font-mono cursor-pointer hover:text-gray-600">
                        Données brutes ({climate.scatter.length} points)
                      </summary>
                      <div className="mt-1 text-[10px] text-gray-400 font-mono leading-relaxed max-h-32 overflow-y-auto">
                        <div className="flex gap-4 font-semibold mb-0.5">
                          <span className="w-16">T (°C)</span>
                          <span className="w-20">kWh/j</span>
                        </div>
                        {climate.scatter.slice(0, 50).map((pt, i) => (
                          <div key={i} className="flex gap-4">
                            <span className="w-16">{fmtNum(pt.T, 1)}</span>
                            <span className="w-20">{fmtNum(pt.kwh, 1)}</span>
                          </div>
                        ))}
                        {climate.scatter.length > 50 && (
                          <div className="text-gray-300 mt-1">… +{climate.scatter.length - 50} points</div>
                        )}
                      </div>
                    </details>
                  )}
                </CardBody>
              </Card>

              {/* Courbe de charge BarChart */}
              <Card>
                <CardBody>
                  <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <BarChart3 size={18} /> Courbe de Charge (Semaine)
                    <span className="text-[10px] text-gray-400 font-normal ml-auto">
                      kW moyen / heure
                    </span>
                  </h2>
                  {weekdayBarData ? (
                    <>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={weekdayBarData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
                          <YAxis tick={{ fontSize: 11 }} unit=" kW" />
                          <RTooltip formatter={(v) => [`${v} kW`, 'Puissance']} />
                          <Bar dataKey="kw" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Puissance" />
                        </BarChart>
                      </ResponsiveContainer>
                      {isExpert && (
                        <details className="mt-3">
                          <summary className="text-[10px] text-gray-400 font-mono cursor-pointer hover:text-gray-600">
                            Données brutes (24h)
                          </summary>
                          <div className="mt-1 text-[10px] text-gray-400 font-mono leading-relaxed overflow-x-auto">
                            [{weekdayBarData.map((d) => `${d.hour}:${d.kw}`).join(' · ')}]
                          </div>
                        </details>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-12">
                      <BarChart3 size={32} className="mx-auto text-gray-200 mb-2" />
                      <p className="text-sm text-gray-400">
                        Lancez une analyse pour générer la courbe de charge.
                      </p>
                      <button
                        onClick={handleRun}
                        className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800"
                      >
                        Lancer analyse
                      </button>
                    </div>
                  )}
                </CardBody>
              </Card>
            </div>

            {/* Insights & Alerts */}
            <Card className="mb-6">
              <CardBody>
                <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                  <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                    <AlertTriangle size={18} className="text-orange-500" />
                    Insights & Alertes
                    {openCount > 0 && <Badge status="crit">{openCount} ouvertes</Badge>}
                    {groupedAlerts.length < filteredAlerts.length && (
                      <span className="text-[10px] text-gray-400 font-normal">
                        ({filteredAlerts.length} alertes → {groupedAlerts.length} groupes)
                      </span>
                    )}
                  </h2>
                  <div className="flex gap-1 flex-wrap">
                    {[
                      { key: 'all', label: 'Tous' },
                      { key: 'open', label: 'Ouverts' },
                      { key: 'ack', label: 'En cours' },
                      { key: 'resolved', label: 'Résolus' },
                    ].map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setAlertFilter(tab.key)}
                        className={`px-3 py-1 text-xs rounded-full font-medium transition ${
                          alertFilter === tab.key
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-500 hover:bg-gray-100'
                        }`}
                      >
                        {tab.label}
                        {tab.key !== 'all' &&
                          ` (${alerts.filter((a) => a.status === tab.key).length})`}
                      </button>
                    ))}
                    <span className="w-px bg-gray-200 mx-1" />
                    {[
                      { key: 'all', label: 'Toutes' },
                      { key: 'critical', label: 'Critiques' },
                      { key: 'high', label: 'Haute' },
                      { key: 'warning', label: 'Moyenne' },
                    ].map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setSeverityFilter(tab.key)}
                        className={`px-2 py-1 text-xs rounded-full font-medium transition ${
                          severityFilter === tab.key
                            ? 'bg-orange-100 text-orange-700'
                            : 'text-gray-400 hover:bg-gray-100'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {groupedAlerts.length === 0 ? (
                  <div className="text-center py-8">
                    <AlertTriangle size={28} className="mx-auto text-gray-200 mb-2" />
                    <p className="text-sm text-gray-400">
                      {alerts.length === 0
                        ? 'Aucune alerte. Lancez une analyse pour détecter les anomalies.'
                        : 'Aucune alerte pour ce filtre.'}
                    </p>
                    {alerts.length === 0 && (
                      <button
                        onClick={handleRun}
                        className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800"
                      >
                        Lancer analyse
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-gray-500">
                          {isExpert && <th className="pb-2 pr-4 text-[10px] font-mono">ID</th>}
                          <th className="pb-2 pr-4">Statut</th>
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4"><Explain term="severite">Sévérité</Explain></th>
                          <th className="pb-2 pr-4">Explication</th>
                          <th className="pb-2 pr-4 text-right">Impact (EUR)</th>
                          {isExpert && <th className="pb-2 pr-4 text-[10px] font-mono">Compteur</th>}
                          {isExpert && <th className="pb-2 pr-4 text-[10px] font-mono">kWh brut</th>}
                          <th className="pb-2">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {groupedAlerts.map((a) => {
                          const stCfg = STATUS_CONFIG[a.status] || STATUS_CONFIG.open;
                          return (
                            <tr
                              key={a.id}
                              className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                              onClick={() => openInsightDrawer(a)}
                            >
                              {isExpert && (
                                <td className="py-3 pr-4 text-[10px] text-gray-400 font-mono">
                                  #{a.id}{a._count > 1 ? ` (+${a._ids?.slice(1).join(',')})` : ''}
                                </td>
                              )}
                              <td className="py-3 pr-4">
                                <Badge status={stCfg.badge}>{stCfg.label}</Badge>
                              </td>
                              <td className="py-3 pr-4">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium whitespace-nowrap">
                                    {ALERT_TYPE_LABELS[a.alert_type] || a.alert_type}
                                  </span>
                                  {a._meters && a._meters.size > 1 && (
                                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-[10px] font-medium whitespace-nowrap">
                                      {a._meters.size} compteurs
                                    </span>
                                  )}
                                  {a._count > 1 && (
                                    <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-[10px] font-medium whitespace-nowrap">
                                      x{a._count}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-3 pr-4">
                                <Badge
                                  status={SEVERITY_BADGE[a._maxSeverity || a.severity] || 'neutral'}
                                >
                                  {a._maxSeverity || a.severity}
                                </Badge>
                              </td>
                              <td className="py-3 pr-4 text-gray-600 max-w-xs lg:max-w-md">
                                <span className="line-clamp-2">{a.explanation}</span>
                              </td>
                              <td className="py-3 pr-4 text-right font-medium">
                                {a._totalEur > 0 ? (
                                  <span className="text-red-600">{fmtNum(a._totalEur, 0)} EUR</span>
                                ) : (
                                  '-'
                                )}
                              </td>
                              {isExpert && (
                                <td className="py-3 pr-4 text-[10px] text-gray-400 font-mono">
                                  {a.meter_id || '-'}{a._meters && a._meters.size > 1 ? ` (+${a._meters.size - 1})` : ''}
                                </td>
                              )}
                              {isExpert && (
                                <td className="py-3 pr-4 text-[10px] text-gray-400 font-mono text-right">
                                  {a._totalKwh > 0 ? `${fmtNum(a._totalKwh, 1)} kWh` : a.estimated_impact_kwh > 0 ? `${fmtNum(a.estimated_impact_kwh, 1)} kWh` : '-'}
                                </td>
                              )}
                              <td className="py-3">
                                <div
                                  className="flex items-center gap-1"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => openInsightDrawer(a)}
                                  >
                                    <Eye size={13} /> Preuve
                                  </Button>
                                  {a.status === 'open' && (
                                    <Button
                                      size="sm"
                                      variant="secondary"
                                      onClick={() => handleAck(a.id)}
                                    >
                                      Acquitter
                                    </Button>
                                  )}
                                  {(a.status === 'open' || a.status === 'ack') && (
                                    <Button
                                      size="sm"
                                      variant="primary"
                                      onClick={() => handleResolve(a.id)}
                                    >
                                      Résoudre
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardBody>
            </Card>

            {/* Métriques avancées — expert mode */}
            {isExpert && (
              <details data-section="metriques-avancees" className="mb-6">
                <summary className="cursor-pointer text-sm font-semibold text-gray-600 hover:text-gray-800 flex items-center gap-2 py-2">
                  <ChevronDown size={14} />
                  Métriques avancées
                </summary>
                <div className="mt-3 space-y-4">
                  {/* Snapshots History */}
                  <Card>
                    <CardBody>
                      <h3 className="font-semibold text-gray-700 mb-4">Historique Snapshots</h3>
                      {snapshots.length === 0 ? (
                        <p className="text-sm text-gray-400 text-center py-4">
                          Aucun snapshot disponible.
                        </p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b text-left text-gray-500">
                                <th className="pb-2 pr-4">ID</th>
                                <th className="pb-2 pr-4">Période</th>
                                <th className="pb-2 pr-4">Qualité</th>
                                <th className="pb-2 pr-4">Risque</th>
                                <th className="pb-2">Date</th>
                              </tr>
                            </thead>
                            <tbody>
                              {snapshots.map((s) => (
                                <tr key={s.id} className="border-b hover:bg-gray-50">
                                  <td className="py-2 pr-4">{s.id}</td>
                                  <td className="py-2 pr-4">{s.period}</td>
                                  <td
                                    className={`py-2 pr-4 font-medium ${scoreColor(s.data_quality_score || 0)}`}
                                  >
                                    {s.data_quality_score ?? '-'}
                                  </td>
                                  <td
                                    className={`py-2 pr-4 font-medium ${riskColor(s.risk_power_score || 0)}`}
                                  >
                                    {s.risk_power_score ?? '-'}
                                  </td>
                                  <td className="py-2 text-gray-400">
                                    {s.created_at?.slice(0, 16)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </CardBody>
                  </Card>
                </div>
              </details>
            )}
          </div>
          {/* end data-section="details" */}

          {/* Trust Badge + Demo CTA */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <TrustBadge
                source="Monitoring Engine"
                period={kpis?.period}
                confidence={qualityScore >= 80 ? 'high' : qualityScore >= 50 ? 'medium' : 'low'}
              />
              <Badge status="info">
                Profil: {PROFILE_OPTIONS.find((p) => p.value === demoProfile)?.label || demoProfile}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <select
                className="border rounded-lg px-2 py-1 text-sm"
                value={demoProfile}
                onChange={(e) => setDemoProfile(e.target.value)}
              >
                {PROFILE_OPTIONS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
              <Button variant="ghost" size="sm" onClick={handleDemo} disabled={demoLoading}>
                <PlayCircle size={14} />
                {demoLoading ? 'Génération...' : 'Régénérer Démo'}
              </Button>
            </div>
          </div>
        </>
      )}

      {/* ConfidenceDrawer */}
      <ConfidenceDrawer
        open={showConfidenceDrawer}
        onClose={() => setShowConfidenceDrawer(false)}
        qualityConf={qualityConf}
        qualityScore={qualityScore}
        climate={climate}
      />

      {/* OffHoursDrawer */}
      <OffHoursDrawer
        open={showOffHoursDrawer}
        onClose={() => setShowOffHoursDrawer(false)}
        offHoursRatio={offHoursRatio}
        offHoursKwh={offHoursKwh}
        schedule={schedule}
        emissions={emissions}
        siteId={siteId}
        onCreateAction={(prefill) => {
          setShowOffHoursDrawer(false);
          openActionDrawer(
            {
              prefill,
              siteId: siteId ? Number(siteId) : null,
              sourceType: 'insight',
            },
            {
              onSave: async () => {
                track('monitoring_action_created', { site_id: siteId });
                await loadSiteActions();
              },
            }
          );
        }}
      />

      {/* InsightDrawer */}
      <InsightDrawer
        alert={drawerAlert}
        open={!!drawerAlert}
        onClose={() => setDrawerAlert(null)}
        onAck={handleAck}
        onResolve={handleResolve}
        onCreateAction={handleCreateAction}
        onOpenExplorer={handleOpenExplorer}
      />

      {/* Action creation handled by ActionDrawerContext */}
    </PageShell>
  );
}
