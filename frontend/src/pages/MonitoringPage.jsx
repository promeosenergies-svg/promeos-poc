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
  climate: 'Pente kW/degC de la signature energetique.',
};

const DAYS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const HOURS_24 = Array.from({ length: 24 }, (_, i) => `${i}h`);

const DRAWER_TABS = [
  { id: 'evidence', label: 'Evidence' },
  { id: 'methode', label: 'Methode' },
  { id: 'actions', label: 'Actions' },
];

const PROFILE_OPTIONS = [
  { value: 'office', label: 'Bureau' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'retail', label: 'Commerce' },
  { value: 'warehouse', label: 'Logistique' },
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
  if (value == null) return 'ok';
  if (invert) {
    if (value <= thresholds.ok) return 'ok';
    if (value <= thresholds.warn) return 'surveiller';
    return 'critique';
  }
  if (value >= thresholds.ok) return 'ok';
  if (value >= thresholds.warn) return 'surveiller';
  return 'critique';
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
  return typeof v === 'number' ? v.toFixed(digits) : String(v);
}

// --- Sub-components ---

const STATUS_BADGES = {
  ok: { label: 'OK', badge: 'ok' },
  surveiller: { label: 'Surveiller', badge: 'warn' },
  critique: { label: 'Critique', badge: 'crit' },
};

function StatusKpiCard({ icon, title, value, sub, tooltip, status, color, onClick }) {
  const st = STATUS_BADGES[status] || STATUS_BADGES.ok;
  return (
    <Tooltip text={tooltip} position="bottom">
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
    </Tooltip>
  );
}

