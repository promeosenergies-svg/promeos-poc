/**
 * PROMEOS - MonitoringPage V3 (/monitoring)
 * Performance Electrique — premium dashboard.
 * 5 KPI cards, 4 graphs (signature, heatmap, climate scatter, bar chart),
 * InsightDrawer, CreateActionModal, demo profile selector.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, Zap, BarChart3, CheckCircle, Clock,
  Shield, TrendingUp, ChevronDown, ChevronUp, Eye, PlayCircle,
  Database, RefreshCw, Thermometer, Sun, Info, UserCheck,
  CheckCircle2, XCircle, ExternalLink,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RTooltip, ResponsiveContainer,
  ComposedChart, Area, ScatterChart, Scatter, Line, Legend,
} from 'recharts';
import {
  Card, CardBody, Badge, Button, EmptyState, TrustBadge,
  Skeleton, PageShell, KpiCard, Drawer, Tabs, Tooltip,
} from '../ui';
import { SkeletonCard } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { mockSites } from '../mocks/sites';
import { track } from '../services/tracker';
import CreateActionModal from '../components/CreateActionModal';
import { fmtKwh, fmtDateFR } from '../utils/format';
import {
  getMonitoringKpis,
  runMonitoring,
  getMonitoringSnapshots,
  getMonitoringAlerts,
  ackMonitoringAlert,
  resolveMonitoringAlert,
  generateMonitoringDemo,
  getUsageSuggest,
} from '../services/api';

// --- Constants ---

const SEVERITY_BADGE = {
  critical: 'crit', high: 'warn', warning: 'warn', info: 'info',
};

const STATUS_CONFIG = {
  open: { label: 'Ouvert', badge: 'crit' },
  ack: { label: 'En cours', badge: 'warn' },
  resolved: { label: 'Resolu', badge: 'ok' },
};

const ALERT_TYPE_LABELS = {
  BASE_NUIT_ELEVEE: 'Base nuit elevee',
  WEEKEND_ANORMAL: 'Week-end anormal',
  DERIVE_TALON: 'Derive talon',
  PIC_ANORMAL: 'Pic anormal',
  P95_HAUSSE: 'Hausse P95',
  DEPASSEMENT_PUISSANCE: 'Depassement puissance',
  RUPTURE_PROFIL: 'Rupture de profil',
  HORS_HORAIRES: 'Consommation hors horaires',
  COURBE_PLATE: 'Courbe plate',
  DONNEES_MANQUANTES: 'Donnees manquantes',
  DOUBLONS_DST: 'Doublons DST',
  VALEURS_NEGATIVES: 'Valeurs negatives',
  SENSIBILITE_CLIMATIQUE: 'Sensibilite climatique',
};

const KPI_THRESHOLDS = {
  quality: { ok: 80, warn: 60 },
  risk: { ok: 35, warn: 60 },
  loadFactor: { ok: 85, warn: 50 },
  climate: { ok: 2, warn: 4 },
};

const KPI_TOOLTIPS = {
  pmax: 'Puissance max atteinte (P = E / dt). P95 = 95e centile.',
  loadFactor: 'E_totale / (Pmax x heures). Eleve = courbe plate.',
  risk: 'Risque depassement Psub. 4 facteurs: P95/Psub, frequence, volatilite, pics.',
  quality: 'Qualite donnees: completude, trous, doublons, negatifs, outliers.',
  climate: 'Pente (kWh/j)/°C de la signature energetique. Eleve = forte dependance climatique.',
};

const DAYS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const HOURS_24 = Array.from({ length: 24 }, (_, i) => `${i}h`);

const DRAWER_TABS = [
  { id: 'evidence', label: 'Preuve' },
  { id: 'methode', label: 'Methode' },
  { id: 'actions', label: 'Actions' },
];

const PROFILE_OPTIONS = [
  { value: 'office', label: 'Bureau' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'retail', label: 'Commerce' },
  { value: 'warehouse', label: 'Logistique' },
  { value: 'school', label: 'Ecole' },
  { value: 'hospital', label: 'Hopital' },
];

// --- Exported helpers (testable) ---

export function buildHeatmapGrid(weekdayProfile, weekendProfile) {
  if (!weekdayProfile) return null;
  return Array.from({ length: 7 }, (_, d) =>
    Array.from({ length: 24 }, (_, h) =>
      Number(((d >= 5 ? (weekendProfile || weekdayProfile) : weekdayProfile)[h] || 0).toFixed(1))
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
  if (r2 != null && r2 < 0.3) reasons.push(`R² faible (${r2.toFixed(2)})`);
  if (nPoints != null && nPoints < 30) reasons.push(`${nPoints} jours de donnees`);
  if (coveragePct != null && coveragePct < 60) reasons.push(`Couverture ${coveragePct}%`);
  return { level, pct: score, reason: reasons.join(' · ') || 'Donnees suffisantes' };
}

/**
 * Load factor thresholds by archetype.
 * lower ok = LF below ok is OK (LF is "high=ok" for some, "high=warn" for others).
 * Seuils: if LF >= ok → ok, >= warn → surveiller, else critique.
 */
