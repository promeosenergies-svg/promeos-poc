/**
 * PROMEOS - ConsumptionExplorerPage (/consommations/explorer)
 * Sprint V11 WoW: Motor + Layers architecture
 * Motor: useExplorerMotor (data engine) + useExplorerURL (URL state sync)
 * Panels: Tunnel (P10-P90), Objectifs/Budgets, HP/HC, Gaz (beta)
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Target, Clock, Flame, BarChart3,
  RefreshCw, AlertTriangle, CheckCircle,
  Plus, Trash2, Save, X, Zap, Database, Wifi,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, ComposedChart, Line,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge } from '../ui';
import { SkeletonCard } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
import {
  getConsumptionTunnel,
  getConsumptionTargets,
  createConsumptionTarget,
  deleteConsumptionTarget,
  getTargetsProgression,
  getActiveTOUSchedule,
  getHPHCRatio,
} from '../services/api';
import StickyFilterBar from './consumption/StickyFilterBar';
import ContextBanner from './consumption/ContextBanner';
import EvidenceDrawer from './consumption/EvidenceDrawer';
import HeatmapChart from './consumption/HeatmapChart';
import ExplorerChart from './consumption/ExplorerChart';
import LayerToggle from './consumption/LayerToggle';
import TunnelLayer from './consumption/layers/TunnelLayer';
import ObjectivesLayer from './consumption/layers/ObjectivesLayer';
import SignatureLayer from './consumption/layers/SignatureLayer';
import InsightsStrip from './consumption/InsightsStrip';
import { computeAutoRange } from './consumption/helpers';
import { computeInsights } from './consumption/insightRules';
import useExplorerMotor from './consumption/useExplorerMotor';
import useExplorerURL from './consumption/useExplorerURL';
import useExplorerPresets from './consumption/useExplorerPresets';
import useExplorerMode from './consumption/useExplorerMode';
import PortfolioPanel from './consumption/PortfolioPanel';
import OverviewRow, { computeOverviewData } from './consumption/OverviewRow';
import { MAX_SITES } from './consumption/types';

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

function TunnelPanel({ siteId, days, energyType, showSignature = false }) {
  const [tunnel, setTunnel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dayType, setDayType] = useState('weekday');
  const [mode, setMode] = useState('energy');
  const [selectedSlot, setSelectedSlot] = useState(null);
  // Layer toggles local to TunnelPanel (tunnel layer on by default)
  const [showP10P90, setShowP10P90] = useState(true);
  const [showP25P75, setShowP25P75] = useState(true);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const data = await getConsumptionTunnelV2(siteId, days, energyType, mode);
      setTunnel(data);
      track('tunnel_loaded', { site_id: siteId, days, energy_type: energyType, mode });
    } catch (e) {
      console.error('Tunnel load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, days, energyType, mode]);

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
  const unit = tunnel.unit || (mode === 'power' ? 'kW' : 'kWh');
  const envelope = tunnel.envelope?.[dayType] || [];
  const chartData = envelope.map(s => ({
    hour: `${s.hour}h`,
    hourNum: s.hour,
    p10: s.p10, p25: s.p25, p50: s.p50, p75: s.p75, p90: s.p90,
  }));

  const handleChartClick = (data) => {
    if (data?.activePayload?.[0]?.payload) {
      const point = data.activePayload[0].payload;
      setSelectedSlot({ hour: point.hourNum, dayType });
    }
  };

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

      {/* Mode toggle (kWh / kW) + Day type selector */}
      <div className="flex items-center justify-between flex-wrap gap-2">
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
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setMode('energy')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition ${mode === 'energy' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            kWh
          </button>
          <button
            onClick={() => setMode('power')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition ${mode === 'power' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            kW
          </button>
        </div>
      </div>

      {/* Tunnel chart + LayerToggle sidebar */}
      <Card>
        <CardBody>
          <div className="flex gap-4">
            {/* Chart (composable) */}
            <div className="flex-1 min-w-0">
              <ExplorerChart
                data={chartData}
                xKey="hour"
                valueKey="p50"
                mode="agrege"
                unit={mode === 'power' ? 'kw' : 'kwh'}
                height={300}
                onSlotClick={handleChartClick}
                summaryData={{
                  points: chartData.length,
                  series: 1,
                  meters: tunnel.meters_count,
                  source: tunnel.source,
                  quality: tunnel.readings_count
                    ? Math.round(Math.min(100, tunnel.readings_count / 500 * 100))
                    : null,
                }}
              >
                {/* Composable TunnelLayer (P10-P25-P50-P75-P90) */}
                <TunnelLayer visible={showP10P90} opacity={showP25P75 ? 0.2 : 0.3} />
                {/* Signature overlay (rolling 7-period mean) */}
                <SignatureLayer visible={showSignature} />
              </ExplorerChart>
              <p className="text-xs text-gray-400 mt-1 text-center">Cliquez sur un creneau pour ouvrir l'analyse detaillee</p>
            </div>

            {/* Layer toggle sidebar */}
            <LayerToggle
              layers={{ tunnel: showP10P90, talon: showP25P75, signature: showSignature }}
              onToggle={(key) => {
                if (key === 'tunnel') setShowP10P90(v => !v);
                if (key === 'talon') setShowP25P75(v => !v);
                // signature is controlled by Motor layers (toggleLayer in parent)
              }}
            />
          </div>
        </CardBody>
      </Card>

      {/* Evidence drawer */}
      {selectedSlot && (
        <EvidenceDrawer
          slot={selectedSlot}
          tunnelData={tunnel}
          onClose={() => setSelectedSlot(null)}
          onCreateAction={(ctx) => {
            track('evidence_action', ctx);
            setSelectedSlot(null);
          }}
        />
      )}
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
        getTargetsProgressionV2(siteId, energyType, year),
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
          <div className="grid grid-cols-4 gap-4 mt-3 text-center">
            <div>
              <p className="text-xs text-gray-500">Objectif annuel</p>
              <p className="text-sm font-semibold">{(progression.yearly_target_kwh || 0).toLocaleString()} kWh</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Reel YTD</p>
              <p className="text-sm font-semibold">{(progression.ytd_actual_kwh || 0).toLocaleString()} kWh</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Run-rate annuel</p>
              <p className={`text-sm font-semibold ${(progression.run_rate_kwh || 0) > (progression.yearly_target_kwh || 0) ? 'text-red-600' : 'text-green-600'}`}>
                {(progression.run_rate_kwh || 0).toLocaleString()} kWh
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Prevision</p>
              <p className={`text-sm font-semibold ${progression.forecast_vs_target_pct > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {progression.forecast_vs_target_pct > 0 ? '+' : ''}{progression.forecast_vs_target_pct}%
              </p>
            </div>
          </div>

          {/* Variance decomposition (top 3 causes) */}
          {progression.variance_decomposition?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">Causes principales de l'ecart :</p>
              <div className="space-y-1.5">
                {progression.variance_decomposition.map((cause, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      cause.severity === 'critical' ? 'bg-red-500' : cause.severity === 'high' ? 'bg-orange-500' : 'bg-amber-500'
                    }`} />
                    <span className="text-gray-700 flex-1">{cause.label}</span>
                    <span className="font-semibold text-gray-800">{(cause.estimated_loss_kwh || 0).toLocaleString()} kWh/an</span>
                  </div>
                ))}
              </div>
            </div>
          )}
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

      {/* Bar chart with ObjectivesLayer overlay */}
      {chartData.length > 0 && (
        <Card>
          <CardBody>
            <div className="flex gap-4">
              <div className="flex-1 min-w-0">
                <ExplorerChart
                  data={chartData}
                  xKey="name"
                  valueKey="reel"
                  mode="agrege"
                  unit="kwh"
                  height={250}
                  summaryData={{
                    points: chartData.length,
                    series: targets.length,
                  }}
                >
                  <Bar dataKey="objectif" fill="#93c5fd" name="Objectif" />
                  <Bar dataKey="reel" fill="#3b82f6" name="Reel" />
                  <ObjectivesLayer targets={targets} visible unit="kwh" />
                </ExplorerChart>
              </div>
              <LayerToggle
                layers={{ objectifs: true }}
                onToggle={() => {}}
              />
            </div>
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
  const [breakdown, setBreakdown] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [bd, s] = await Promise.all([
        getHPHCBreakdownV2(siteId, days),
        getActiveTOUSchedule(siteId),
      ]);
      setBreakdown(bd);
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

  const conf = CONFIDENCE_BADGE[breakdown?.confidence] || CONFIDENCE_BADGE.low;
  const hpPct = breakdown ? Math.round(breakdown.hp_ratio * 100) : 0;
  const hcPct = 100 - hpPct;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Ratio HP / HC</h3>
          {breakdown && <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />}
        </div>
      </div>

      {breakdown && breakdown.total_kwh > 0 ? (
        <>
          {/* HP/HC bar */}
          <Card>
            <CardBody>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-600">Calendrier : {breakdown.calendar_name || schedule?.name || 'Par defaut'}</span>
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
                <p className="text-lg font-bold text-red-600">{breakdown.hp_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{breakdown.hp_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">HC</p>
                <p className="text-lg font-bold text-blue-600">{breakdown.hc_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{breakdown.hc_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Total</p>
                <p className="text-lg font-bold text-gray-800">{breakdown.total_kwh.toLocaleString()} kWh</p>
                <p className="text-xs text-gray-400">{breakdown.total_cost_eur.toLocaleString()} EUR</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Prix HP/HC</p>
                <p className="text-sm font-semibold text-gray-700">
                  {breakdown.opportunity?.price_hp || '—'} / {breakdown.opportunity?.price_hc || '—'} EUR/kWh
                </p>
              </CardBody>
            </Card>
          </div>

          {/* Opportunity card */}
          {breakdown.opportunity?.savings_eur > 0 && (
            <Card className="bg-green-50 border-green-200">
              <CardBody className="py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-green-700">Opportunite de report HP → HC</p>
                    <p className="text-sm text-green-800 mt-0.5">
                      ~{breakdown.opportunity.shiftable_kwh.toLocaleString()} kWh reportables
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-700">{breakdown.opportunity.savings_eur} EUR</p>
                    <p className="text-xs text-green-600">economies potentielles</p>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Heatmap 7x24 */}
          {breakdown.heatmap?.length > 0 && (
            <Card>
              <CardBody>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Carte thermique HP/HC (7j x 24h)</h4>
                <HeatmapChart data={breakdown.heatmap} />
              </CardBody>
            </Card>
          )}

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
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [g, w] = await Promise.all([
        getGasSummary(siteId, days),
        getGasWeatherNormalized(siteId, days).catch(() => null),
      ]);
      setGas(g);
      setWeather(w);
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
  const model = weather?.model;
  const SEVERITY_STYLE = {
    high: 'bg-red-50 border-red-200 text-red-700',
    medium: 'bg-amber-50 border-amber-200 text-amber-700',
    low: 'bg-gray-50 border-gray-200 text-gray-700',
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Consommation Gaz</h3>
          <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
        {model && (
          <>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Base (talon)</p>
                <p className="text-xl font-bold text-amber-600">{model.base_kwh_day} kWh/j</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="py-3 px-4 text-center">
                <p className="text-xs text-gray-500">Sensibilite R²</p>
                <p className={`text-xl font-bold ${model.r_squared > 0.7 ? 'text-green-600' : model.r_squared > 0.4 ? 'text-amber-600' : 'text-gray-600'}`}>
                  {model.r_squared}
                </p>
              </CardBody>
            </Card>
          </>
        )}
      </div>

      {/* Decomposition bar */}
      {weather?.decomposition && (
        <Card>
          <CardBody className="py-3">
            <p className="text-xs font-semibold text-gray-600 mb-2">Decomposition base / chauffage</p>
            <div className="w-full h-6 rounded-full overflow-hidden flex">
              <div className="bg-amber-400 flex items-center justify-center" style={{ width: `${weather.decomposition.base_pct}%` }}>
                <span className="text-[10px] font-bold text-white">{weather.decomposition.base_pct}% Base</span>
              </div>
              <div className="bg-orange-500 flex items-center justify-center" style={{ width: `${weather.decomposition.heating_pct}%` }}>
                <span className="text-[10px] font-bold text-white">{weather.decomposition.heating_pct}% Chauffage</span>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* DJU scatter chart (Sensibilite climatique) */}
      {weather?.dju_data?.length > 0 && (
        <Card>
          <CardBody>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Sensibilite climatique (DJU vs Conso)</h4>
            <ResponsiveContainer width="100%" height={250}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="dju" name="DJU" tick={{ fontSize: 11 }} label={{ value: 'DJU', position: 'insideBottom', offset: -5, style: { fontSize: 11 } }} />
                <YAxis dataKey="kwh" name="kWh" tick={{ fontSize: 11 }} label={{ value: 'kWh/j', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
                <Tooltip formatter={(v, name) => [`${v}`, name === 'dju' ? 'DJU' : 'kWh/j']} />
                <Scatter data={weather.dju_data} fill="#f59e0b" name="Conso journaliere" />
              </ScatterChart>
            </ResponsiveContainer>
            {model && (
              <p className="text-xs text-gray-500 mt-1 text-center">
                Modele : kWh = {model.slope} × DJU + {model.intercept} (R² = {model.r_squared})
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Raw + normalized chart */}
      {weather?.dju_data?.length > 0 && (
        <Card>
          <CardBody>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Conso brute vs corrigee meteo</h4>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={weather.dju_data.slice(-60)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11 }} label={{ value: 'kWh', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
                <Tooltip />
                <Bar dataKey="kwh" fill="#f59e0b" name="Brut (kWh)" opacity={0.7} />
                <Line dataKey="normalized_kwh" stroke="#3b82f6" name="Corrige meteo" dot={false} strokeWidth={2} />
                <Legend />
              </ComposedChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Alerts */}
      {weather?.alerts?.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-700">Alertes gaz</h4>
          {weather.alerts.map((alert, i) => (
            <Card key={i} className={`border ${SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.low}`}>
              <CardBody className="py-2.5 flex items-center gap-3">
                <AlertTriangle size={16} className="shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-semibold">{alert.type.replace(/_/g, ' ')}</p>
                  <p className="text-xs mt-0.5">{alert.message}</p>
                </div>
                <Badge status={alert.severity === 'high' ? 'crit' : 'warn'}>{alert.severity}</Badge>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ========================================
// Main Page
// ========================================

export default function ConsumptionExplorerPage() {
  const { selectedSiteId, scopedSites } = useScope();

  // ── UI mode (Classic / Expert) — localStorage only, never in URL ───────
  const { uiMode, isClassic, toggleUiMode } = useExplorerMode();

  // ── URL state (bidirectional sync) ─────────────────────────────────────
  const { urlState, setUrlParams } = useExplorerURL();

  // ── Resolve initial site IDs from URL or scope ─────────────────────────
  const sites = scopedSites || [];
  const initialSiteIds = (() => {
    if (urlState.siteIds.length) return urlState.siteIds;
    if (selectedSiteId) return [selectedSiteId];
    if (sites.length) return [sites[0].id];
    return [];
  })();

  // ── Motor (data engine) ────────────────────────────────────────────────
  const motor = useExplorerMotor({
    initialSiteIds,
    initialEnergy: urlState.energy,
    initialDays: urlState.days,
  });

  const {
    state: { siteIds, energyType, days, mode, unit, layers },
    setSiteIds, setEnergyType, setDays, setMode, setUnit, toggleLayer,
    mergedAvailability,
    primarySiteId,
    primaryAvailability,
    loading,
  } = motor;

  // ── Portfolio mode (V12-A): all sites, aggregated view ────────────────
  const [isPortfolioMode, setIsPortfolioMode] = useState(false);

  const handleTogglePortfolio = useCallback(() => {
    const next = !isPortfolioMode;
    setIsPortfolioMode(next);
    if (next) {
      // Select all available sites when entering portfolio mode
      const allIds = sites.map(s => s.id);
      setSiteIds(allIds);
      setMode('agrege'); // only agrege is valid in portfolio
    } else {
      // Return to single/first site when leaving portfolio
      const firstSiteId = selectedSiteId || (sites.length ? sites[0].id : null);
      setSiteIds(firstSiteId ? [firstSiteId] : []);
    }
  }, [isPortfolioMode, sites, selectedSiteId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Custom date range (V11.1-A) ────────────────────────────────────────
  const [startDate, setStartDate] = useState(urlState.startDate || null);
  const [endDate, setEndDate] = useState(urlState.endDate || null);

  // Sync custom dates → URL
  useEffect(() => {
    setUrlParams({
      start: startDate || null,
      end: endDate || null,
    });
  }, [startDate, endDate]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Sync Motor state → URL ─────────────────────────────────────────────
  useEffect(() => {
    setUrlParams({ sites: siteIds, energy: energyType, days, mode, unit });
  }, [siteIds, energyType, days, mode, unit]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Tab state (persisted in URL) ───────────────────────────────────────
  const [activeTab, setActiveTab] = useState(urlState.tab);
  const switchTab = (tab) => {
    setActiveTab(tab);
    setUrlParams({ tab });
    track('explorer_tab', { tab });
  };

  // ── Auto-calibrate period from availability ────────────────────────────
  useEffect(() => {
    const avail = primaryAvailability;
    if (avail?.has_data && avail.first_ts && avail.last_ts) {
      const autoDays = computeAutoRange(avail.first_ts, avail.last_ts);
      if (autoDays !== days) setDays(autoDays);
    }
    // Auto-switch tab for gas-only
    if (avail?.has_data && energyType === 'gas' && activeTab === 'tunnel') {
      setActiveTab('gas');
    }
  }, [primaryAvailability]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Initialize siteIds when scope resolves ─────────────────────────────
  useEffect(() => {
    if (!siteIds.length && selectedSiteId) {
      setSiteIds([selectedSiteId]);
    } else if (!siteIds.length && sites.length) {
      setSiteIds([sites[0].id]);
    }
  }, [selectedSiteId, sites]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Reset to defaults (V11.1-A) ────────────────────────────────────────
  const handleReset = useCallback(() => {
    const firstSiteId = selectedSiteId || (sites.length ? sites[0].id : null);
    setSiteIds(firstSiteId ? [firstSiteId] : []);
    setEnergyType('electricity');
    setDays(30);
    setMode('agrege');
    setUnit('kwh');
    setStartDate(null);
    setEndDate(null);
    setUrlParams({ sites: firstSiteId ? [firstSiteId] : [], energy: 'electricity', days: 30, mode: 'agrege', unit: 'kwh', start: null, end: null });
  }, [selectedSiteId, sites]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Presets (V11.1-C) ──────────────────────────────────────────────────
  const { presets, savePreset, loadPreset, deletePreset } = useExplorerPresets();

  const handleSavePreset = useCallback((name) => {
    savePreset(name, {
      siteIds,
      energy: energyType,
      days,
      mode,
      unit,
      startDate,
      endDate,
    });
  }, [siteIds, energyType, days, mode, unit, startDate, endDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLoadPreset = useCallback((name) => {
    const state = loadPreset(name);
    if (!state) return;
    if (state.siteIds) setSiteIds(state.siteIds);
    if (state.energy) setEnergyType(state.energy);
    if (state.days) setDays(state.days);
    if (state.mode) setMode(state.mode);
    if (state.unit) setUnit(state.unit);
    if (state.startDate !== undefined) setStartDate(state.startDate);
    if (state.endDate !== undefined) setEndDate(state.endDate);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Navigation helpers ─────────────────────────────────────────────────
  const handleNavigate = useCallback((path) => { window.location.href = path; }, []);
  const handleSwitchEnergy = useCallback((type) => {
    setEnergyType(type);
    if (type === 'gas') switchTab('gas');
    else switchTab('tunnel');
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const availability = mergedAvailability || primaryAvailability;
  const hasData = availability?.has_data === true;
  const showContent = hasData && !loading;
  const siteId = primarySiteId; // backward compat for panels

  return (
    <div className="space-y-5">
      {/* UI Mode toggle — persisted in localStorage, never in URL */}
      <div className="flex justify-end">
        <button
          onClick={toggleUiMode}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition text-gray-600 border-gray-200 bg-white hover:bg-gray-50"
          title={isClassic ? 'Passer en mode Expert (contrôles avancés)' : 'Passer en mode Classique (vue standard)'}
        >
          {isClassic ? '⚙ Mode Expert' : '← Mode Classique'}
        </button>
      </div>

      {/* Unified sticky filter bar */}
      <StickyFilterBar
        uiMode={uiMode}
        siteIds={siteIds}
        setSiteIds={setSiteIds}
        siteId={siteId}
        setSiteId={(id) => setSiteIds([id])}
        sites={sites}
        energyType={energyType}
        setEnergyType={setEnergyType}
        availableTypes={availability?.energy_types}
        days={days}
        setDays={setDays}
        startDate={startDate}
        setStartDate={setStartDate}
        endDate={endDate}
        setEndDate={setEndDate}
        mode={mode}
        setMode={setMode}
        unit={unit}
        setUnit={setUnit}
        availability={availability}
        isPortfolioMode={isPortfolioMode}
        onTogglePortfolio={sites.length > 1 ? handleTogglePortfolio : undefined}
        onReset={handleReset}
        onCopyLink={() => { try { navigator.clipboard.writeText(window.location.href); } catch {} }}
        onSave={handleSavePreset}
        savedPresets={presets}
        onLoadPreset={handleLoadPreset}
        onDeletePreset={deletePreset}
      />

      {/* Context banner (site info + date range) */}
      <ContextBanner availability={availability} />

      {/* Loading skeleton */}
      {loading && <AvailabilitySkeleton />}

      {/* Smart empty state (no data) */}
      {!loading && availability && !hasData && (
        <SmartEmptyState
          reasons={availability.reasons}
          energyTypes={availability.energy_types}
          onNavigate={handleNavigate}
          onSwitchEnergy={handleSwitchEnergy}
        />
      )}

      {/* Portfolio mode — shown instead of tab panels */}
      {isPortfolioMode && (loading || (availability && hasData) || !loading) && (
        <>
          {/* OverviewRow (aggregate) */}
          {motor.primaryTunnel && (
            <OverviewRow
              data={computeOverviewData(motor.primaryTunnel)}
              unit={unit}
            />
          )}
          <PortfolioPanel motor={motor} sites={sites} unit={unit} />
        </>
      )}

      {/* Main content (data available, non-portfolio) */}
      {!isPortfolioMode && showContent && (
        <>
          {/* OverviewRow — KPI summary above tabs */}
          {motor.primaryTunnel && (
            <OverviewRow
              data={computeOverviewData(motor.primaryTunnel)}
              unit={unit}
            />
          )}

          {/* Tab bar */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {TAB_CONFIG.map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              if (tab.key === 'gas' && energyType !== 'gas') return null;
              if ((tab.key === 'hphc' || tab.key === 'tunnel' || tab.key === 'targets') && energyType === 'gas') {
                if (tab.key !== 'gas') return null;
              }
              return (
                <button
                  key={tab.key}
                  onClick={() => switchTab(tab.key)}
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

          {/* InsightsStrip — auto-generated badges from Motor data */}
          <InsightsStrip
            insights={computeInsights({
              primaryTunnel: motor.primaryTunnel,
              primaryHphc: motor.primaryHphc,
              primaryGas: motor.primaryGas,
              primaryWeather: motor.primaryWeather,
              primaryProgression: motor.primaryProgression,
            }, mode, unit)}
          />

          {/* Panel content — panels use primarySiteId for backward compat */}
          <div>
            {activeTab === 'tunnel' && (
              <TunnelPanel
                siteId={siteId}
                days={days}
                energyType={energyType}
                showSignature={layers.signature}
              />
            )}
            {activeTab === 'targets' && <TargetsPanel siteId={siteId} energyType={energyType} />}
            {activeTab === 'hphc' && <HPHCPanel siteId={siteId} days={days} />}
            {activeTab === 'gas' && <GasPanel siteId={siteId} days={days} />}
          </div>
        </>
      )}

      {/* Blocked state: too many sites in comparatif (guard) */}
      {!isPortfolioMode && !loading && siteIds.length > MAX_SITES && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mb-4">
            <BarChart3 size={28} className="text-amber-500" />
          </div>
          <h3 className="text-base font-semibold text-gray-700 mb-1">Trop de sites sélectionnés</h3>
          <p className="text-sm text-gray-500 mb-4 max-w-sm">
            Le mode comparatif supporte jusqu'à {MAX_SITES} sites simultanément.
            Passez en mode Portfolio pour visualiser tous vos sites.
          </p>
          <button
            onClick={handleTogglePortfolio}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
          >
            Passer en mode Portfolio
          </button>
        </div>
      )}
    </div>
  );
}