function ResumeBanner({ alerts, kpiData, climate }) {
  const items = [];

  // Top alert by EUR impact
  const topAlert = alerts
    .filter((a) => a.status === 'open' && a.estimated_impact_eur)
    .sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0))[0];
  if (topAlert) {
    items.push({
      icon: AlertTriangle,
      color: 'text-red-600',
      text: `${ALERT_TYPE_LABELS[topAlert.alert_type] || topAlert.alert_type}: ${topAlert.estimated_impact_eur} EUR/an potentiels`,
    });
  }

  // Load factor insight
  const lf = kpiData?.load_factor;
  if (lf != null) {
    const lfPct = Math.round(lf * 100);
    if (lfPct > 85) {
      items.push({ icon: TrendingUp, color: 'text-green-600', text: `Load factor ${lfPct}% — courbe tres plate, verifier compteur.` });
    } else if (lfPct < 30) {
      items.push({ icon: TrendingUp, color: 'text-orange-600', text: `Load factor ${lfPct}% — forte variabilite, potentiel d'effacement.` });
    }
  }

  // Climate slope insight
  const slope = climate?.slope_kw_per_c;
  if (slope != null && slope > 2) {
    items.push({
      icon: Thermometer,
      color: 'text-blue-600',
      text: `Sensibilite climatique: ${slope.toFixed(1)} kW/degC — isolation ou regulation a verifier.`,
    });
  }

  if (items.length === 0) return null;

  return (
    <Card className="mb-4">
      <CardBody>
        <div className="flex flex-col gap-2">
          {items.slice(0, 3).map((item, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <item.icon size={14} className={item.color} />
              <span className="text-gray-700">{item.text}</span>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
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
    return <p className="text-sm text-gray-400 text-center py-12">Lancez une analyse pour generer le profil.</p>;
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
    return <p className="text-xs text-gray-400 text-center py-8">Pas de donnees heatmap</p>;
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

function ClimateScatter({ climate }) {
  if (!climate || !climate.scatter || climate.scatter.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-12">Pas de donnees climatiques.</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={250}>
        <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="T" name="Temperature" unit=" degC" tick={{ fontSize: 11 }} type="number" />
          <YAxis dataKey="kwh" name="Consommation" unit=" kWh" tick={{ fontSize: 11 }} type="number" />
          <RTooltip cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={climate.scatter} fill="#3b82f6" fillOpacity={0.6} r={3} name="Jours" />
          {climate.fit_line && climate.fit_line.length > 0 && (
            <Scatter data={climate.fit_line} fill="none" line={{ stroke: '#ef4444', strokeWidth: 2 }} shape={() => null} name="Regression" />
          )}
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        {climate.slope_kw_per_c != null && <span>Pente: {climate.slope_kw_per_c.toFixed(1)} kW/degC</span>}
        {climate.balance_point_c != null && <span>Tb: {climate.balance_point_c.toFixed(1)} degC</span>}
        {climate.r_squared != null && <span>R²: {climate.r_squared.toFixed(2)}</span>}
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
              <DrawerSection title="Evidence">
                {Object.entries(evidence).map(([k, v]) => (
                  <DrawerRow key={k} label={k}>
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </DrawerRow>
                ))}
              </DrawerSection>
            ) : (
              <p className="text-sm text-gray-400 text-center py-4">Pas d'evidence detaillee.</p>
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
              <DrawerRow label="Engine">Monitoring Engine v1.0</DrawerRow>
            </DrawerSection>
            <DrawerSection title="Seuils">
              <DrawerRow label="Seuil declenchement">Defini dans alert_engine.py</DrawerRow>
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
  const [demoProfile, setDemoProfile] = useState('office');

  // Drawer state
  const [drawerAlert, setDrawerAlert] = useState(null);
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
    if (alertFilter === 'all') return alerts;
    return alerts.filter((a) => a.status === alertFilter);
  }, [alerts, alertFilter]);

  const sortedAlerts = useMemo(() =>
    [...filteredAlerts].sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0)).slice(0, 8),
    [filteredAlerts]
  );

  const openCount = alerts.filter((a) => a.status === 'open').length;

  const allOrgSites = useMemo(() => mockSites, []);

  // KPI statuses
  const qualityStatus = kpiStatus(qualityScore, KPI_THRESHOLDS.quality);
  const riskStatus = kpiStatus(riskScore, KPI_THRESHOLDS.risk, true);
  const lfStatus = kpiStatus(
    kpiData.load_factor != null ? kpiData.load_factor * 100 : null,
    KPI_THRESHOLDS.loadFactor
  );
  const climateStatus = kpiStatus(climate?.slope_kw_per_c, KPI_THRESHOLDS.climate, true);

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
          {/* Resume Banner */}
          <ResumeBanner alerts={alerts} kpiData={kpiData} climate={climate} />

          {/* KPI Strip — 5 cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
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
              title="Load Factor"
              value={kpiData.load_factor != null ? `${fmtNum(kpiData.load_factor * 100)}%` : '-'}
              sub={`Peak/Avg: ${fmtNum(kpiData.peak_to_average)}x`}
              tooltip={KPI_TOOLTIPS.loadFactor}
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
            />
            <StatusKpiCard
              icon={CheckCircle}
              title="Qualite Donnees"
              value={qualityScore != null ? `${qualityScore}/100` : '-'}
              sub={qualityScore != null ? (qualityScore >= 80 ? 'Excellente' : qualityScore >= 60 ? 'Correcte' : 'Degradee') : ''}
              tooltip={KPI_TOOLTIPS.quality}
              status={qualityStatus}
              color={qualityScore >= 80 ? 'bg-green-500' : qualityScore >= 60 ? 'bg-yellow-500' : 'bg-red-500'}
            />
          </div>

          {/* Climate KPI card (if climate data available) */}
          {climate && climate.slope_kw_per_c != null && (
            <div className="mb-6">
              <StatusKpiCard
                icon={Thermometer}
                title="Sensibilite Climatique"
                value={`${climate.slope_kw_per_c.toFixed(1)} kW/degC`}
                sub={`R²: ${climate.r_squared != null ? climate.r_squared.toFixed(2) : '-'} | ${climate.label || 'unknown'}`}
                tooltip={KPI_TOOLTIPS.climate}
                status={climateStatus}
                color="bg-cyan-500"
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
                </h2>
                <WeekdayWeekendChart weekdayProfile={weekdayProfile} weekendProfile={weekendProfile} />
              </CardBody>
            </Card>

            {/* Heatmap 7x24 */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Sun size={18} /> Heatmap 7j × 24h
                </h2>
                <HeatmapGrid data={heatmapData} />
              </CardBody>
            </Card>

            {/* Conso vs Temperature */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Thermometer size={18} /> Conso vs Temperature
                </h2>
                <ClimateScatter climate={climate} />
              </CardBody>
            </Card>

            {/* Courbe de charge BarChart */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <BarChart3 size={18} /> Courbe de Charge (Semaine)
                </h2>
                {weekdayBarData ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={weekdayBarData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <RTooltip formatter={(v) => [`${v} kW`, 'Puissance']} />
                      <Bar dataKey="kw" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-gray-400 text-center py-12">
                    Lancez une analyse pour generer la courbe de charge.
                  </p>
                )}
              </CardBody>
            </Card>
          </div>

          {/* Insights & Alerts */}
          <Card className="mb-6">
            <CardBody>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                  <AlertTriangle size={18} className="text-orange-500" />
                  Insights & Alertes
                  {openCount > 0 && (
                    <Badge status="crit">{openCount} ouvertes</Badge>
                  )}
                </h2>
                <div className="flex gap-1">
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
                </div>
              </div>

              {sortedAlerts.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  {alerts.length === 0
                    ? 'Aucune alerte. Lancez une analyse pour detecter les anomalies.'
                    : 'Aucune alerte pour ce filtre.'}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-500">
                        <th className="pb-2 pr-4">Statut</th>
                        <th className="pb-2 pr-4">Type</th>
                        <th className="pb-2 pr-4">Severite</th>
                        <th className="pb-2 pr-4">Explication</th>
                        <th className="pb-2 pr-4 text-right">Impact</th>
                        <th className="pb-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedAlerts.map((a) => {
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
                              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">
                                {ALERT_TYPE_LABELS[a.alert_type] || a.alert_type}
                              </span>
                            </td>
                            <td className="py-3 pr-4">
                              <Badge status={SEVERITY_BADGE[a.severity] || 'neutral'}>{a.severity}</Badge>
                            </td>
                            <td className="py-3 pr-4 text-gray-600 max-w-md truncate">{a.explanation}</td>
                            <td className="py-3 pr-4 text-right text-red-600 font-medium">
                              {a.estimated_impact_eur ? `${a.estimated_impact_eur} EUR` : '-'}
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                {a.status === 'open' && (
                                  <Button size="sm" variant="secondary" onClick={() => handleAck(a.id)}>ACK</Button>
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
          <div className="flex items-center justify-between">
            <TrustBadge
              source="Monitoring Engine"
              period={kpis?.period}
              confidence={qualityScore >= 80 ? 'high' : qualityScore >= 50 ? 'medium' : 'low'}
            />
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