export const LF_THRESHOLDS_BY_ARCHETYPE = {
  office:    { ok: 40, warn: 25 },
  hotel:     { ok: 55, warn: 35 },
  retail:    { ok: 45, warn: 30 },
  warehouse: { ok: 50, warn: 35 },
  school:    { ok: 35, warn: 20 },
  hospital:  { ok: 60, warn: 40 },
  default:   { ok: 35, warn: 20 },
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
  a_confirmer: { label: 'A confirmer', badge: 'info' },
  no_data: { label: 'Pas de donnees', badge: 'neutral' },
};

const CONFIDENCE_DOT = {
  high: 'bg-green-500',
  medium: 'bg-yellow-500',
  low: 'bg-red-400',
};

function StatusKpiCard({ icon, title, value, sub, tooltip, status, color, onClick, confidence }) {
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
            <span className={`w-1.5 h-1.5 rounded-full ${CONFIDENCE_DOT[confidence.level] || CONFIDENCE_DOT.low}`} />
            Confiance: {confidence.level === 'high' ? 'Forte' : confidence.level === 'medium' ? 'Moyenne' : 'Faible'}
          </div>
        )}
      </div>
    </Tooltip>
  );
}

/**
 * Executive summary: top risk, top waste, data confidence — each with CTA.
 */
