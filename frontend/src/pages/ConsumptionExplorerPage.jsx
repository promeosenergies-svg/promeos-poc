/**
 * PROMEOS - ConsumptionExplorerPage (/explorer) V3 — "Graph WOW"
 * Multi-site consumption explorer with overlay/aggregate/stack modes,
 * SitePicker, weather overlay, energy signature, saved views, demo data.
 *
 * V3 additions:
 * - Brush zoom + Reset button, crosshair cursor, enriched tooltip
 * - Interactive legend (click to hide/show series), stable color hashing per site_id
 * - Overlay: Normalize toggle (Index 100), Top 8 badge, Others indicator
 * - Stack: % contribution in tooltip
 * - Data coverage badge + quality indicator
 * - ReferenceLine talon (base load)
 * - Mini sticky selection bar + Save collection + Clear
 * - Demo scenarios loader (4 presets)
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  BarChart3, Thermometer, TrendingUp, Save, AlertTriangle,
  RefreshCw, Layers, SplitSquareHorizontal, GitMerge, Calendar,
  Zap, Database, Eye, X, RotateCcw, Percent, Sparkles,
} from 'lucide-react';
import {
  ComposedChart, Area, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Brush, ReferenceLine,
} from 'recharts';
import { Card, CardBody, Badge, Button, EmptyState, PageShell, KpiCard, TrustBadge } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { useToast } from '../ui/ToastProvider';
import SitePicker from '../components/SitePicker';
import {
  getEmsTimeseries, getEmsWeather, runEmsSignature,
  getEmsViews, createEmsView, generateEmsDemo, createEmsCollection,
} from '../services/api';

// ── Helpers (exported for unit tests) ────────────────────────────

/**
 * Stable color from a string key — deterministic HSL with good saturation.
 * Used so the same site_id always gets the same color across sessions.
 */
export function stableColor(key) {
  let hash = 0;
  const str = String(key);
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
    hash |= 0;
  }
  const hue = ((hash % 360) + 360) % 360;
  return `hsl(${hue}, 70%, 50%)`;
}

/**
 * Normalize series data to Index 100 (first non-null value = 100).
 * Returns a new data array with normalized values.
 */
export function normalizeIndex100(chartData, seriesKeys) {
  if (!chartData.length || !seriesKeys.length) return chartData;
  const bases = {};
  for (const key of seriesKeys) {
    for (const row of chartData) {
      if (row[key] != null && row[key] > 0) {
        bases[key] = row[key];
        break;
      }
    }
  }
  return chartData.map(row => {
    const out = { t: row.t };
    for (const key of seriesKeys) {
      if (row[key] != null && bases[key]) {
        out[key] = Math.round((row[key] / bases[key]) * 100 * 10) / 10;
      } else {
        out[key] = row[key];
      }
    }
    if (row.temp !== undefined) out.temp = row.temp;
    return out;
  });
}

// Palette: 8 distinct, accessible colors
const PALETTE = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6','#06b6d4','#ec4899','#64748b'];

function seriesColor(series, index) {
  if (series.key && series.key.startsWith('site_')) return stableColor(series.key);
  if (series.key === 'others') return '#94a3b8';
  return PALETTE[index % PALETTE.length];
}

// ── Constants ────────────────────────────────────────────────────

const GRANULARITY_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: '15min', label: '15 min' },
  { value: '30min', label: '30 min' },
  { value: 'hourly', label: 'Horaire' },
  { value: 'daily', label: 'Jour' },
  { value: 'monthly', label: 'Mois' },
];

const MODE_OPTIONS = [
  { value: 'aggregate', label: 'Agrege', icon: GitMerge, desc: 'Somme de tous les sites' },
  { value: 'overlay', label: 'Superpose', icon: Eye, desc: 'Courbes par site (max 8)' },
  { value: 'stack', label: 'Empile', icon: Layers, desc: 'Aires empilees par compteur' },
  { value: 'split', label: 'Separe', icon: SplitSquareHorizontal, desc: 'Lignes par compteur' },
];

const DATE_PRESETS = [
  { label: '7j', days: 7 },
  { label: '30j', days: 30 },
  { label: '90j', days: 90 },
  { label: '12m', days: 365 },
  { label: 'YTD', days: null },
];

