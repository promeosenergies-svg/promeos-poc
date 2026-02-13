/**
 * PROMEOS - ConsumptionExplorerPage (/explorer)
 * EMS Consumption Explorer: multi-site timeseries, weather overlay,
 * energy signature, saved views, cap-points guardrail.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  BarChart3, Thermometer, TrendingUp, Save, AlertTriangle,
  RefreshCw, Layers, SplitSquareHorizontal, GitMerge, Calendar,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Brush, Legend,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, PageShell, KpiCard, Select } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import {
  getEmsTimeseries, getEmsWeather, runEmsSignature,
  getEmsViews, createEmsView,
} from '../services/api';

// --- Constants ---

const SERIES_COLORS = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6','#06b6d4','#ec4899','#64748b'];

const GRANULARITY_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: '15min', label: '15 min' },
  { value: '30min', label: '30 min' },
  { value: 'hourly', label: 'Horaire' },
  { value: 'daily', label: 'Jour' },
  { value: 'monthly', label: 'Mois' },
];

const MODE_OPTIONS = [
  { value: 'aggregate', label: 'Agrege', icon: GitMerge },
  { value: 'stack', label: 'Empile', icon: Layers },
  { value: 'split', label: 'Separe', icon: SplitSquareHorizontal },
];

const DATE_PRESETS = [
  { label: '7j', days: 7 },
  { label: '30j', days: 30 },
  { label: '90j', days: 90 },
  { label: '12m', days: 365 },
  { label: 'YTD', days: null },
];

function fmtDate(d) {
  return d.toISOString().split('T')[0];
}

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

function ytdStart() {
  const now = new Date();
  return new Date(now.getFullYear(), 0, 1);
}

// --- Main Page ---

export default function ConsumptionExplorerPage() {
  const { scopedSites, scope } = useScope();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // State: toolbar
  const [selectedSiteIds, setSelectedSiteIds] = useState([]);
  const [dateFrom, setDateFrom] = useState(fmtDate(daysAgo(30)));
  const [dateTo, setDateTo] = useState(fmtDate(new Date()));
  const [granularity, setGranularity] = useState('auto');
  const [mode, setMode] = useState('aggregate');
  const [metric, setMetric] = useState('kwh');
  const [showWeather, setShowWeather] = useState(false);
  const [showSignature, setShowSignature] = useState(false);

  // State: data
  const [tsData, setTsData] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [sigData, setSigData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [capError, setCapError] = useState(null);

  // State: saved views
  const [views, setViews] = useState([]);
  const [saveName, setSaveName] = useState('');

  // Deep-link from query params
  useEffect(() => {
    const siteId = searchParams.get('site_id');
    const df = searchParams.get('date_from');
    const dt = searchParams.get('date_to');
    if (siteId) setSelectedSiteIds([parseInt(siteId)]);
    if (df) setDateFrom(df);
    if (dt) setDateTo(dt);
  }, [searchParams]);

  // Default: first site if none selected
  useEffect(() => {
    if (selectedSiteIds.length === 0 && scopedSites.length > 0) {
      setSelectedSiteIds([scopedSites[0].id]);
    }
  }, [scopedSites, selectedSiteIds.length]);

  // Fetch timeseries
  const fetchData = useCallback(async () => {
    if (selectedSiteIds.length === 0) return;
    setLoading(true);
    setError(null);
    setCapError(null);
    try {
      const result = await getEmsTimeseries({
        site_ids: selectedSiteIds.join(','),
        date_from: dateFrom,
        date_to: dateTo,
        granularity,
        mode,
        metric,
      });
      setTsData(result);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.error === 'too_many_points') {
        setCapError(detail);
        setTsData(null);
      } else {
        setError(err.response?.data?.detail || err.message);
        setTsData(null);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedSiteIds, dateFrom, dateTo, granularity, mode, metric]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch weather overlay
  useEffect(() => {
    if (!showWeather || selectedSiteIds.length !== 1) {
      setWeatherData(null);
      return;
    }
    getEmsWeather(selectedSiteIds[0], dateFrom, dateTo)
      .then(r => setWeatherData(r.days))
      .catch(() => setWeatherData(null));
  }, [showWeather, selectedSiteIds, dateFrom, dateTo]);

  // Fetch signature
  useEffect(() => {
    if (!showSignature || selectedSiteIds.length !== 1) {
      setSigData(null);
      return;
    }
    runEmsSignature(selectedSiteIds[0], dateFrom, dateTo)
      .then(setSigData)
      .catch(() => setSigData(null));
  }, [showSignature, selectedSiteIds, dateFrom, dateTo]);

  // Load saved views
  useEffect(() => {
    getEmsViews().then(setViews).catch(() => {});
  }, []);

  // Handlers
  const applyPreset = (preset) => {
    const end = new Date();
    const start = preset.days ? daysAgo(preset.days) : ytdStart();
    setDateFrom(fmtDate(start));
    setDateTo(fmtDate(end));
  };

  const applySuggestion = () => {
    if (capError?.suggested_granularity) {
      setGranularity(capError.suggested_granularity);
    }
  };

  const handleSaveView = async () => {
    if (!saveName.trim()) return;
    const config = JSON.stringify({
      scope_type: 'site', scope_ids: selectedSiteIds,
      date_from: dateFrom, date_to: dateTo,
      granularity, mode, metric,
      show_weather: showWeather, show_quality: false,
    });
    await createEmsView(saveName, config);
    const updated = await getEmsViews();
    setViews(updated);
    setSaveName('');
  };

  const loadView = (view) => {
    try {
      const cfg = JSON.parse(view.config_json);
      if (cfg.scope_ids) setSelectedSiteIds(cfg.scope_ids);
      if (cfg.date_from) setDateFrom(cfg.date_from);
      if (cfg.date_to) setDateTo(cfg.date_to);
      if (cfg.granularity) setGranularity(cfg.granularity);
      if (cfg.mode) setMode(cfg.mode);
      if (cfg.metric) setMetric(cfg.metric);
      if (cfg.show_weather !== undefined) setShowWeather(cfg.show_weather);
    } catch { /* ignore parse errors */ }
  };

  // Chart data merge (timeseries + weather)
  const chartData = useMemo(() => {
    if (!tsData?.series?.length) return [];
    const main = tsData.series[0].data;
    const weatherMap = {};
    if (weatherData) {
      for (const w of weatherData) {
        weatherMap[w.date] = w.temp_avg_c;
      }
    }
    return main.map((pt, i) => {
      const row = { t: pt.t };
      for (const s of tsData.series) {
        row[s.key] = s.data[i]?.v ?? null;
      }
      const dateKey = pt.t?.slice(0, 10);
      if (dateKey && weatherMap[dateKey] !== undefined) {
        row.temp = weatherMap[dateKey];
      }
      return row;
    });
  }, [tsData, weatherData]);

  // Coverage stats
  const totalPoints = tsData?.series?.reduce((sum, s) => sum + s.data.length, 0) || 0;

  return (
    <PageShell
      title="Explorateur Consommation"
      icon={BarChart3}
      actions={
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={fetchData} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </Button>
        </div>
      }
    >
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {/* Site selector */}
        <select
          className="text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
          value={selectedSiteIds[0] || ''}
          onChange={(e) => {
            const v = parseInt(e.target.value);
            if (v) setSelectedSiteIds([v]);
          }}
        >
          {scopedSites.map(s => (
            <option key={s.id} value={s.id}>{s.nom}</option>
          ))}
        </select>

        {/* Date presets */}
        <div className="flex gap-1">
          {DATE_PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => applyPreset(p)}
              className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-blue-50 hover:border-blue-300 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Custom date range */}
        <div className="flex items-center gap-1">
          <Calendar size={14} className="text-gray-400" />
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
            className="text-xs border border-gray-300 rounded px-1.5 py-1" />
          <span className="text-gray-400 text-xs">-</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
            className="text-xs border border-gray-300 rounded px-1.5 py-1" />
        </div>

        {/* Granularity */}
        <select
          className="text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
          value={granularity}
          onChange={e => setGranularity(e.target.value)}
        >
          {GRANULARITY_OPTIONS.map(g => (
            <option key={g.value} value={g.value}>{g.label}</option>
          ))}
        </select>

        {/* Mode */}
        <div className="flex border border-gray-300 rounded-md overflow-hidden">
          {MODE_OPTIONS.map(m => (
            <button
              key={m.value}
              onClick={() => setMode(m.value)}
              className={`px-2.5 py-1.5 text-xs flex items-center gap-1 transition-colors ${
                mode === m.value ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <m.icon size={12} />
              {m.label}
            </button>
          ))}
        </div>

        {/* Metric toggle */}
        <div className="flex border border-gray-300 rounded-md overflow-hidden">
          {['kwh', 'kw'].map(m => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-2.5 py-1.5 text-xs transition-colors ${
                metric === m ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Weather toggle */}
        <button
          onClick={() => setShowWeather(!showWeather)}
          className={`px-2.5 py-1.5 text-xs rounded-md border flex items-center gap-1 transition-colors ${
            showWeather ? 'bg-orange-100 border-orange-300 text-orange-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          <Thermometer size={12} />
          Meteo
        </button>

        {/* Signature toggle */}
        <button
          onClick={() => setShowSignature(!showSignature)}
          className={`px-2.5 py-1.5 text-xs rounded-md border flex items-center gap-1 transition-colors ${
            showSignature ? 'bg-purple-100 border-purple-300 text-purple-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          <TrendingUp size={12} />
          Signature
        </button>
      </div>

      {/* Cap points error banner */}
      {capError && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
          <AlertTriangle size={18} className="text-amber-600 shrink-0" />
          <div className="flex-1 text-sm">
            <span className="font-medium text-amber-800">Trop de points</span>
            <span className="text-amber-700 ml-1">
              ({capError.estimated?.toLocaleString()} estimes, max {capError.cap?.toLocaleString()}).
            </span>
          </div>
          <Button size="sm" onClick={applySuggestion}>
            Appliquer &laquo;{capError.suggested_granularity}&raquo;
          </Button>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {typeof error === 'string' ? error : JSON.stringify(error)}
        </div>
      )}

      {/* Data coverage badge */}
      {tsData && (
        <div className="flex items-center gap-3 mb-3">
          <Badge status="info">{totalPoints} points</Badge>
          <span className="text-xs text-gray-500">
            {tsData.series?.length || 0} serie(s) &middot; {tsData.meta?.granularity || granularity}
          </span>
        </div>
      )}

      {/* Main chart */}
      {loading ? (
        <div className="h-80 bg-gray-100 rounded-xl animate-pulse flex items-center justify-center text-gray-400">
          Chargement...
        </div>
      ) : tsData && chartData.length > 0 ? (
        <Card className="mb-6">
          <CardBody className="p-2">
            <ResponsiveContainer width="100%" height={380}>
              {mode === 'split' ? (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="t" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10 }} />
                  {showWeather && weatherData && (
                    <YAxis yAxisId="temp" orientation="right" tick={{ fontSize: 10 }} unit="°C" />
                  )}
                  <RTooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {tsData.series.map((s, i) => (
                    <Line
                      key={s.key}
                      dataKey={s.key}
                      name={s.label}
                      stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                      dot={false}
                      strokeWidth={1.5}
                    />
                  ))}
                  {showWeather && weatherData && (
                    <Line yAxisId="temp" dataKey="temp" name="Temp (°C)" stroke="#f97316" dot={false} strokeDasharray="4 2" strokeWidth={1} />
                  )}
                  <Brush dataKey="t" height={25} stroke="#3b82f6" travellerWidth={8} />
                </LineChart>
              ) : (
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="t" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10 }} />
                  {showWeather && weatherData && (
                    <YAxis yAxisId="temp" orientation="right" tick={{ fontSize: 10 }} unit="°C" />
                  )}
                  <RTooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {tsData.series.map((s, i) => (
                    <Area
                      key={s.key}
                      dataKey={s.key}
                      name={s.label}
                      fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                      stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                      fillOpacity={0.3}
                      stackId={mode === 'stack' ? 'stack' : undefined}
                    />
                  ))}
                  {showWeather && weatherData && (
                    <Line yAxisId="temp" dataKey="temp" name="Temp (°C)" stroke="#f97316" dot={false} strokeDasharray="4 2" strokeWidth={1} />
                  )}
                  <Brush dataKey="t" height={25} stroke="#3b82f6" travellerWidth={8} />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </CardBody>
        </Card>
      ) : !capError && !error && !loading ? (
        <EmptyState
          icon={BarChart3}
          title="Aucune donnee"
          description="Selectionnez un site avec des compteurs pour visualiser les consommations."
        />
      ) : null}

      {/* Signature panel */}
      {showSignature && sigData && !sigData.error && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <TrendingUp size={16} /> Signature Energetique
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            <KpiCard label="Talon" value={`${sigData.base_kwh} kWh`} />
            <KpiCard label="R²" value={sigData.r_squared?.toFixed(3)} />
            <KpiCard label="Label" value={sigData.label?.replace('_', ' ')} />
            <KpiCard label="Pente chauffage" value={`${sigData.a_heating} kWh/°C`} />
            <KpiCard label="Pente clim" value={`${sigData.b_cooling} kWh/°C`} />
          </div>

          <Card>
            <CardBody className="p-2">
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="T" name="Temp (°C)" tick={{ fontSize: 10 }} type="number" />
                  <YAxis dataKey="kwh" name="kWh/j" tick={{ fontSize: 10 }} />
                  <RTooltip contentStyle={{ fontSize: 12 }} />
                  <Scatter data={sigData.scatter} fill="#3b82f6" fillOpacity={0.5} />
                  <Scatter data={sigData.fit_line} fill="none" line={{ stroke: '#ef4444', strokeWidth: 2 }} shape={() => null}>
                    {sigData.fit_line.map((_, i) => (
                      <circle key={i} r={0} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        </div>
      )}
      {showSignature && sigData?.error && (
        <div className="mb-6 p-3 bg-gray-50 border rounded-lg text-sm text-gray-600">
          Signature: {sigData.error} ({sigData.n_points} points)
        </div>
      )}

      {/* Saved views */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        {views.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Vues:</span>
            {views.map(v => (
              <button
                key={v.id}
                onClick={() => loadView(v)}
                className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-blue-50 transition-colors"
              >
                {v.name}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-center gap-1 ml-auto">
          <input
            type="text"
            placeholder="Nom de la vue..."
            value={saveName}
            onChange={e => setSaveName(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2 py-1 w-40"
          />
          <Button size="sm" variant="ghost" onClick={handleSaveView} disabled={!saveName.trim()}>
            <Save size={14} />
          </Button>
        </div>
      </div>
    </PageShell>
  );
}