function ExecutiveSummary({ alerts, kpiData, climate, qualityScore, qualityConf, onOpenExplorer, onCreateAction }) {
  // Top risk: highest EUR impact open alert
  const topAlert = alerts
    .filter((a) => a.status === 'open' && a.estimated_impact_eur)
    .sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0))[0];

  // Top waste: off-hours or high base load
  const wasteAlerts = alerts.filter((a) =>
    ['HORS_HORAIRES', 'BASE_NUIT_ELEVEE', 'WEEKEND_ANORMAL'].includes(a.alert_type) && a.status !== 'resolved'
  );
  const totalWasteEur = wasteAlerts.reduce((s, a) => s + (a.estimated_impact_eur || 0), 0);

  // Data confidence
  const confLabel = qualityConf?.level === 'high' ? 'Forte' : qualityConf?.level === 'medium' ? 'Moyenne' : 'Faible';
  const confColor = qualityConf?.level === 'high' ? 'text-green-600' : qualityConf?.level === 'medium' ? 'text-yellow-600' : 'text-red-500';

  const cards = [
    {
      icon: AlertTriangle,
      iconColor: topAlert ? 'text-red-500' : 'text-gray-300',
      title: 'Risque principal',
      value: topAlert
        ? `${fmtNum(topAlert.estimated_impact_eur, 0)} EUR/an`
        : 'Aucun risque detecte',
      sub: topAlert
        ? ALERT_TYPE_LABELS[topAlert.alert_type] || topAlert.alert_type
        : 'Continuez le suivi',
      cta: topAlert ? { label: 'Voir preuve', action: () => onCreateAction(topAlert) } : null,
    },
    {
      icon: Zap,
      iconColor: totalWasteEur > 0 ? 'text-orange-500' : 'text-gray-300',
      title: 'Gaspillage estime',
      value: totalWasteEur > 0 ? `${fmtNum(totalWasteEur, 0)} EUR/an` : 'Non detecte',
      sub: wasteAlerts.length > 0
        ? `${wasteAlerts.length} alerte${wasteAlerts.length > 1 ? 's' : ''} (hors horaires, WE, talon)`
        : 'Aucune anomalie de gaspillage',
      cta: totalWasteEur > 0 ? { label: 'Explorer', action: onOpenExplorer } : null,
    },
    {
      icon: Database,
      iconColor: confColor,
      title: 'Confiance donnees',
      value: `${qualityScore ?? '-'}/100`,
      sub: `${confLabel}${qualityConf?.reason ? ' — ' + qualityConf.reason : ''}`,
      cta: null,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
      {cards.map((c, i) => (
        <Card key={i}>
          <CardBody className="p-4">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-gray-50 ${c.iconColor}`}>
                <c.icon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{c.title}</p>
                <p className="text-lg font-bold text-gray-800 mt-0.5">{c.value}</p>
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{c.sub}</p>
                {c.cta && (
                  <button
                    onClick={c.cta.action}
                    className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800 transition flex items-center gap-1"
                  >
                    {c.cta.label} <ExternalLink size={10} />
                  </button>
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
 * Quick actions bar: Explorer, Create Action, Compare (stub)
 */
function QuickActionsBar({ onOpenExplorer, onCreateAction, onCompare, compareEnabled }) {
  return (
    <div className="flex items-center gap-2 mb-6 flex-wrap">
      <Button variant="secondary" size="sm" onClick={onOpenExplorer}>
        <BarChart3 size={14} />
        Ouvrir dans Explorer
      </Button>
      <Button variant="primary" size="sm" onClick={onCreateAction}>
        <Zap size={14} />
        Creer une action
      </Button>
      {compareEnabled && (
        <Button variant="ghost" size="sm" onClick={onCompare}>
          <Clock size={14} />
          Comparer periode precedente
        </Button>
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
        <p className="text-sm text-gray-400">Lancez une analyse pour generer le profil jour-type.</p>
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
        <Area type="monotone" dataKey="semaine" stroke="#3b82f6" fill="#bfdbfe" fillOpacity={0.5} name="Semaine" />
        <Area type="monotone" dataKey="weekend" stroke="#f59e0b" fill="#fde68a" fillOpacity={0.4} name="Weekend" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function HeatmapGrid({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8">
        <Sun size={24} className="mx-auto text-gray-200 mb-2" />
        <p className="text-xs text-gray-400">Pas de donnees heatmap. Lancez une analyse.</p>
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
          <div key={h} className="text-center text-gray-400 py-0.5">{h}</div>
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
        {['bg-green-200', 'bg-yellow-300', 'bg-amber-400', 'bg-orange-400', 'bg-red-500'].map((c) => (
          <div key={c} className={`w-3 h-3 rounded-sm ${c}`} />
        ))}
        <span>Haut</span>
      </div>
    </div>
  );
}

export const CLIMATE_REASONS = {
  no_meter: 'Aucun compteur associe au snapshot. Relancez l\'analyse.',
  no_weather: 'Donnees meteo indisponibles pour la periode.',
  meter_not_found: 'Compteur introuvable.',
  insufficient_readings: 'Moins de 10 jours de donnees — insuffisant pour la regression.',
  computation_error: 'Erreur de calcul. Verifiez les donnees sources.',
};

export const CLIMATE_LABEL_FR = {
  heating_dominant: 'Chauffage majoritaire',
  cooling_dominant: 'Climatisation majoritaire',
  mixed: 'Mixte (chauffage + clim.)',
  flat: 'Insensible au climat',
  unknown: 'Non determine',
};

// --- Usage Panel helpers ---

export const USAGE_DAYS_FR = { 0: 'Lun', 1: 'Mar', 2: 'Mer', 3: 'Jeu', 4: 'Ven', 5: 'Sam', 6: 'Dim' };

export function formatSchedule(sched) {
  if (!sched) return '-';
  if (sched.is_24_7) return '24/7';
  const days = (sched.open_days || '').split(',').map((d) => USAGE_DAYS_FR[d.trim()]).filter(Boolean);
  const daysStr = days.length === 7 ? 'Tous les jours' : days.length === 5 && !days.includes('Sam') ? 'Lun-Ven' : days.join(', ');
  return `${daysStr} ${sched.open_time}-${sched.close_time}`;
}

const CONFIDENCE_LABEL_FR = { high: 'Forte', medium: 'Moyenne', low: 'Faible' };
const SOURCE_LABEL_FR = { naf: 'NAF', type_fallback: 'Type site', default: 'Defaut' };

function UsagePanel({ usage, loading: usageLoading }) {
  if (usageLoading) return (
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
                <span className="text-[10px] text-gray-400">NAF: {usage.reasons?.[0]?.split('→')[0]?.replace('NAF ', '').trim()}</span>
              )}
            </div>
            <div className="text-sm text-gray-600">
              {current ? (
                <span>{schedText} · Source: horaires site</span>
              ) : (
                <span className="text-yellow-600">Horaires suggeres: {suggestText}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
              <span>Confiance: {CONFIDENCE_LABEL_FR[usage.confidence] || usage.confidence}</span>
              <span>Source: {SOURCE_LABEL_FR[usage.archetype_source] || usage.archetype_source}</span>
              {usage.has_vacation && <span className="text-blue-500">Vacances actives</span>}
            </div>
          </div>
          <div className="shrink-0">
            {current ? (
              <Button variant="ghost" size="sm" onClick={() => {}}>
                Modifier
              </Button>
            ) : (
              <Button variant="secondary" size="sm" onClick={() => {}}>
                Appliquer
              </Button>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

const OFF_HOURS_TABS = [
  { id: 'methode', label: 'Methode' },
  { id: 'hypotheses', label: 'Hypotheses' },
  { id: 'actions', label: 'Actions' },
];

function OffHoursDrawer({ open, onClose, offHoursRatio, offHoursKwh, schedule, onCreateAction }) {
  const [tab, setTab] = useState('methode');
  const estimate = computeOffHoursEstimate(offHoursKwh);

  return (
    <Drawer open={open} onClose={onClose} title="Hors Horaires — Detail" wide>
      <div className="space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          {offHoursRatio != null && <Badge status={offHoursRatio <= 0.20 ? 'ok' : offHoursRatio <= 0.40 ? 'warn' : 'crit'}>{fmtNum(offHoursRatio * 100)}%</Badge>}
          {offHoursKwh > 0 && <span className="text-sm text-orange-600 font-medium">{fmtNum(offHoursKwh, 0)} kWh (90j)</span>}
          {estimate.eur > 0 && <span className="text-sm text-red-600 font-medium">{estimate.label}</span>}
        </div>

        <Tabs tabs={OFF_HOURS_TABS} active={tab} onChange={setTab} />

        {tab === 'methode' && (
          <div className="space-y-3">
            <DrawerSection title="Definition">
              <p className="text-sm text-gray-600">Energie consommee en dehors des heures d'exploitation definies dans le planning du site.</p>
              <DrawerRow label="Ratio">{offHoursRatio != null ? `${fmtNum(offHoursRatio * 100)}%` : '-'}</DrawerRow>
              <DrawerRow label="kWh (90 jours)">{offHoursKwh != null ? fmtNum(offHoursKwh, 0) : '-'}</DrawerRow>
            </DrawerSection>
            <DrawerSection title="Horaires actuels">
              {schedule ? (
                <>
                  <DrawerRow label="Jours">{schedule.open_days || '-'}</DrawerRow>
                  <DrawerRow label="Heures">{schedule.is_24_7 ? '24/7' : `${schedule.open_time}-${schedule.close_time}`}</DrawerRow>
                </>
              ) : (
                <p className="text-sm text-gray-400">Horaires non definis — le ratio est base sur un profil par defaut.</p>
              )}
            </DrawerSection>
            <DrawerSection title="Extrapolation">
              <DrawerRow label="Periode mesuree">90 jours</DrawerRow>
              <DrawerRow label="Facteur annuel">x {(365 / 90).toFixed(2)}</DrawerRow>
              <DrawerRow label="kWh annuel estime">{offHoursKwh > 0 ? fmtNum(offHoursKwh * (365 / 90), 0) : '-'}</DrawerRow>
            </DrawerSection>
          </div>
        )}

        {tab === 'hypotheses' && (
          <div className="space-y-3">
            <DrawerSection title="Prix de reference">
              <DrawerRow label="Prix kWh">{estimate.price} EUR/kWh</DrawerRow>
              <DrawerRow label="Source">Tarif moyen tertiaire France (estimation)</DrawerRow>
            </DrawerSection>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
              Les montants affiches sont des estimations. Renseignez vos tarifs reels pour un chiffrage precis.
            </div>
          </div>
        )}

        {tab === 'actions' && (
          <div className="space-y-3">
            <DrawerSection title="Action recommandee">
              <p className="text-sm text-gray-600">Reduire la consommation hors horaires d'exploitation par ajustement des equipements CVC, eclairage, et veilles.</p>
            </DrawerSection>
            {estimate.eur > 0 && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onCreateAction({
                  titre: `Reduction conso hors horaires — Site`,
                  type: 'conso',
                  impact_eur: estimate.eur,
                  description: `Off-hours ${offHoursRatio != null ? fmtNum(offHoursRatio * 100) : '?'}% — ${fmtNum(offHoursKwh, 0)} kWh sur 90j. Estimation: ${estimate.label}.`,
                })}
              >
                <Zap size={14} />
                Creer action ({estimate.label})
              </Button>
            )}
          </div>
        )}
      </div>
    </Drawer>
  );
}

function ClimateScatter({ climate }) {
  if (!climate || !climate.scatter || climate.scatter.length === 0) {
    const reason = climate?.reason;
    const msg = reason ? CLIMATE_REASONS[reason] || reason : 'Pas de donnees climatiques.';
    return (
      <div className="text-center py-12">
        <Thermometer size={28} className="mx-auto text-gray-200 mb-2" />
        <p className="text-sm text-gray-400">{msg}</p>
        {reason && <p className="text-xs text-gray-300 mt-1">code: {reason}</p>}
      </div>
    );
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={250}>
        <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="T" name="Temperature (°C)" unit=" °C" tick={{ fontSize: 11 }} type="number" />
          <YAxis dataKey="kwh" name="Conso. journaliere" unit=" kWh/j" tick={{ fontSize: 11 }} type="number" />
          <RTooltip cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={climate.scatter} fill="#3b82f6" fillOpacity={0.6} r={3} name="Jours" />
          {climate.fit_line && climate.fit_line.length > 0 && (
            <Scatter data={climate.fit_line} fill="none" line={{ stroke: '#ef4444', strokeWidth: 2 }} shape={() => null} name="Regression" />
          )}
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        {climate.slope_kw_per_c != null && <span>Pente: {climate.slope_kw_per_c.toFixed(1)} (kWh/j)/°C</span>}
        {climate.balance_point_c != null && <span>Tb: {climate.balance_point_c.toFixed(1)} °C</span>}
        {climate.r_squared != null && <span>R²: {climate.r_squared.toFixed(2)}</span>}
        {climate.label && <span>{CLIMATE_LABEL_FR[climate.label] || climate.label}</span>}
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
          <Badge status={SEVERITY_BADGE[alert.severity] || 'neutral'}>{alert.severity}</Badge>
          {alert.estimated_impact_kwh > 0 && (
            <span className="text-xs text-orange-600 font-medium">{alert.estimated_impact_kwh} kWh</span>
          )}
          {alert.estimated_impact_eur > 0 && (
            <span className="text-xs text-red-600 font-medium">{alert.estimated_impact_eur} EUR</span>
          )}
        </div>

        <p className="text-sm text-gray-700">{alert.explanation}</p>
        {alert.recommended_action && (
          <p className="text-sm text-blue-700 bg-blue-50 rounded-lg p-2">{alert.recommended_action}</p>
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
              <p className="text-sm text-gray-400 text-center py-4">Pas de preuve detaillee.</p>
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
            <DrawerSection title="Methode de detection">
              <DrawerRow label="Type">{alert.alert_type}</DrawerRow>
              <DrawerRow label="Severite">{alert.severity}</DrawerRow>
              <DrawerRow label="Moteur">Moteur Monitoring v1.0</DrawerRow>
            </DrawerSection>
            <DrawerSection title="Seuils">
              <DrawerRow label="Seuil declenchement">Calcule par le moteur d'alertes</DrawerRow>
              <DrawerRow label="Confiance">{alert.severity === 'critical' ? 'Haute' : 'Moyenne'}</DrawerRow>
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
              <p className="text-sm text-gray-400 text-center py-6">Aucune action recommandee.</p>
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
            Creer une action
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
                <CheckCircle2 size={14} /> Resolu
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
  const { scope, scopedSites, setSite } = useScope();
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

  // Drawer state
  const [drawerAlert, setDrawerAlert] = useState(null);
  const [showOffHoursDrawer, setShowOffHoursDrawer] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [actionPrefill, setActionPrefill] = useState(null);

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
      setAlerts(alertRes.status === 'fulfilled' ? (alertRes.value || []) : []);
      setSnapshots(snapRes.status === 'fulfilled' ? (snapRes.value || []) : []);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }, [siteId]);

  useEffect(() => {
    if (siteId) {
      loadAll();
      track('monitoring_view', { site_id: siteId });
      // Fetch usage suggestion
      setUsageLoading(true);
      getUsageSuggest(siteId)
        .then(setUsageSuggest)
        .catch(() => setUsageSuggest(null))
        .finally(() => setUsageLoading(false));
    }
  }, [siteId, loadAll]);

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
      setAlerts((prev) => prev.map((a) =>
        a.id === id ? { ...a, status: 'ack' } : a
      ));
      if (drawerAlert?.id === id) setDrawerAlert((d) => ({ ...d, status: 'ack' }));
    } catch { toast('Erreur lors de l\'acquittement', 'error'); }
  };

  const handleResolve = async (id) => {
    try {
      await resolveMonitoringAlert(id, 'Resolu depuis UI');
      track('monitoring_resolve', { alert_id: id });
      setAlerts((prev) => prev.map((a) =>
        a.id === id ? { ...a, status: 'resolved' } : a
      ));
      if (drawerAlert?.id === id) setDrawerAlert((d) => ({ ...d, status: 'resolved' }));
    } catch { toast('Erreur lors de la resolution', 'error'); }
  };

  const openInsightDrawer = (alert) => {
    setDrawerAlert(alert);
    track('monitoring_drawer_open', { alert_type: alert.alert_type });
  };

  const handleCreateAction = (alert) => {
    setActionPrefill({
      titre: `${ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type} — Site ${siteId}`,
      type: 'conso',
      impact_eur: alert.estimated_impact_eur || '',
      description: alert.explanation || '',
    });
    setShowActionModal(true);
  };

  const handleSaveAction = () => {
    toast('Action creee avec succes', 'success');
    setShowActionModal(false);
    track('monitoring_action_created', { site_id: siteId });
  };

  const handleOpenExplorer = (alert) => {
    const params = new URLSearchParams({ site_id: siteId });
    if (kpis?.period) {
      const parts = kpis.period.split(' - ');
      if (parts[0]) params.set('date_from', parts[0]);
      if (parts[1]) params.set('date_to', parts[1]);
    }
    navigate(`/explorer?${params.toString()}`);
  };

  // --- Derived data ---

  const kpiData = kpis?.kpis || {};
  const qualityScore = kpis?.data_quality_score ?? null;
  const riskScore = kpis?.risk_power_score ?? null;
  const schedule = kpis?.schedule || null;
  const offHoursRatio = kpiData.off_hours_ratio ?? null;
  const offHoursKwh = kpiData.off_hours_kwh ?? null;
  const offHoursEstimate = useMemo(() => computeOffHoursEstimate(offHoursKwh), [offHoursKwh]);

  const weekdayProfile = kpiData.weekday_profile_kw;
  const weekendProfile = kpiData.weekend_profile_kw;

  const weekdayBarData = useMemo(() => {
    if (!weekdayProfile || !Array.isArray(weekdayProfile)) return null;
    return weekdayProfile.map((kw, hour) => ({
      hour: `${hour}h`,
      kw: Number(kw.toFixed(1)),
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

  const allOrgSites = useMemo(() => mockSites, []);

  // Confidence
  const climateConf = useMemo(() => computeConfidence({
    r2: climate?.r_squared,
    nPoints: climate?.n_points,
    reason: climate?.reason,
  }), [climate]);

  const qualityConf = useMemo(() => computeConfidence({
    coveragePct: kpis?.data_quality_details?.completeness_pct,
  }), [kpis]);

  // Load factor: archetype-aware thresholds
  const archetype = demoProfile || 'default';
  const archetypeLabel = PROFILE_OPTIONS.find((p) => p.value === archetype)?.label || 'Tertiaire (defaut)';
  const isDefaultArchetype = !demoProfile || !LF_THRESHOLDS_BY_ARCHETYPE[demoProfile];
  const lfThresholds = useMemo(() => {
    return LF_THRESHOLDS_BY_ARCHETYPE[archetype] || LF_THRESHOLDS_BY_ARCHETYPE.default;
  }, [archetype]);

  // KPI statuses (all confidence-aware)
  const qualityStatus = kpiStatusWithConfidence(qualityScore, KPI_THRESHOLDS.quality, false, qualityConf);
  const riskStatus = kpiStatusWithConfidence(riskScore, KPI_THRESHOLDS.risk, true, qualityConf);
  const lfStatus = kpiStatusWithConfidence(
    kpiData.load_factor != null ? kpiData.load_factor * 100 : null,
    lfThresholds, false, qualityConf
  );
  const climateStatus = kpiStatusWithConfidence(
    climate?.slope_kw_per_c, KPI_THRESHOLDS.climate, true, climateConf
  );

  // --- No site selected ---

  if (!siteId) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Electrique"
        subtitle="KPIs, puissance, qualite de donnees & alertes"
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
          title="Selectionnez un site"
          text="Choisissez un site dans le selecteur ci-dessus pour voir les KPIs de performance electrique."
        />
      </PageShell>
    );
  }

  // --- Loading skeleton ---

  if (loading && !kpis && alerts.length === 0) {
    return (
      <PageShell
        icon={Activity}
        title="Performance Electrique"
        subtitle="KPIs, puissance, qualite de donnees & alertes"
      >
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          {[1, 2, 3, 4, 5].map((i) => <SkeletonCard key={i} />)}
        </div>
        <Skeleton rows={6} />
      </PageShell>
    );
  }

  const hasData = kpis || alerts.length > 0 || snapshots.length > 0;

  return (
    <PageShell
      icon={Activity}
      title="Performance Electrique"
      subtitle="KPIs, puissance, qualite de donnees & alertes"
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
          <Button variant="secondary" size="sm" onClick={handleRun} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Analyse...' : 'Lancer Analyse'}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => {
            const params = new URLSearchParams({ site_id: siteId });
            if (kpis?.period) {
              const parts = kpis.period.split(' - ');
              if (parts[0]) params.set('date_from', parts[0]);
              if (parts[1]) params.set('date_to', parts[1]);
            }
            navigate(`/explorer?${params.toString()}`);
          }}>
            <BarChart3 size={14} />
            Explorer
          </Button>
          <Button variant="ghost" size="sm" onClick={() => navigate('/diagnostic-conso')}>
            <Eye size={14} />
            Diagnostics
          </Button>
        </>
      }
    >

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-red-700 text-sm">{error}</div>
      )}

      {/* Empty state with demo CTA */}
      {!hasData && (
        <div>
          <EmptyState
            icon={Database}
            title="Aucune donnee de monitoring"
            text="Generez des donnees de demo pour explorer les KPIs de performance electrique, les profils jour-type et les alertes automatiques."
            ctaLabel={demoLoading ? 'Generation...' : 'Generer Donnees Demo'}
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
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {hasData && (
        <>
          {/* Usage Panel */}
          <UsagePanel usage={usageSuggest} loading={usageLoading} />

          {/* Executive Summary */}
          <ExecutiveSummary
            alerts={alerts}
            kpiData={kpiData}
            climate={climate}
            qualityScore={qualityScore}
            qualityConf={qualityConf}
            onOpenExplorer={() => handleOpenExplorer(null)}
            onCreateAction={(a) => {
              if (a) handleCreateAction(a);
              else {
                setActionPrefill({ titre: `Action — Site ${siteId}`, type: 'conso' });
                setShowActionModal(true);
              }
            }}
          />

          {/* Quick Actions Bar */}
          <QuickActionsBar
            onOpenExplorer={() => handleOpenExplorer(null)}
            onCreateAction={() => {
              setActionPrefill({ titre: `Action — Site ${siteId}`, type: 'conso' });
              setShowActionModal(true);
            }}
            compareEnabled={!!kpis?.period}
            onCompare={() => {
              const params = new URLSearchParams({ site_id: siteId, compare: '30d' });
              if (kpis?.period) {
                const parts = kpis.period.split(' - ');
                if (parts[0]) params.set('date_from', parts[0]);
                if (parts[1]) params.set('date_to', parts[1]);
              }
              navigate(`/explorer?${params.toString()}`);
            }}
          />

          {/* KPI Strip — 6 cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <StatusKpiCard
              icon={Zap}
              title="Pmax / P95"
              value={kpiData.pmax_kw != null ? `${fmtNum(kpiData.pmax_kw)} kW` : '-'}
              sub={`P95: ${fmtNum(kpiData.p95_kw)} kW`}
              tooltip={KPI_TOOLTIPS.pmax}
              status="ok"
              color="bg-yellow-500"
            />
            <StatusKpiCard
              icon={TrendingUp}
              title="Talon / Base"
              value={kpiData.pbase_kw != null ? `${fmtNum(kpiData.pbase_kw)} kW` : '-'}
              sub={`Nuit: ${fmtNum(kpiData.pbase_night_kw)} kW | WE: ${kpiData.weekend_ratio != null ? fmtNum(kpiData.weekend_ratio * 100) + '%' : '-'}`}
              tooltip="Talon = consommation mini hors periodes d'activite. Ratio WE = part weekend."
              status="ok"
              color="bg-blue-500"
            />
            <StatusKpiCard
              icon={Activity}
              title="Facteur de charge"
              value={kpiData.load_factor != null ? `${fmtNum(kpiData.load_factor * 100)}%` : '-'}
              sub={`Pic/Moy: ${fmtNum(kpiData.peak_to_average)}x · ${archetypeLabel}`}
              tooltip={`${KPI_TOOLTIPS.loadFactor}\nProfil: ${archetypeLabel} (OK >= ${lfThresholds.ok}%, Attention >= ${lfThresholds.warn}%)${isDefaultArchetype ? '\n⚠ Profil par defaut — choisissez un profil pour des seuils adaptes.' : ''}`}
              status={lfStatus}
              color="bg-indigo-500"
            />
            <StatusKpiCard
              icon={Shield}
              title="Risque Puissance"
              value={riskScore != null ? `${riskScore}/100` : '-'}
              sub={riskScore != null ? (riskScore < 35 ? 'Marge confortable' : riskScore < 60 ? 'A surveiller' : 'Depassement probable') : ''}
              tooltip={KPI_TOOLTIPS.risk}
              status={riskStatus}
              color={riskScore >= 60 ? 'bg-red-500' : riskScore >= 35 ? 'bg-orange-500' : 'bg-green-500'}
              confidence={qualityConf}
            />
            <StatusKpiCard
              icon={CheckCircle}
              title="Qualite Donnees"
              value={qualityScore != null ? `${qualityScore}/100` : '-'}
              sub={qualityScore != null ? (qualityScore >= 80 ? 'Excellente' : qualityScore >= 60 ? 'Correcte' : 'Degradee') : ''}
              tooltip={KPI_TOOLTIPS.quality}
              status={qualityStatus}
              color={qualityScore >= 80 ? 'bg-green-500' : qualityScore >= 60 ? 'bg-yellow-500' : 'bg-red-500'}
              confidence={qualityConf}
            />
            <StatusKpiCard
              icon={Clock}
              title="Hors Horaires"
              value={offHoursRatio != null ? `${fmtNum(offHoursRatio * 100)}%` : '-'}
              sub={schedule
                ? (schedule.is_24_7
                  ? '24/7 — pas de hors horaires'
                  : `${schedule.open_time}-${schedule.close_time}${offHoursEstimate.eur > 0 ? ` · ${offHoursEstimate.label}` : ''}`)
                : `Horaires non definis${offHoursEstimate.eur > 0 ? ` · ${offHoursEstimate.label}` : ''}`}
              tooltip={`Part d'energie consommee en dehors des heures d'exploitation. Un ratio eleve signale un talon ou des equipements actifs la nuit/week-end.\nHypothese: ${offHoursEstimate.price} EUR/kWh (tarif moyen)`}
              status={offHoursRatio != null ? (offHoursRatio <= 0.20 ? 'ok' : offHoursRatio <= 0.40 ? 'surveiller' : 'critique') : 'no_data'}
              color={offHoursRatio != null ? (offHoursRatio <= 0.20 ? 'bg-green-500' : offHoursRatio <= 0.40 ? 'bg-orange-500' : 'bg-red-500') : 'bg-slate-400'}
              confidence={qualityConf}
              onClick={() => setShowOffHoursDrawer(true)}
            />
          </div>

          {/* Climate KPI card — always visible, with reason code if no data */}
          {climate && (
            <div className="mb-6">
              <StatusKpiCard
                icon={Thermometer}
                title="Sensibilite Climatique"
                value={climate.slope_kw_per_c != null ? `${climate.slope_kw_per_c.toFixed(1)} (kWh/j)/°C` : '-'}
                sub={climate.slope_kw_per_c != null
                  ? `R²: ${climate.r_squared != null ? climate.r_squared.toFixed(2) : '-'} | ${CLIMATE_LABEL_FR[climate.label] || climate.label || 'Non determine'}`
                  : (CLIMATE_REASONS[climate.reason] || 'Analyse climatique non disponible')}
                tooltip={KPI_TOOLTIPS.climate}
                status={climateStatus}
                color={climate.slope_kw_per_c != null ? 'bg-cyan-500' : 'bg-slate-400'}
                confidence={climateConf}
              />
            </div>
          )}

          {/* Graphs — 2x2 grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Signature jour-type: Semaine vs Weekend */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Clock size={18} /> Signature Jour-Type
                  <span className="text-[10px] text-gray-400 font-normal ml-auto">Puissance moyenne (kW)</span>
                </h2>
                <WeekdayWeekendChart weekdayProfile={weekdayProfile} weekendProfile={weekendProfile} />
              </CardBody>
            </Card>

            {/* Heatmap 7x24 */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Sun size={18} /> Heatmap 7j x 24h
                  <span className="text-[10px] text-gray-400 font-normal ml-auto">kW moyen / creneau</span>
                </h2>
                <HeatmapGrid data={heatmapData} />
              </CardBody>
            </Card>

            {/* Conso. vs Temperature */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Thermometer size={18} /> Conso. vs Temperature
                  <span className="text-[10px] text-gray-400 font-normal ml-auto">kWh/jour vs °C</span>
                </h2>
                <ClimateScatter climate={climate} />
              </CardBody>
            </Card>

            {/* Courbe de charge BarChart */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <BarChart3 size={18} /> Courbe de Charge (Semaine)
                  <span className="text-[10px] text-gray-400 font-normal ml-auto">kW moyen / heure</span>
                </h2>
                {weekdayBarData ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={weekdayBarData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
                      <YAxis tick={{ fontSize: 11 }} unit=" kW" />
                      <RTooltip formatter={(v) => [`${v} kW`, 'Puissance']} />
                      <Bar dataKey="kw" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Puissance" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-12">
                    <BarChart3 size={32} className="mx-auto text-gray-200 mb-2" />
                    <p className="text-sm text-gray-400">Lancez une analyse pour generer la courbe de charge.</p>
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
                  {openCount > 0 && (
                    <Badge status="crit">{openCount} ouvertes</Badge>
                  )}
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
                    { key: 'resolved', label: 'Resolus' },
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
                      {tab.key !== 'all' && ` (${alerts.filter((a) => a.status === tab.key).length})`}
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
                      ? 'Aucune alerte. Lancez une analyse pour detecter les anomalies.'
                      : 'Aucune alerte pour ce filtre.'}
                  </p>
                  {alerts.length === 0 && (
                    <button onClick={handleRun} className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800">
                      Lancer analyse
                    </button>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-500">
                        <th className="pb-2 pr-4">Statut</th>
                        <th className="pb-2 pr-4">Type</th>
                        <th className="pb-2 pr-4">Severite</th>
                        <th className="pb-2 pr-4">Explication</th>
                        <th className="pb-2 pr-4 text-right">Impact (EUR)</th>
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
                              <Badge status={SEVERITY_BADGE[a._maxSeverity || a.severity] || 'neutral'}>
                                {a._maxSeverity || a.severity}
                              </Badge>
                            </td>
                            <td className="py-3 pr-4 text-gray-600 max-w-xs lg:max-w-md">
                              <span className="line-clamp-2">{a.explanation}</span>
                            </td>
                            <td className="py-3 pr-4 text-right font-medium">
                              {a._totalEur > 0 ? (
                                <span className="text-red-600">{fmtNum(a._totalEur, 0)} EUR</span>
                              ) : '-'}
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                <Button size="sm" variant="ghost" onClick={() => openInsightDrawer(a)}>
                                  <Eye size={13} /> Preuve
                                </Button>
                                {a.status === 'open' && (
                                  <Button size="sm" variant="secondary" onClick={() => handleAck(a.id)}>Acquitter</Button>
                                )}
                                {(a.status === 'open' || a.status === 'ack') && (
                                  <Button size="sm" variant="primary" onClick={() => handleResolve(a.id)}>Resoudre</Button>
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

          {/* Snapshots History */}
          <Card className="mb-6">
            <CardBody>
              <h2 className="font-semibold text-gray-700 mb-4">Historique Snapshots</h2>
              {snapshots.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">Aucun snapshot disponible.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-500">
                        <th className="pb-2 pr-4">ID</th>
                        <th className="pb-2 pr-4">Periode</th>
                        <th className="pb-2 pr-4">Qualite</th>
                        <th className="pb-2 pr-4">Risque</th>
                        <th className="pb-2">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshots.map((s) => (
                        <tr key={s.id} className="border-b hover:bg-gray-50">
                          <td className="py-2 pr-4">{s.id}</td>
                          <td className="py-2 pr-4">{s.period}</td>
                          <td className={`py-2 pr-4 font-medium ${scoreColor(s.data_quality_score || 0)}`}>
                            {s.data_quality_score ?? '-'}
                          </td>
                          <td className={`py-2 pr-4 font-medium ${riskColor(s.risk_power_score || 0)}`}>
                            {s.risk_power_score ?? '-'}
                          </td>
                          <td className="py-2 text-gray-400">{s.created_at?.slice(0, 16)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardBody>
          </Card>

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
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              <Button variant="ghost" size="sm" onClick={handleDemo} disabled={demoLoading}>
                <PlayCircle size={14} />
                {demoLoading ? 'Generation...' : 'Regenerer Demo'}
              </Button>
            </div>
          </div>
        </>
      )}

      {/* OffHoursDrawer */}
      <OffHoursDrawer
        open={showOffHoursDrawer}
        onClose={() => setShowOffHoursDrawer(false)}
        offHoursRatio={offHoursRatio}
        offHoursKwh={offHoursKwh}
        schedule={schedule}
        onCreateAction={(prefill) => {
          setShowOffHoursDrawer(false);
          setActionPrefill(prefill);
          setShowActionModal(true);
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

      {/* CreateActionModal */}
      <CreateActionModal
        open={showActionModal}
        onClose={() => setShowActionModal(false)}
        onSave={handleSaveAction}
        prefill={actionPrefill}
      />
    </PageShell>
  );
}
