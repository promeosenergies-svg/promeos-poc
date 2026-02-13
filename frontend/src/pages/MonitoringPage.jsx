/**
 * PROMEOS - MonitoringPage (/monitoring)
 * Electric Consumption Mastery — production-grade.
 * KPIs, Recharts power profile, alerts lifecycle, demo integration.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Activity, AlertTriangle, Zap, BarChart3, CheckCircle, Clock,
  Shield, TrendingUp, ChevronDown, ChevronUp, Eye, PlayCircle,
  Database, RefreshCw,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge, Skeleton } from '../ui';
import { SkeletonCard } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
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
};

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

function ScoreCard({ icon: Icon, iconColor, label, value, unit, sub, colorFn }) {
  const valColor = colorFn && value != null ? colorFn(value) : '';
  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-2 mb-2">
          <Icon size={18} className={iconColor} />
          <span className="text-sm text-gray-500">{label}</span>
        </div>
        <p className={`text-2xl font-bold ${valColor}`}>
          {value != null ? value : '-'}
          {unit && <span className="text-sm font-normal text-gray-400 ml-1">{unit}</span>}
        </p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </CardBody>
    </Card>
  );
}

function AlertCard({ alert, onAck, onResolve }) {
  const [expanded, setExpanded] = useState(false);
  const stCfg = STATUS_CONFIG[alert.status] || STATUS_CONFIG.open;
  const sevBadge = SEVERITY_BADGE[alert.severity] || 'neutral';
  const typeLabel = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type;

  return (
    <Card className="overflow-hidden">
      <CardBody className="space-y-2">
        {/* Header row */}
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge status={stCfg.badge}>{stCfg.label}</Badge>
              <span className="font-medium text-sm truncate">{typeLabel}</span>
              <Badge status={sevBadge}>{alert.severity}</Badge>
              {(alert.estimated_impact_kwh || alert.estimated_impact_eur) && (
                <span className="text-xs text-gray-500">
                  {alert.estimated_impact_kwh ? `${alert.estimated_impact_kwh} kWh` : ''}
                  {alert.estimated_impact_eur ? ` / ${alert.estimated_impact_eur} EUR` : ''}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 mt-1">{alert.explanation}</p>
            {alert.recommended_action && (
              <p className="text-xs text-gray-500 mt-1">Action: {alert.recommended_action}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-4 shrink-0">
            {alert.status === 'open' && (
              <Button size="sm" variant="secondary" onClick={() => onAck(alert.id)}>ACK</Button>
            )}
            {(alert.status === 'open' || alert.status === 'ack') && (
              <Button size="sm" variant="primary" onClick={() => onResolve(alert.id)}>Resoudre</Button>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 hover:bg-gray-100 rounded"
              title="Details"
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        </div>

        {/* Expanded details */}
        {expanded && (
          <div className="pt-2 border-t border-gray-100 space-y-2">
            {alert.evidence && Object.keys(alert.evidence).length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">Evidence</p>
                <div className="bg-gray-50 rounded p-2 text-xs font-mono overflow-x-auto">
                  {Object.entries(alert.evidence).map(([k, v]) => (
                    <div key={k}><span className="text-gray-500">{k}:</span> {JSON.stringify(v)}</div>
                  ))}
                </div>
              </div>
            )}
            {alert.kb_link && Object.keys(alert.kb_link).length > 0 && (
              <div className="flex items-center gap-1 text-xs text-indigo-600">
                <Eye size={12} />
                <span>KB: {alert.kb_link.item_type} / {alert.kb_link.code}</span>
              </div>
            )}
            <div className="text-xs text-gray-400">
              Cree: {alert.created_at?.slice(0, 16)}
              {alert.acknowledged_at && ` | ACK: ${alert.acknowledged_at.slice(0, 16)}`}
              {alert.resolved_at && ` | Resolu: ${alert.resolved_at.slice(0, 16)}`}
              {alert.resolution_note && ` — ${alert.resolution_note}`}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

// --- Main component ---

export default function MonitoringPage() {
  const { scope, scopedSites, setSite } = useScope();
  const siteId = scope.siteId;

  const [kpis, setKpis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [alertFilter, setAlertFilter] = useState('all');

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
      setKpis(kpiRes.status === 'fulfilled' ? kpiRes.value : null);
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
      await generateMonitoringDemo(siteId, 90);
      track('monitoring_demo', { site_id: siteId });
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
    } catch { /* ignore */ }
  };

  const handleResolve = async (id) => {
    try {
      await resolveMonitoringAlert(id, 'Resolu depuis UI');
      track('monitoring_resolve', { alert_id: id });
      setAlerts((prev) => prev.map((a) =>
        a.id === id ? { ...a, status: 'resolved' } : a
      ));
    } catch { /* ignore */ }
  };

  // --- Derived data ---

  const kpiData = kpis?.kpis || {};
  const qualityScore = kpis?.data_quality_score ?? null;
  const riskScore = kpis?.risk_power_score ?? null;

  const weekdayProfile = useMemo(() => {
    const data = kpiData.weekday_profile_kw;
    if (!data || !Array.isArray(data)) return null;
    return data.map((kw, hour) => ({
      hour: `${hour}h`,
      kw: Number(kw.toFixed(1)),
    }));
  }, [kpiData.weekday_profile_kw]);

  const filteredAlerts = useMemo(() => {
    if (alertFilter === 'all') return alerts;
    return alerts.filter((a) => a.status === alertFilter);
  }, [alerts, alertFilter]);

  const openCount = alerts.filter((a) => a.status === 'open').length;

  // --- No site selected ---

  if (!siteId) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Activity size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Performance Electrique</h1>
        </div>
        <EmptyState
          icon={Activity}
          title="Selectionnez un site"
          text="Choisissez un site dans le selecteur de perimetre pour voir les KPIs de performance electrique."
        />
      </div>
    );
  }

  // --- Loading skeleton ---

  if (loading && !kpis && alerts.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Activity size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Performance Electrique</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
        <Skeleton rows={6} />
      </div>
    );
  }

  const hasData = kpis || alerts.length > 0 || snapshots.length > 0;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity size={28} className="text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Performance Electrique</h1>
            <p className="text-sm text-gray-500">KPIs, puissance, qualite de donnees & alertes</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={siteId || ''}
            onChange={(e) => setSite(Number(e.target.value))}
          >
            {scopedSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nom || `Site ${s.id}`}
              </option>
            ))}
          </select>
          <Button variant="secondary" size="sm" onClick={handleRun} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Analyse...' : 'Lancer Analyse'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-red-700 text-sm">{error}</div>
      )}

      {/* Empty state with demo CTA */}
      {!hasData && (
        <EmptyState
          icon={Database}
          title="Aucune donnee de monitoring"
          text="Generez des donnees de demo pour explorer les KPIs de performance electrique, les profils jour-type et les alertes automatiques."
          ctaLabel={demoLoading ? 'Generation...' : 'Generer Donnees Demo'}
          onCta={handleDemo}
        />
      )}

      {hasData && (
        <>
          {/* Score Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <ScoreCard
              icon={Zap} iconColor="text-yellow-500"
              label="Pmax"
              value={kpiData.pmax_kw != null ? fmtNum(kpiData.pmax_kw) : null}
              unit="kW"
              sub={`P95: ${fmtNum(kpiData.p95_kw)} kW | P99: ${fmtNum(kpiData.p99_kw)} kW`}
            />
            <ScoreCard
              icon={BarChart3} iconColor="text-blue-500"
              label="Load Factor"
              value={kpiData.load_factor != null ? fmtNum(kpiData.load_factor * 100) : null}
              unit="%"
              sub={`Peak/Avg: ${fmtNum(kpiData.peak_to_average)}x`}
            />
            <ScoreCard
              icon={Shield}
              iconColor={riskScore != null ? riskColor(riskScore) : 'text-gray-400'}
              label="Risque Puissance"
              value={riskScore} unit="/100"
              colorFn={riskColor}
            />
            <ScoreCard
              icon={CheckCircle}
              iconColor={qualityScore != null ? scoreColor(qualityScore) : 'text-gray-400'}
              label="Qualite Donnees"
              value={qualityScore} unit="/100"
              colorFn={scoreColor}
            />
          </div>

          {/* KPI Details + Recharts Profile */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* KPI Details */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <TrendingUp size={18} /> KPIs Detailles
                </h2>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    ['Pmean', kpiData.pmean_kw, 'kW'],
                    ['Pbase (talon)', kpiData.pbase_kw, 'kW'],
                    ['Base nuit', kpiData.pbase_night_kw, 'kW'],
                    ['Total kWh', kpiData.total_kwh ? kpiData.total_kwh.toLocaleString() : null, ''],
                    ['Weekend ratio', kpiData.weekend_ratio != null ? fmtNum(kpiData.weekend_ratio * 100) + '%' : null, ''],
                    ['Night ratio', kpiData.night_ratio != null ? fmtNum(kpiData.night_ratio * 100) + '%' : null, ''],
                    ['Ramp rate max', kpiData.ramp_rate_max_kw_h, 'kW/h'],
                    ['Readings', kpiData.readings_count, ''],
                  ].map(([label, val, unit]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-gray-500">{label}</span>
                      <span className="font-medium">{val != null ? `${val}${unit ? ' ' + unit : ''}` : '-'}</span>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>

            {/* Recharts BarChart */}
            <Card>
              <CardBody>
                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Clock size={18} /> Profil Jour-Type (Semaine)
                </h2>
                {weekdayProfile ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={weekdayProfile}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={2} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v) => [`${v} kW`, 'Puissance']} />
                      <Bar dataKey="kw" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-gray-400 text-center py-12">
                    Lancez une analyse pour generer le profil jour-type.
                  </p>
                )}
              </CardBody>
            </Card>
          </div>

          {/* Alerts */}
          <Card className="mb-6">
            <CardBody>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                  <AlertTriangle size={18} className="text-orange-500" />
                  Alertes Monitoring
                  {openCount > 0 && (
                    <Badge status="crit">{openCount} ouvertes</Badge>
                  )}
                </h2>
                {/* Filter tabs */}
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

              {filteredAlerts.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  {alerts.length === 0
                    ? 'Aucune alerte. Lancez une analyse pour detecter les anomalies.'
                    : 'Aucune alerte pour ce filtre.'}
                </p>
              ) : (
                <div className="space-y-3">
                  {filteredAlerts.map((a) => (
                    <AlertCard key={a.id} alert={a} onAck={handleAck} onResolve={handleResolve} />
                  ))}
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
            <Button variant="ghost" size="sm" onClick={handleDemo} disabled={demoLoading}>
              <PlayCircle size={14} />
              {demoLoading ? 'Generation...' : 'Regenerer Demo'}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