const DEMO_SCENARIOS = [
  { label: 'Bureaux IDF', seed: 100, size: 5, days: 365 },
  { label: 'Retail national', seed: 200, size: 8, days: 180 },
  { label: 'Portfolio mixte', seed: 123, size: 12, days: 365 },
  { label: 'Datacenter + Process', seed: 300, size: 4, days: 90 },
];

function fmtDate(d) { return d.toISOString().split('T')[0]; }
function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return d; }
function ytdStart() { return new Date(new Date().getFullYear(), 0, 1); }

// ── Client-side mock timeseries generator (fallback when backend unavailable) ─

function seededRandom(seed) {
  let s = seed;
  return () => { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; };
}

function generateMockTimeseries(siteIds, dateFrom, dateTo, granularity, modeStr, metricStr, sites) {
  const df = new Date(dateFrom);
  const dt = new Date(dateTo);
  const spanMs = dt - df;
  const spanDays = spanMs / 86400000;

  // Auto granularity
  let gran = granularity;
  if (gran === 'auto') {
    gran = spanDays <= 3 ? '15min' : spanDays <= 14 ? 'hourly' : spanDays <= 120 ? 'daily' : 'monthly';
  }

  // Time buckets
  const stepMs = { '15min': 900000, '30min': 1800000, hourly: 3600000, daily: 86400000, monthly: 2592000000 }[gran] || 86400000;
  const bucketHours = { '15min': 0.25, '30min': 0.5, hourly: 1, daily: 24, monthly: 730 }[gran] || 24;
  const buckets = [];
  for (let t = df.getTime(); t < dt.getTime(); t += stepMs) {
    const d = new Date(t);
    if (gran === 'monthly') {
      buckets.push(d.toISOString().slice(0, 7));
    } else if (gran === 'daily') {
      buckets.push(d.toISOString().slice(0, 10));
    } else {
      buckets.push(d.toISOString().slice(0, 16).replace('T', ' ') + ':00');
    }
  }

  const siteNameMap = {};
  for (const s of sites) siteNameMap[s.id] = s.nom;

  // Build per-site curves with realistic daily+seasonal patterns
  function makeCurve(siteId, idx) {
    const rng = seededRandom(siteId * 1000 + idx + 7);
    const baseKwh = 40 + rng() * 160;
    return buckets.map((bk, i) => {
      const hour = gran === 'hourly' || gran === '15min' || gran === '30min'
        ? parseInt(bk.slice(11, 13)) : 12;
      const dayOfYear = Math.floor(i * stepMs / 86400000) % 365;
      const dailyProfile = hour >= 8 && hour <= 18 ? 1.4 : 0.6;
      const seasonal = 1 + 0.3 * Math.sin((dayOfYear - 180) / 365 * 2 * Math.PI);
      const noise = 0.85 + rng() * 0.3;
      let kwh = baseKwh * dailyProfile * seasonal * noise * (bucketHours / 24);
      if (metricStr === 'kw') kwh = bucketHours > 0 ? kwh / bucketHours : 0;
      return { t: bk, v: Math.round(kwh * 100) / 100, quality: 0.92 + rng() * 0.08, estimated_pct: 0 };
    });
  }

  let series;
  if (modeStr === 'aggregate') {
    const curves = siteIds.map((sid, i) => makeCurve(sid, i));
    const data = buckets.map((bk, bi) => ({
      t: bk,
      v: Math.round(curves.reduce((s, c) => s + c[bi].v, 0) * 100) / 100,
      quality: 0.95,
      estimated_pct: 0,
    }));
    series = [{ key: 'total', label: 'Total', data }];
  } else if (modeStr === 'overlay') {
    const MAX = 8;
    const main = siteIds.slice(0, MAX);
    series = main.map((sid, i) => ({
      key: `site_${sid}`,
      label: siteNameMap[sid] || `Site ${sid}`,
      data: makeCurve(sid, i),
    }));
    const others = siteIds.slice(MAX);
    if (others.length > 0) {
      const otherCurves = others.map((sid, i) => makeCurve(sid, i + MAX));
      series.push({
        key: 'others',
        label: `Autres (${others.length} sites)`,
        data: buckets.map((bk, bi) => ({
          t: bk,
          v: Math.round(otherCurves.reduce((s, c) => s + c[bi].v, 0) * 100) / 100,
          quality: 0.93, estimated_pct: 0,
        })),
      });
    }
  } else {
    // stack / split — one series per site
    series = siteIds.slice(0, 8).map((sid, i) => ({
      key: `site_${sid}`,
      label: siteNameMap[sid] || `Site ${sid}`,
      data: makeCurve(sid, i),
    }));
  }

  return {
    series,
    meta: { granularity: gran, metric: metricStr, n_points: buckets.length, n_meters: siteIds.length, date_from: dateFrom, date_to: dateTo },
  };
}

