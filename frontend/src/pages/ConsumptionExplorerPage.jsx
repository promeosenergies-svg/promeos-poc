/**
 * PROMEOS - ConsumptionExplorerPage (/consumption-explorer)
 * Sprint V10: Consommations World-Class (Elec + Gaz)
 * Panels: Tunnel (P10-P90), Objectifs/Budgets, HP/HC, Gaz (beta)
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Target, Clock, Flame, BarChart3, TrendingUp,
  RefreshCw, AlertTriangle, CheckCircle, ChevronDown, ChevronUp,
  Plus, Trash2, Edit3, Save, X,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, LineChart, Line,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, TrustBadge, Skeleton } from '../ui';
import { SkeletonCard } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
import {
  getConsumptionTunnel,
  getConsumptionTargets,
  createConsumptionTarget,
  patchConsumptionTarget,
  deleteConsumptionTarget,
  getTargetsProgression,
  getTOUSchedules,
  getActiveTOUSchedule,
  createTOUSchedule,
  getHPHCRatio,
  getGasSummary,
} from '../services/api';

// ========================================
// Constants
// ========================================

const TAB_CONFIG = [
  { key: 'tunnel', label: 'Tunnel', icon: Activity, desc: 'Enveloppe P10-P90' },
  { key: 'targets', label: 'Objectifs', icon: Target, desc: 'Budgets & progression' },
  { key: 'hphc', label: 'HP/HC', icon: Clock, desc: 'Grille tarifaire' },
  { key: 'gas', label: 'Gaz', icon: Flame, desc: 'Beta' },
];

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

// ========================================
// Tunnel Panel
// ========================================

function TunnelPanel({ siteId }) {
  const [tunnel, setTunnel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(90);
  const [dayType, setDayType] = useState('weekday');

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const data = await getConsumptionTunnel(siteId, days);
      setTunnel(data);
      track('tunnel_loaded', { site_id: siteId, days });
    } catch (e) {
      console.error('Tunnel load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, days]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <SkeletonCard rows={6} />;
  if (!tunnel || tunnel.readings_count === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="Aucune donnee de consommation"
        description="Importez des releves ou generez des donnees demo pour voir l'enveloppe tunnel."
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
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-sm border rounded px-2 py-1"
          >
            <option value={30}>30 jours</option>
            <option value={60}>60 jours</option>
            <option value={90}>90 jours</option>
            <option value={180}>6 mois</option>
            <option value={365}>1 an</option>
          </select>
          <Button size="sm" variant="ghost" onClick={load}>
            <RefreshCw size={14} />
          </Button>
        </div>
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

function TargetsPanel({ siteId }) {
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
        getConsumptionTargets(siteId, 'electricity', year),
        getTargetsProgression(siteId, 'electricity', year),
      ]);
      setTargets(t);
      setProgression(p);
      track('targets_loaded', { site_id: siteId, year });
    } catch (e) {
      console.error('Targets load error:', e);
    } finally {
      setLoading(false);
    }
  }, [siteId, year]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    try {
      await createConsumptionTarget({
        site_id: siteId,
        energy_type: 'electricity',
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

function HPHCPanel({ siteId }) {
  const [ratio, setRatio] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);

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
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="text-sm border rounded px-2 py-1">
          <option value={7}>7 jours</option>
          <option value={30}>30 jours</option>
          <option value={90}>90 jours</option>
        </select>
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
          description="Importez des releves electricite pour voir la repartition HP/HC."
        />
      )}
    </div>
  );
}

// ========================================
// Gas Panel (Beta)
// ========================================

function GasPanel({ siteId }) {
  const [gas, setGas] = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(90);

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
        description="Ajoutez un compteur gaz et importez des releves pour voir le resume."
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
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="text-sm border rounded px-2 py-1">
          <option value={30}>30 jours</option>
          <option value={90}>90 jours</option>
          <option value={180}>6 mois</option>
          <option value={365}>1 an</option>
        </select>
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

  useEffect(() => {
    if (selectedSiteId) {
      setSiteId(selectedSiteId);
    } else if (sites?.length > 0) {
      setSiteId(sites[0].id);
    }
  }, [selectedSiteId, sites]);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Consommations Explorer</h1>
          <p className="text-sm text-gray-500 mt-1">Analyse avancee Electricite & Gaz</p>
        </div>
        {sites?.length > 1 && (
          <select
            value={siteId || ''}
            onChange={(e) => setSiteId(Number(e.target.value))}
            className="text-sm border rounded px-3 py-1.5"
          >
            {sites.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
          </select>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
        {TAB_CONFIG.map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
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
        {activeTab === 'tunnel' && <TunnelPanel siteId={siteId} />}
        {activeTab === 'targets' && <TargetsPanel siteId={siteId} />}
        {activeTab === 'hphc' && <HPHCPanel siteId={siteId} />}
        {activeTab === 'gas' && <GasPanel siteId={siteId} />}
      </div>
    </div>
  );
}
