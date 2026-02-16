/**
 * PROMEOS - ConsumptionExplorerPage (/consommations/explorer)
 * Sprint V11: Unified StickyFilterBar + ContextBanner + availability handshake
 * Panels: Tunnel (P10-P90), Objectifs/Budgets, HP/HC, Gaz (beta)
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Target, Clock, Flame, BarChart3, TrendingUp,
  RefreshCw, AlertTriangle, CheckCircle, ChevronDown, ChevronUp,
  Plus, Trash2, Save, X, Zap, Database, Upload, Wifi,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge } from '../ui';
import { SkeletonCard } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
import {
  getConsumptionAvailability,
  getConsumptionTunnel,
  getConsumptionTargets,
  createConsumptionTarget,
  deleteConsumptionTarget,
  getTargetsProgression,
  getActiveTOUSchedule,
  getHPHCRatio,
  getGasSummary,
} from '../services/api';
import StickyFilterBar from './consumption/StickyFilterBar';
import ContextBanner from './consumption/ContextBanner';
import { computeAutoRange } from './consumption/helpers';

// ========================================
// Constants
// ========================================

const TAB_CONFIG = [
  { key: 'tunnel', label: 'Tunnel', icon: Activity, desc: 'Enveloppe P10-P90' },
  { key: 'targets', label: 'Objectifs', icon: Target, desc: 'Budgets & progression' },
  { key: 'hphc', label: 'HP/HC', icon: Clock, desc: 'Grille tarifaire' },
  { key: 'gas', label: 'Gaz', icon: Flame, desc: 'Beta' },
];

// ENERGY_OPTIONS + PERIOD_OPTIONS moved to StickyFilterBar

const CONFIDENCE_BADGE = {
  high: { label: 'Haute', variant: 'ok' },
  medium: { label: 'Moyenne', variant: 'warn' },
  low: { label: 'Basse', variant: 'crit' },
};

const ALERT_COLOR = {
  on_track: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', label: 'En bonne voie' },
  at_risk: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'A risque' },
  over_budget: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', label: 'Hors budget' },
};

const REASON_CONFIG = {
  no_site: {
    icon: AlertTriangle,
    title: 'Site introuvable',
    text: 'Le site selectionne n\'existe pas ou a ete supprime. Verifiez votre selection.',
    ctaLabel: null,
  },
  no_meter: {
    icon: Wifi,
    title: 'Aucun compteur configure',
    text: 'Ce site n\'a pas encore de compteur rattache. Connectez Enedis / GRDF ou ajoutez un compteur manuellement.',
    ctaLabel: 'Connecter un compteur',
    ctaPath: '/connectors',
  },
  no_readings: {
    icon: Database,
    title: 'Compteur present, aucun releve',
    text: 'Un compteur est configure mais aucune donnee de consommation n\'a ete importee.',
    ctaLabel: 'Importer des donnees',
    ctaPath: '/consommations/import',
  },
  insufficient_readings: {
    icon: BarChart3,
    title: 'Donnees insuffisantes',
    text: 'Moins de 48 releves disponibles. L\'analyse necessite davantage de donnees pour etre fiable.',
    ctaLabel: 'Importer des donnees',
    ctaPath: '/consommations/import',
  },
  wrong_energy_type: {
    icon: Zap,
    title: 'Pas de donnees pour ce type d\'energie',
    text: null, // dynamic
    ctaLabel: null,
  },
};

// ========================================
// Smart Empty State
// ========================================

function SmartEmptyState({ reasons, energyTypes, onNavigate, onSwitchEnergy }) {
  if (!reasons?.length) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Aucune donnee disponible"
        text="Verifiez la configuration du site ou importez des donnees."
      />
    );
  }

  const primary = reasons[0];
  const config = REASON_CONFIG[primary] || REASON_CONFIG.no_readings;
  const Icon = config.icon;

  // Dynamic text for wrong_energy_type
  let text = config.text;
  if (primary === 'wrong_energy_type' && energyTypes?.length > 0) {
    text = `Aucune donnee pour ce vecteur energetique. Types disponibles : ${energyTypes.join(', ')}.`;
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={32} className="text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{config.title}</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-md">{text}</p>
      <div className="flex items-center gap-3">
        {config.ctaLabel && config.ctaPath && (
          <Button onClick={() => onNavigate(config.ctaPath)}>
            {config.ctaLabel}
          </Button>
        )}
        {primary === 'wrong_energy_type' && energyTypes?.length > 0 && (
          <Button onClick={() => onSwitchEnergy(energyTypes[0])}>
            Basculer vers {energyTypes[0]}
          </Button>
        )}
      </div>
      {reasons.length > 1 && (
        <p className="text-xs text-gray-400 mt-4">
          Diagnostics : {reasons.join(', ')}
        </p>
      )}
    </div>
  );
}

// ========================================
// Availability Skeleton
// ========================================

function AvailabilitySkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-10 bg-gray-200 rounded-lg w-full" />
      <div className="grid grid-cols-3 gap-3">
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
      </div>
      <div className="h-64 bg-gray-200 rounded-lg" />
    </div>
  );
}

// FilterBar + ContextBanner extracted to consumption/StickyFilterBar + consumption/ContextBanner

// ========================================
// Tunnel Panel
// ========================================

function TunnelPanel({ siteId, days, energyType }) {
  const [tunnel, setTunnel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dayType, setDayType] = useState('weekday');

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const data = await getConsumptionTunnel(siteId, days, energyType);
      setTunnel(data);
      track('tunnel_loaded', { site_id: siteId, days, energy_type: energyType });
    } catch (e) {
      console.error('Tunnel load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, days, energyType]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <SkeletonCard rows={6} />;
  if (!tunnel || tunnel.readings_count === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="Aucune donnee de consommation"
        text="Importez des releves ou generez des donnees demo pour voir l'enveloppe tunnel."
      />
    );
  }

  const conf = CONFIDENCE_BADGE[tunnel.confidence] || CONFIDENCE_BADGE.low;
  const envelope = tunnel.envelope?.[dayType] || [];
  const chartData = envelope.map(s => ({
    hour: `${s.hour}h`,
    p10: s.p10, p25: s.p25, p50: s.p50, p75: s.p75, p90: s.p90,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Enveloppe de consommation</h3>
          <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
        </div>
        <Button size="sm" variant="ghost" onClick={load}>
          <RefreshCw size={14} />
        </Button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Releves</p>
            <p className="text-xl font-bold text-gray-800">{tunnel.readings_count.toLocaleString()}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">% hors bande</p>
            <p className={`text-xl font-bold ${tunnel.outside_pct > 15 ? 'text-red-600' : tunnel.outside_pct > 5 ? 'text-amber-600' : 'text-green-600'}`}>
              {tunnel.outside_pct}%
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Hors bande (7j)</p>
            <p className="text-xl font-bold text-gray-800">{tunnel.outside_count}/{tunnel.total_evaluated}</p>
          </CardBody>
        </Card>
      </div>

      {/* Day type selector */}
      <div className="flex gap-2">
        <button
          className={`px-3 py-1 rounded-full text-sm font-medium transition ${dayType === 'weekday' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          onClick={() => setDayType('weekday')}
        >
          Semaine
        </button>
        <button
          className={`px-3 py-1 rounded-full text-sm font-medium transition ${dayType === 'weekend' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          onClick={() => setDayType('weekend')}
        >
          Week-end
        </button>
      </div>

      {/* Tunnel chart */}
      <Card>
        <CardBody>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} label={{ value: 'kW', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
              <Tooltip formatter={(v) => `${v} kW`} />
              <Area type="monotone" dataKey="p90" stroke="#ef4444" fill="#fecaca" fillOpacity={0.3} name="P90" />
              <Area type="monotone" dataKey="p75" stroke="#f59e0b" fill="#fde68a" fillOpacity={0.3} name="P75" />
              <Area type="monotone" dataKey="p50" stroke="#3b82f6" fill="#93c5fd" fillOpacity={0.5} name="P50 (mediane)" />
              <Area type="monotone" dataKey="p25" stroke="#10b981" fill="#6ee7b7" fillOpacity={0.3} name="P25" />
              <Area type="monotone" dataKey="p10" stroke="#6b7280" fill="#e5e7eb" fillOpacity={0.3} name="P10" />
              <Legend />
            </AreaChart>
          </ResponsiveContainer>
        </CardBody>
      </Card>
    </div>
  );
}

// ========================================
// Targets Panel (Objectifs & Budgets)
// ========================================

function TargetsPanel({ siteId, energyType }) {
  const [targets, setTargets] = useState([]);
  const [progression, setProgression] = useState(null);
  const [loading, setLoading] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());
  const [showAdd, setShowAdd] = useState(false);
  const [newTarget, setNewTarget] = useState({ month: 1, target_kwh: '', target_eur: '' });

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [t, p] = await Promise.all([
        getConsumptionTargets(siteId, energyType, year),
        getTargetsProgression(siteId, energyType, year),
      ]);
      setTargets(t);
      setProgression(p);
      track('targets_loaded', { site_id: siteId, year, energy_type: energyType });
    } catch (e) {
      console.error('Targets load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, year, energyType]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    try {
      await createConsumptionTarget({
        site_id: siteId,
        energy_type: energyType,
        period: 'monthly',
        year,
        month: newTarget.month,
        target_kwh: parseFloat(newTarget.target_kwh) || null,
        target_eur: parseFloat(newTarget.target_eur) || null,
      });
      setShowAdd(false);
      setNewTarget({ month: 1, target_kwh: '', target_eur: '' });
      load();
    } catch (e) {
      console.error('Add target error:', e);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteConsumptionTarget(id);
      load();
    } catch (e) {
      console.error('Delete target error:', e);
    }
  };

  if (loading) return <SkeletonCard rows={6} />;

  const alert = progression?.alert;
  const alertConf = ALERT_COLOR[alert] || ALERT_COLOR.on_track;

  const MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec'];

  const chartData = (progression?.months || []).map(m => ({
    name: MONTH_NAMES[m.month - 1],
    objectif: m.target_kwh,
    reel: m.actual_kwh,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Objectifs & Budgets</h3>
        <div className="flex items-center gap-2">
          <select value={year} onChange={(e) => setYear(Number(e.target.value))} className="text-sm border rounded px-2 py-1">
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <Button size="sm" variant="ghost" onClick={() => setShowAdd(!showAdd)}>
            <Plus size={14} className="mr-1" /> Objectif
          </Button>
        </div>
      </div>

      {/* Alert banner */}
      {progression && (
        <div className={`${alertConf.bg} ${alertConf.border} border rounded-lg p-3`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {alert === 'on_track' ? <CheckCircle size={16} className="text-green-600" /> : <AlertTriangle size={16} className={alertConf.text} />}
              <span className={`text-sm font-medium ${alertConf.text}`}>{alertConf.label}</span>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Progression YTD</p>
              <p className={`text-lg font-bold ${alertConf.text}`}>{progression.progress_pct}%</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 mt-3 text-center">
            <div>
              <p className="text-xs text-gray-500">Objectif annuel</p>
              <p className="text-sm font-semibold">{(progression.yearly_target_kwh || 0).toLocaleString()} kWh</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Reel YTD</p>
              <p className="text-sm font-semibold">{(progression.ytd_actual_kwh || 0).toLocaleString()} kWh</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Prevision annuelle</p>
              <p className={`text-sm font-semibold ${progression.forecast_vs_target_pct > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {(progression.forecast_year_kwh || 0).toLocaleString()} kWh
                <span className="text-xs ml-1">({progression.forecast_vs_target_pct > 0 ? '+' : ''}{progression.forecast_vs_target_pct}%)</span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <Card>
          <CardBody className="flex items-end gap-3">
            <div>
              <label className="text-xs text-gray-500 block">Mois</label>
              <select value={newTarget.month} onChange={(e) => setNewTarget({ ...newTarget, month: Number(e.target.value) })} className="text-sm border rounded px-2 py-1">
                {MONTH_NAMES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block">Objectif kWh</label>
              <input type="number" value={newTarget.target_kwh} onChange={(e) => setNewTarget({ ...newTarget, target_kwh: e.target.value })} className="text-sm border rounded px-2 py-1 w-28" placeholder="5000" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block">Budget EUR</label>
              <input type="number" value={newTarget.target_eur} onChange={(e) => setNewTarget({ ...newTarget, target_eur: e.target.value })} className="text-sm border rounded px-2 py-1 w-28" placeholder="900" />
            </div>
            <Button size="sm" onClick={handleAdd}><Save size={14} className="mr-1" /> Enregistrer</Button>
            <Button size="sm" variant="ghost" onClick={() => setShowAdd(false)}><X size={14} /></Button>
          </CardBody>
        </Card>
      )}

      {/* Bar chart */}
      {chartData.length > 0 && (
        <Card>
          <CardBody>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} label={{ value: 'kWh', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
                <Tooltip formatter={(v) => v != null ? `${v.toLocaleString()} kWh` : 'N/A'} />
                <Legend />
                <Bar dataKey="objectif" fill="#93c5fd" name="Objectif" />
                <Bar dataKey="reel" fill="#3b82f6" name="Reel" />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Targets table */}
      {targets.length > 0 && (
        <Card>
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-2">Mois</th>
                  <th className="text-right px-4 py-2">Objectif kWh</th>
                  <th className="text-right px-4 py-2">Reel kWh</th>
                  <th className="text-right px-4 py-2">Ecart</th>
                  <th className="text-center px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {targets.map((t) => {
                  const delta = t.actual_kwh != null && t.target_kwh ? ((t.actual_kwh - t.target_kwh) / t.target_kwh * 100).toFixed(1) : null;
                  return (
                    <tr key={t.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-2">{t.month ? MONTH_NAMES[t.month - 1] : 'Annuel'} {t.year}</td>
                      <td className="px-4 py-2 text-right">{t.target_kwh?.toLocaleString() || '—'}</td>
                      <td className="px-4 py-2 text-right">{t.actual_kwh?.toLocaleString() || '—'}</td>
                      <td className={`px-4 py-2 text-right font-medium ${delta && parseFloat(delta) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {delta ? `${delta > 0 ? '+' : ''}${delta}%` : '—'}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <button onClick={() => handleDelete(t.id)} className="text-gray-400 hover:text-red-500 transition">
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

// ========================================
// HP/HC Panel
// ========================================

function HPHCPanel({ siteId, days }) {
  const [ratio, setRatio] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [r, s] = await Promise.all([
        getHPHCRatio(siteId, null, days),
        getActiveTOUSchedule(siteId),
      ]);
      setRatio(r);
      setSchedule(s);
      track('hphc_loaded', { site_id: siteId, days });
    } catch (e) {
      console.error('HP/HC load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, days]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <SkeletonCard rows={4} />;

  const conf = CONFIDENCE_BADGE[ratio?.confidence] || CONFIDENCE_BADGE.low;
  const hpPct = ratio ? Math.round(ratio.hp_ratio * 100) : 0;
  const hcPct = 100 - hpPct;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Ratio HP / HC</h3>
          {ratio && <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />}
        </div>
      </div>

      {ratio && ratio.total_kwh > 0 ? (
        <>
          {/* HP/HC bar */}
          <Card>
            <CardBody>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-600">Grille : {schedule?.name || 'Par defaut'}</span>
                {schedule?.source && <Badge variant="info">{schedule.source}</Badge>}
              </div>
              <div className="w-full h-8 rounded-full overflow-hidden flex">
                <div className="bg-red-400 flex items-center justify-center" style={{ width: `${hpPct}%` }}>
                  <span className="text-xs font-bold text-white">{hpPct}% HP</span>
                </div>
                <div className="bg-blue-400 flex items-center justify-center" style={{ width: `${hcPct}%` }}>
                  <span className="text-xs font-bold text-white">{hcPct}% HC</span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* KPI grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">HP</p>
                <p className="text-lg font-bold text-red-600">{ratio.hp_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{ratio.hp_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">HC</p>
                <p className="text-lg font-bold text-blue-600">{ratio.hc_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{ratio.hc_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Total</p>
                <p className="text-lg font-bold text-gray-800">{ratio.total_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{ratio.total_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Prix HP/HC</p>
                <p className="text-sm font-semibold text-gray-700">
                  {schedule?.price_hp_eur_kwh || '—'} / {schedule?.price_hc_eur_kwh || '—'} EUR/kWh
                </p>
              </CardBody>
            </Card>
          </div>

          {/* Schedule windows */}
          {schedule?.windows?.length > 0 && (
            <Card>
              <CardBody>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Plages horaires</h4>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-1.5">Jours</th>
                      <th className="text-left px-3 py-1.5">Debut</th>
                      <th className="text-left px-3 py-1.5">Fin</th>
                      <th className="text-left px-3 py-1.5">Periode</th>
                      <th className="text-right px-3 py-1.5">Prix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.windows.map((w, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-3 py-1.5">{(w.day_types || []).join(', ')}</td>
                        <td className="px-3 py-1.5">{w.start}</td>
                        <td className="px-3 py-1.5">{w.end}</td>
                        <td className="px-3 py-1.5">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${w.period === 'HP' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                            {w.period}
                          </span>
                        </td>
                        <td className="px-3 py-1.5 text-right">{w.price_eur_kwh ? `${w.price_eur_kwh} EUR` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>
          )}
        </>
      ) : (
        <EmptyState
          icon={Clock}
          title="Aucune donnee HP/HC"
          text="Importez des releves electricite pour voir la repartition HP/HC."
        />
      )}
    </div>
  );
}

// ========================================
// Gas Panel (Beta)
// ========================================

function GasPanel({ siteId, days }) {
  const [gas, setGas] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const data = await getGasSummary(siteId, days);
      setGas(data);
      track('gas_loaded', { site_id: siteId, days });
    } catch (e) {
      console.error('Gas load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, days]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <SkeletonCard rows={4} />;
  if (!gas || gas.readings_count === 0) {
    return (
      <EmptyState
        icon={Flame}
        title="Aucun compteur gaz"
        text="Ajoutez un compteur gaz et importez des releves pour voir le resume."
      />
    );
  }

  const conf = CONFIDENCE_BADGE[gas.confidence] || CONFIDENCE_BADGE.low;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Consommation Gaz</h3>
          <Badge variant="warn">Beta</Badge>
          <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-xl font-bold text-gray-800">{gas.total_kwh.toLocaleString()} kWh</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Moy. journaliere</p>
            <p className="text-xl font-bold text-gray-800">{gas.avg_daily_kwh.toLocaleString()} kWh</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Base ete</p>
            <p className="text-xl font-bold text-amber-600">{gas.summer_base_kwh.toLocaleString()} kWh/j</p>
          </CardBody>
        </Card>
      </div>

      {/* Daily chart */}
      {gas.daily_kwh?.length > 0 && (
        <Card>
          <CardBody>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={gas.daily_kwh.slice(-60)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11 }} label={{ value: 'kWh', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
                <Tooltip formatter={(v) => `${v} kWh`} />
                <Bar dataKey="kwh" fill="#f59e0b" name="Conso gaz" />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

// ========================================
// Main Page
// ========================================

export default function ConsumptionExplorerPage() {
  const [activeTab, setActiveTab] = useState('tunnel');
  const { selectedSiteId, sites } = useScope();
  const [siteId, setSiteId] = useState(null);

  // V10.1: Availability handshake
  const [availability, setAvailability] = useState(null);
  const [availLoading, setAvailLoading] = useState(false);

  // Filters
  const [energyType, setEnergyType] = useState('electricity');
  const [days, setDays] = useState(90);

  // Resolve siteId from scope
  useEffect(() => {
    if (selectedSiteId) {
      setSiteId(selectedSiteId);
    } else if (sites?.length > 0) {
      setSiteId(sites[0].id);
    }
  }, [selectedSiteId, sites]);

  // Availability check on siteId or energyType change
  const checkAvailability = useCallback(async () => {
    if (!siteId) return;
    setAvailLoading(true);
    try {
      const data = await getConsumptionAvailability(siteId, energyType);
      setAvailability(data);
      track('availability_checked', { site_id: siteId, energy_type: energyType, has_data: data.has_data });

      // Auto-calibrate period from available data range
      if (data.has_data && data.first_ts && data.last_ts) {
        setDays(computeAutoRange(data.first_ts, data.last_ts));
      }

      // Auto-switch to gas tab if only gas data
      if (data.has_data && energyType === 'gas' && activeTab === 'tunnel') {
        setActiveTab('gas');
      }
    } catch (e) {
      console.error('Availability check error:', e);
      setAvailability(null);
    } finally {
      setAvailLoading(false);
    }
  }, [siteId, energyType]);

  useEffect(() => { checkAvailability(); }, [checkAvailability]);

  // Navigation helper for CTAs
  const handleNavigate = useCallback((path) => {
    window.location.href = path;
  }, []);

  // Energy switch from empty state CTA
  const handleSwitchEnergy = useCallback((type) => {
    setEnergyType(type);
    if (type === 'gas') setActiveTab('gas');
    else setActiveTab('tunnel');
  }, []);

  const hasData = availability?.has_data === true;
  const showContent = hasData && !availLoading;

  return (
    <div className="space-y-5">
      {/* Unified sticky filter bar */}
      <StickyFilterBar
        siteId={siteId}
        setSiteId={setSiteId}
        sites={sites}
        energyType={energyType}
        setEnergyType={setEnergyType}
        availableTypes={availability?.energy_types}
        days={days}
        setDays={setDays}
        availability={availability}
      />

      {/* Context banner (site info + date range) */}
      <ContextBanner availability={availability} />

      {/* Loading skeleton */}
      {availLoading && <AvailabilitySkeleton />}

      {/* Smart empty state (no data) */}
      {!availLoading && availability && !hasData && (
        <SmartEmptyState
          reasons={availability.reasons}
          energyTypes={availability.energy_types}
          onNavigate={handleNavigate}
          onSwitchEnergy={handleSwitchEnergy}
        />
      )}

      {/* Main content (data available) */}
      {showContent && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {TAB_CONFIG.map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              // Hide gas tab if electricity, and hphc if gas
              if (tab.key === 'gas' && energyType !== 'gas') return null;
              if ((tab.key === 'hphc' || tab.key === 'tunnel' || tab.key === 'targets') && energyType === 'gas') {
                if (tab.key !== 'gas') return null;
              }
              return (
                <button
                  key={tab.key}
                  onClick={() => { setActiveTab(tab.key); track('explorer_tab', { tab: tab.key }); }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition flex-1 justify-center ${
                    active ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Icon size={16} />
                  <span>{tab.label}</span>
                  {tab.key === 'gas' && <Badge variant="warn" className="text-[10px] px-1 py-0">Beta</Badge>}
                </button>
              );
            })}
          </div>

          {/* Panel content */}
          <div>
            {activeTab === 'tunnel' && <TunnelPanel siteId={siteId} days={days} energyType={energyType} />}
            {activeTab === 'targets' && <TargetsPanel siteId={siteId} energyType={energyType} />}
            {activeTab === 'hphc' && <HPHCPanel siteId={siteId} days={days} />}
            {activeTab === 'gas' && <GasPanel siteId={siteId} days={days} />}
          </div>
        </>
      )}
    </div>
  );
}