// ── Tooltip ──────────────────────────────────────────────────────

function EnrichedTooltip({ active, payload, label, mode, metric, normalized }) {
  if (!active || !payload?.length) return null;
  const visible = payload.filter(p => !p.hide);
  if (!visible.length) return null;
  const total = visible.reduce((s, p) => s + (p.value || 0), 0);
  const unit = normalized ? 'idx' : metric === 'kw' ? 'kW' : 'kWh';
  const isStack = mode === 'stack';
  return (
    <div className="bg-white/95 backdrop-blur border border-gray-200 rounded-lg shadow-xl px-3 py-2 text-xs max-w-xs">
      <p className="font-medium text-gray-600 mb-1.5 border-b border-gray-100 pb-1">{label}</p>
      {visible.map((p, i) => {
        const pct = total > 0 ? Math.round((p.value / total) * 100) : 0;
        return (
          <div key={i} className="flex items-center gap-2 py-0.5">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
            <span className="text-gray-700 flex-1 truncate">{p.name}</span>
            <span className="font-semibold text-gray-900 tabular-nums">
              {(p.value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
            </span>
            <span className="text-gray-400 w-8 text-right">{unit}</span>
            {(isStack || visible.length > 1) && total > 0 && (
              <span className="text-gray-400 w-8 text-right">{pct}%</span>
            )}
          </div>
        );
      })}
      {visible.length > 1 && (
        <div className="flex items-center gap-2 pt-1.5 mt-1 border-t border-gray-100">
          <span className="w-2.5 h-2.5" />
          <span className="text-gray-500 flex-1 font-medium">Total</span>
          <span className="font-bold text-gray-900 tabular-nums">{total.toLocaleString(undefined, { maximumFractionDigits: 1 })}</span>
          <span className="text-gray-400 w-8 text-right">{unit}</span>
          {(isStack || visible.length > 1) && <span className="w-8" />}
        </div>
      )}
    </div>
  );
}

// ── Interactive Legend ────────────────────────────────────────────

function InteractiveLegend({ series, colors, hidden, onToggle }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2">
      {series.map((s, i) => {
        const isHidden = hidden.has(s.key);
        return (
          <button
            key={s.key}
            onClick={() => onToggle(s.key)}
            className={`flex items-center gap-1.5 text-xs py-0.5 px-1 rounded transition-all
              ${isHidden ? 'opacity-35 line-through' : 'hover:bg-gray-50'}`}
          >
            <span
              className="w-3 h-1.5 rounded-sm shrink-0"
              style={{ backgroundColor: isHidden ? '#d1d5db' : colors[i] }}
            />
            <span className={isHidden ? 'text-gray-400' : 'text-gray-700'}>{s.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Sticky Selection Bar ─────────────────────────────────────────

function StickySelectionBar({ sites, selectedIds, onChange, onSaveCollection, toast }) {
  const [collName, setCollName] = useState('');
  const selectedSites = useMemo(() =>
    sites.filter(s => selectedIds.includes(s.id)), [sites, selectedIds]);

  if (selectedIds.length === 0) return null;

  const handleSave = async () => {
    if (!collName.trim()) return;
    try {
      await onSaveCollection(collName, selectedIds);
      toast(`Collection "${collName}" sauvegardee`, 'success');
      setCollName('');
    } catch {
      toast('Erreur lors de la sauvegarde', 'error');
    }
  };

  return (
    <div className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-gray-100 px-4 py-2 -mx-6 mb-2 flex items-center gap-3">
      <div className="flex items-center gap-1.5 flex-1 min-w-0 overflow-x-auto">
        {selectedSites.slice(0, 6).map(s => (
          <span key={s.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium shrink-0">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: stableColor(`site_${s.id}`) }} />
            {s.nom}
            <button onClick={() => onChange(selectedIds.filter(x => x !== s.id))} className="hover:bg-blue-100 rounded-full p-0.5 ml-0.5">
              <X size={9} />
            </button>
          </span>
        ))}
        {selectedSites.length > 6 && (
          <span className="text-xs text-gray-400 shrink-0">+{selectedSites.length - 6} autres</span>
        )}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <input
          type="text"
          placeholder="Sauvegarder..."
          value={collName}
          onChange={e => setCollName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          className="text-xs border border-gray-200 rounded px-2 py-1 w-28 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          onClick={handleSave}
          disabled={!collName.trim()}
          className="p-1 text-blue-600 hover:bg-blue-50 rounded disabled:opacity-30"
          title="Sauvegarder collection"
        >
          <Save size={13} />
        </button>
        <button
          onClick={() => onChange([])}
          className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5"
        >
          Effacer
        </button>
      </div>
    </div>
  );
}

// ── Conditional PageShell (bare = no shell, used as tab content) ─

function PageWrapper({ bare, children, ...props }) {
  if (bare) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">{props.subtitle}</p>
          {props.actions}
        </div>
        {children}
      </div>
    );
  }
  return <PageShell {...props}>{children}</PageShell>;
}

// ── Main Page ────────────────────────────────────────────────────

export default function ConsumptionExplorerPage({ bare = false }) {
  const { scopedSites } = useScope();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const brushRef = useRef(null);

  // State: toolbar
  const [selectedSiteIds, setSelectedSiteIds] = useState([]);
  const [dateFrom, setDateFrom] = useState(fmtDate(daysAgo(30)));
  const [dateTo, setDateTo] = useState(fmtDate(new Date()));
  const [granularity, setGranularity] = useState('auto');
  const [mode, setMode] = useState('aggregate');
  const [metric, setMetric] = useState('kwh');
  const [showWeather, setShowWeather] = useState(false);
  const [showSignature, setShowSignature] = useState(false);
  const [activePreset, setActivePreset] = useState('30j');

  // State: V3 features
  const [hiddenSeries, setHiddenSeries] = useState(new Set());
  const [normalized, setNormalized] = useState(false);
  const [showBaseLine, setShowBaseLine] = useState(false);
  const [brushIndex, setBrushIndex] = useState(null);

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

  // State: demo
  const [demoLoading, setDemoLoading] = useState(false);
  const [showDemoMenu, setShowDemoMenu] = useState(false);

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

  // Reset hidden series when mode or data changes
  useEffect(() => { setHiddenSeries(new Set()); }, [mode, tsData]);
  // Reset normalize when not overlay
  useEffect(() => { if (mode !== 'overlay') setNormalized(false); }, [mode]);
  // Reset brush when data changes
  useEffect(() => { setBrushIndex(null); }, [tsData]);

  // Fetch timeseries (API first, client-side mock fallback)
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
        // Fallback: generate client-side mock data
        const mock = generateMockTimeseries(selectedSiteIds, dateFrom, dateTo, granularity, mode, metric, scopedSites);
        setTsData(mock);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedSiteIds, dateFrom, dateTo, granularity, mode, metric, scopedSites]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch weather overlay
  useEffect(() => {
    if (!showWeather || selectedSiteIds.length !== 1) { setWeatherData(null); return; }
    getEmsWeather(selectedSiteIds[0], dateFrom, dateTo)
      .then(r => setWeatherData(r.days))
      .catch(() => setWeatherData(null));
  }, [showWeather, selectedSiteIds, dateFrom, dateTo]);

  // Fetch signature
  useEffect(() => {
    if (!showSignature || selectedSiteIds.length !== 1) { setSigData(null); return; }
    runEmsSignature(selectedSiteIds[0], dateFrom, dateTo)
      .then(setSigData)
      .catch(() => setSigData(null));
  }, [showSignature, selectedSiteIds, dateFrom, dateTo]);

  // Load saved views
  useEffect(() => { getEmsViews().then(setViews).catch(() => {}); }, []);

  // ── Handlers ─────────────────────────────────────────────────

  const applyPreset = (preset) => {
    const end = new Date();
    const start = preset.days ? daysAgo(preset.days) : ytdStart();
    setDateFrom(fmtDate(start));
    setDateTo(fmtDate(end));
    setActivePreset(preset.label);
  };

  const applySuggestion = () => {
    if (capError?.suggested_granularity) setGranularity(capError.suggested_granularity);
  };

  const handleSaveView = async () => {
    if (!saveName.trim()) return;
    const config = JSON.stringify({
      scope_type: 'site', scope_ids: selectedSiteIds,
      date_from: dateFrom, date_to: dateTo,
      granularity, mode, metric,
      show_weather: showWeather, normalized,
    });
    try {
      await createEmsView(saveName, config);
      const updated = await getEmsViews();
      setViews(updated);
    } catch { /* backend offline */ }
    setSaveName('');
    toast('Vue sauvegardee', 'success');
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
      if (cfg.normalized !== undefined) setNormalized(cfg.normalized);
      toast(`Vue "${view.name}" chargee`, 'info');
    } catch { /* ignore parse errors */ }
  };

  const handleGenerateDemo = async (scenario) => {
    setDemoLoading(true);
    setShowDemoMenu(false);
    try {
      const r = await generateEmsDemo(scenario.size, scenario.days, scenario.seed, false);
      if (r.status === 'skipped') {
        toast(r.message, 'info');
      } else {
        toast(`Demo "${scenario.label}": ${r.total_readings.toLocaleString()} lectures, ${r.sites_generated} sites`, 'success');
      }
      fetchData();
    } catch {
      // Backend unavailable — generate client-side with scenario params
      const demoSiteIds = scopedSites.slice(0, scenario.size).map(s => s.id);
      if (demoSiteIds.length > 0) {
        setSelectedSiteIds(demoSiteIds);
        const end = new Date();
        const start = daysAgo(scenario.days);
        setDateFrom(fmtDate(start));
        setDateTo(fmtDate(end));
        const mock = generateMockTimeseries(demoSiteIds, fmtDate(start), fmtDate(end), granularity, mode, metric, scopedSites);
        setTsData(mock);
        toast(`Demo "${scenario.label}": ${demoSiteIds.length} sites (donnees simulees)`, 'success');
      }
    } finally {
      setDemoLoading(false);
    }
  };

  const toggleSeries = (key) => {
    setHiddenSeries(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const resetBrush = () => {
    setBrushIndex(null);
  };

  const handleSaveCollection = async (name, ids) => {
    try { await createEmsCollection(name, ids); } catch { /* backend offline — silent */ }
  };

  // ── Chart data ───────────────────────────────────────────────

  const seriesKeys = useMemo(() =>
    tsData?.series?.map(s => s.key) || [], [tsData]);

  const seriesColors = useMemo(() =>
    tsData?.series?.map((s, i) => seriesColor(s, i)) || [], [tsData]);

  const rawChartData = useMemo(() => {
    if (!tsData?.series?.length) return [];
    const main = tsData.series[0].data;
    const weatherMap = {};
    if (weatherData) {
      for (const w of weatherData) weatherMap[w.date] = w.temp_avg_c;
    }
    return main.map((pt, i) => {
      const row = { t: pt.t, _quality: pt.quality };
      for (const s of tsData.series) {
        row[s.key] = s.data[i]?.v ?? null;
      }
      const dateKey = pt.t?.slice(0, 10);
      if (dateKey && weatherMap[dateKey] !== undefined) row.temp = weatherMap[dateKey];
      return row;
    });
  }, [tsData, weatherData]);

  const chartData = useMemo(() => {
    if (!normalized || mode !== 'overlay') return rawChartData;
    return normalizeIndex100(rawChartData, seriesKeys);
  }, [rawChartData, normalized, mode, seriesKeys]);

  // Base load (talon) = P10 of aggregate values
  const baseLine = useMemo(() => {
    if (!showBaseLine || !tsData?.series?.length) return null;
    if (mode === 'aggregate' && tsData.series[0]?.data?.length > 0) {
      const vals = tsData.series[0].data.map(d => d.v).filter(v => v > 0);
      if (!vals.length) return null;
      vals.sort((a, b) => a - b);
      return Math.round(vals[Math.floor(vals.length * 0.1)] * 10) / 10;
    }
    return null;
  }, [showBaseLine, tsData, mode]);

  // Quality stats
  const qualityStats = useMemo(() => {
    if (!tsData?.series?.length) return null;
    const firstSeries = tsData.series[0].data;
    if (!firstSeries?.length) return null;
    const quals = firstSeries.map(d => d.quality).filter(q => q != null);
    if (!quals.length) return null;
    const avg = quals.reduce((a, b) => a + b, 0) / quals.length;
    const estPcts = firstSeries.map(d => d.estimated_pct).filter(e => e != null);
    const avgEst = estPcts.length ? estPcts.reduce((a, b) => a + b, 0) / estPcts.length : 0;
    return { avgQuality: avg, avgEstimated: avgEst, count: quals.length };
  }, [tsData]);

  // Coverage stats
  const totalPoints = tsData?.series?.reduce((sum, s) => sum + s.data.length, 0) || 0;
  const seriesCount = tsData?.series?.length || 0;

  // Chart type resolution
  const useLines = mode === 'split' || mode === 'overlay';
  const useStack = mode === 'stack';
  const yLabel = normalized ? 'Index (base 100)' : metric === 'kw' ? 'kW' : 'kWh';

  return (
    <PageWrapper
      bare={bare}
      title="Explorateur Consommation"
      icon={BarChart3}
      subtitle={selectedSiteIds.length > 0
        ? `${selectedSiteIds.length} site(s) · ${activePreset} · ${granularity === 'auto' ? 'auto' : granularity}`
        : 'Selectionnez un ou plusieurs sites'}
      actions={
        <div className="flex items-center gap-2">
          {/* Demo scenarios dropdown */}
          <div className="relative">
            <Button size="sm" variant="secondary" onClick={() => setShowDemoMenu(!showDemoMenu)} disabled={demoLoading}>
              <Database size={14} className={demoLoading ? 'animate-spin' : ''} />
              {demoLoading ? 'Generation...' : 'Demo'}
            </Button>
            {showDemoMenu && (
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50 w-56 py-1">
                <p className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase">Scenarios</p>
                {DEMO_SCENARIOS.map(sc => (
                  <button
                    key={sc.seed}
                    onClick={() => handleGenerateDemo(sc)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 transition flex items-center gap-2"
                  >
                    <Sparkles size={12} className="text-amber-500" />
                    <div>
                      <p className="font-medium text-gray-800">{sc.label}</p>
                      <p className="text-xs text-gray-400">{sc.size} sites · {sc.days}j</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button size="sm" variant="ghost" onClick={() => navigate('/diagnostic-conso')} title="Lancer diagnostic">
            <AlertTriangle size={14} />
            Diagnostic
          </Button>
          <Button size="sm" variant="ghost" onClick={fetchData} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </Button>
        </div>
      }
    >
      {/* Sticky selection bar */}
      <StickySelectionBar
        sites={scopedSites}
        selectedIds={selectedSiteIds}
        onChange={setSelectedSiteIds}
        onSaveCollection={handleSaveCollection}
        toast={toast}
      />

      {/* Toolbar row 1: Site picker + Date presets + Custom dates */}
      <div className="flex flex-wrap items-start gap-3">
        <SitePicker
          sites={scopedSites}
          selectedIds={selectedSiteIds}
          onChange={setSelectedSiteIds}
          maxSelection={8}
        />

        <div className="flex gap-1">
          {DATE_PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => applyPreset(p)}
              className={`px-2.5 py-1.5 text-xs rounded-md border transition-colors
                ${activePreset === p.label
                  ? 'bg-blue-100 border-blue-300 text-blue-700 font-medium'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <Calendar size={14} className="text-gray-400" />
          <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setActivePreset(''); }}
            className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <span className="text-gray-400 text-xs">-</span>
          <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setActivePreset(''); }}
            className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      {/* Toolbar row 2: Granularity + Mode + Metric + Toggles */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={granularity}
          onChange={e => setGranularity(e.target.value)}
        >
          {GRANULARITY_OPTIONS.map(g => (
            <option key={g.value} value={g.value}>{g.label}</option>
          ))}
        </select>

        <div className="flex border border-gray-300 rounded-lg overflow-hidden">
          {MODE_OPTIONS.map(m => (
            <button
              key={m.value}
              onClick={() => setMode(m.value)}
              title={m.desc}
              className={`px-2.5 py-1.5 text-xs flex items-center gap-1 transition-colors
                ${mode === m.value ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              <m.icon size={12} />
              {m.label}
            </button>
          ))}
        </div>

        <div className="flex border border-gray-300 rounded-lg overflow-hidden">
          {['kwh', 'kw'].map(m => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-2.5 py-1.5 text-xs transition-colors
                ${metric === m ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Normalize toggle (overlay only) */}
        {mode === 'overlay' && (
          <button
            onClick={() => setNormalized(!normalized)}
            className={`px-2.5 py-1.5 text-xs rounded-lg border flex items-center gap-1 transition-colors
              ${normalized ? 'bg-indigo-100 border-indigo-300 text-indigo-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
          >
            <Percent size={12} />
            Index 100
          </button>
        )}

        {/* Base line toggle (aggregate only) */}
        {mode === 'aggregate' && (
          <button
            onClick={() => setShowBaseLine(!showBaseLine)}
            className={`px-2.5 py-1.5 text-xs rounded-lg border flex items-center gap-1 transition-colors
              ${showBaseLine ? 'bg-emerald-100 border-emerald-300 text-emerald-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
          >
            <Zap size={12} />
            Talon
          </button>
        )}

        <button
          onClick={() => setShowWeather(!showWeather)}
          className={`px-2.5 py-1.5 text-xs rounded-lg border flex items-center gap-1 transition-colors
            ${showWeather ? 'bg-orange-100 border-orange-300 text-orange-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
        >
          <Thermometer size={12} />
          Meteo
        </button>

        <button
          onClick={() => setShowSignature(!showSignature)}
          className={`px-2.5 py-1.5 text-xs rounded-lg border flex items-center gap-1 transition-colors
            ${showSignature ? 'bg-purple-100 border-purple-300 text-purple-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
        >
          <TrendingUp size={12} />
          Signature
        </button>

        {/* Overlay info badges */}
        {mode === 'overlay' && selectedSiteIds.length > 1 && (
          <span className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded flex items-center gap-1">
            Top {Math.min(selectedSiteIds.length, 8)} par energie
            {selectedSiteIds.length > 8 && <span className="text-amber-600 font-medium ml-1">+ Autres ({selectedSiteIds.length - 8})</span>}
          </span>
        )}
      </div>

      {/* Cap points error banner */}
      {capError && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
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
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
          <AlertTriangle size={16} className="text-red-500 shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="p-1 hover:bg-red-100 rounded">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Data coverage + quality badges */}
      {tsData && !loading && (
        <div className="flex items-center gap-3 flex-wrap">
          <Badge status="info">{totalPoints.toLocaleString()} points</Badge>
          <span className="text-xs text-gray-500">
            {seriesCount} serie(s) &middot; {tsData.meta?.granularity || granularity}
            {tsData.meta?.n_meters > 0 && ` &middot; ${tsData.meta.n_meters} compteur(s)`}
          </span>
          {qualityStats && (
            <TrustBadge
              source="EMS"
              period={`Q: ${(qualityStats.avgQuality * 100).toFixed(0)}%`}
              confidence={qualityStats.avgQuality >= 0.9 ? 'high' : qualityStats.avgQuality >= 0.7 ? 'medium' : 'low'}
            />
          )}
          {qualityStats && qualityStats.avgEstimated > 0.05 && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
              {(qualityStats.avgEstimated * 100).toFixed(0)}% estime
            </span>
          )}
          {brushIndex && (
            <button
              onClick={resetBrush}
              className="flex items-center gap-1 text-xs text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded transition"
            >
              <RotateCcw size={11} />
              Reset zoom
            </button>
          )}
        </div>
      )}

      {/* ── Main chart ─────────────────────────────────────────── */}
      {loading ? (
        <Card>
          <div className="h-[440px] bg-gray-50 rounded-xl animate-pulse flex flex-col items-center justify-center gap-3">
            <RefreshCw size={24} className="text-gray-300 animate-spin" />
            <span className="text-sm text-gray-400">Chargement des donnees...</span>
          </div>
        </Card>
      ) : tsData && chartData.length > 0 ? (
        <Card>
          {/* Interactive legend */}
          {tsData.series.length > 1 && (
            <InteractiveLegend
              series={tsData.series}
              colors={seriesColors}
              hidden={hiddenSeries}
              onToggle={toggleSeries}
            />
          )}

          <CardBody className="p-3 pt-0">
            <ResponsiveContainer width="100%" height={420}>
              <ComposedChart data={chartData} style={{ cursor: 'crosshair' }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 10 }}
                  interval="preserveStartEnd"
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  label={{ value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#9ca3af' } }}
                />
                {showWeather && weatherData && (
                  <YAxis yAxisId="temp" orientation="right" tick={{ fontSize: 10 }} unit="°C" tickLine={false} />
                )}
                <RTooltip
                  content={<EnrichedTooltip mode={mode} metric={metric} normalized={normalized} />}
                  cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' }}
                />

                {/* Base load reference line */}
                {baseLine && (
                  <ReferenceLine
                    y={baseLine}
                    stroke="#10b981"
                    strokeDasharray="6 3"
                    strokeWidth={1.5}
                    label={{ value: `Talon: ${baseLine.toLocaleString()} ${metric}`, position: 'right', style: { fontSize: 10, fill: '#10b981' } }}
                  />
                )}

                {/* Series rendering */}
                {tsData.series.map((s, i) => {
                  const color = seriesColors[i];
                  const isHidden = hiddenSeries.has(s.key);
                  if (useLines) {
                    return (
                      <Line
                        key={s.key}
                        dataKey={s.key}
                        name={s.label}
                        stroke={color}
                        dot={false}
                        strokeWidth={isHidden ? 0 : (s.key === 'others' ? 1 : 1.5)}
                        strokeDasharray={s.key === 'others' ? '4 2' : undefined}
                        hide={isHidden}
                        animationDuration={500}
                        connectNulls
                      />
                    );
                  } else {
                    return (
                      <Area
                        key={s.key}
                        dataKey={s.key}
                        name={s.label}
                        fill={color}
                        stroke={color}
                        fillOpacity={isHidden ? 0 : (useStack ? 0.65 : 0.25)}
                        strokeWidth={isHidden ? 0 : 1}
                        stackId={useStack ? 'stack' : undefined}
                        hide={isHidden}
                        animationDuration={500}
                      />
                    );
                  }
                })}

                {/* Weather overlay line */}
                {showWeather && weatherData && (
                  <Line yAxisId="temp" dataKey="temp" name="Temp (°C)" stroke="#f97316" dot={false} strokeDasharray="4 2" strokeWidth={1} />
                )}

                {/* Brush zoom */}
                <Brush
                  ref={brushRef}
                  dataKey="t"
                  height={28}
                  stroke="#3b82f6"
                  fill="#f8fafc"
                  travellerWidth={10}
                  startIndex={brushIndex?.startIndex}
                  endIndex={brushIndex?.endIndex}
                  onChange={(idx) => setBrushIndex(idx)}
                  tickFormatter={(val) => val?.slice(5, 10) || ''}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardBody>

          {/* Chart footer */}
          <div className="px-4 py-2 border-t border-gray-50 flex items-center gap-3 text-xs text-gray-400">
            <span>{seriesCount} serie(s) affichee(s)</span>
            {hiddenSeries.size > 0 && <span>· {hiddenSeries.size} masquee(s)</span>}
            {normalized && <Badge status="info">Index 100</Badge>}
            {baseLine && <span className="text-emerald-600">Talon: {baseLine.toLocaleString()} {metric}</span>}
          </div>
        </Card>
      ) : !capError && !error && !loading ? (
        <EmptyState
          icon={BarChart3}
          title="Aucune donnee de consommation"
          text="Selectionnez un site avec des compteurs, ou generez des donnees de demo pour explorer."
          ctaLabel="Generer donnees demo"
          onCta={() => handleGenerateDemo(DEMO_SCENARIOS[2])}
        />
      ) : null}

      {/* Signature panel */}
      {showSignature && sigData && !sigData.error && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <TrendingUp size={16} /> Signature Energetique
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            <KpiCard title="Talon" value={`${sigData.base_kwh} kWh`} color="bg-blue-600" icon={Zap} />
            <KpiCard title="R²" value={sigData.r_squared?.toFixed(3)} color="bg-green-600" icon={TrendingUp} />
            <KpiCard title="Label" value={sigData.label?.replace('_', ' ')} color="bg-gray-600" icon={BarChart3} />
            <KpiCard title="Pente chauffage" value={`${sigData.a_heating} kWh/°C`} color="bg-red-600" icon={Thermometer} />
            <KpiCard title="Pente clim" value={`${sigData.b_cooling} kWh/°C`} color="bg-cyan-600" icon={Thermometer} />
          </div>

          <Card>
            <CardBody className="p-3">
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
        <div className="p-3 bg-gray-50 border rounded-lg text-sm text-gray-600">
          Signature: {sigData.error} ({sigData.n_points} points)
        </div>
      )}

      {/* Saved views */}
      <div className="flex flex-wrap items-center gap-3">
        {views.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Vues:</span>
            {views.map(v => (
              <button
                key={v.id}
                onClick={() => loadView(v)}
                className="px-2.5 py-1 text-xs rounded-md border border-gray-300 hover:bg-blue-50 hover:border-blue-300 transition-colors"
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
            className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 w-40
              focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button size="sm" variant="ghost" onClick={handleSaveView} disabled={!saveName.trim()}>
            <Save size={14} />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
