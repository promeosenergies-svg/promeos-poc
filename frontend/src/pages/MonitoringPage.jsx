import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, Zap, BarChart3, CheckCircle, Clock, Shield, TrendingUp } from 'lucide-react';

const API = 'http://localhost:8000/api/monitoring';

function MonitoringPage() {
  const [kpis, setKpis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSite, setSelectedSite] = useState(1);
  const [runResult, setRunResult] = useState(null);

  useEffect(() => {
    loadAlerts();
    loadSnapshots();
    loadKpis();
  }, [selectedSite]);

  const loadKpis = async () => {
    try {
      const res = await fetch(`${API}/kpis?site_id=${selectedSite}`);
      if (res.ok) setKpis(await res.json());
      else setKpis(null);
    } catch { setKpis(null); }
  };

  const loadAlerts = async () => {
    try {
      const res = await fetch(`${API}/alerts?site_id=${selectedSite}&limit=50`);
      if (res.ok) setAlerts(await res.json());
    } catch { /* ignore */ }
  };

  const loadSnapshots = async () => {
    try {
      const res = await fetch(`${API}/snapshots?site_id=${selectedSite}&limit=10`);
      if (res.ok) setSnapshots(await res.json());
    } catch { /* ignore */ }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site_id: selectedSite, days: 90 })
      });
      const data = await res.json();
      if (res.ok) {
        setRunResult(data);
        loadKpis();
        loadAlerts();
        loadSnapshots();
      } else {
        setError(data.detail || 'Analysis failed');
      }
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const ackAlert = async (id) => {
    await fetch(`${API}/alerts/${id}/ack`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: 'user' })
    });
    loadAlerts();
  };

  const resolveAlert = async (id) => {
    await fetch(`${API}/alerts/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolved_by: 'user', resolution_note: 'Resolved from UI' })
    });
    loadAlerts();
  };

  const severityColor = (sev) => {
    const map = { critical: 'red', high: 'orange', warning: 'yellow', info: 'blue' };
    return map[sev] || 'gray';
  };

  const severityBg = (sev) => {
    const map = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      info: 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return map[sev] || 'bg-gray-100 text-gray-800';
  };

  const statusBadge = (status) => {
    const map = {
      open: 'bg-red-500 text-white',
      ack: 'bg-yellow-500 text-white',
      resolved: 'bg-green-500 text-white'
    };
    return map[status] || 'bg-gray-500 text-white';
  };

  const scoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const riskColor = (score) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-orange-600';
    if (score >= 35) return 'text-yellow-600';
    return 'text-green-600';
  };

  const kpiData = kpis?.kpis || runResult?.kpis || {};
  const qualityScore = kpis?.data_quality_score ?? runResult?.data_quality?.quality_score ?? null;
  const riskScore = kpis?.risk_power_score ?? runResult?.power_risk?.risk_score ?? null;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Activity size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Performance</h1>
          <p className="text-sm text-gray-500 mt-0.5">KPIs, puissance, qualité de données & alertes</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border rounded px-3 py-2 text-sm"
            value={selectedSite}
            onChange={(e) => setSelectedSite(Number(e.target.value))}
          >
            {[1,2,3,4,5].map(i => (
              <option key={i} value={i}>Site {i}</option>
            ))}
          </select>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {loading ? 'Analyse...' : 'Lancer Analyse'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm">{error}</div>
      )}

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={18} className="text-yellow-500" />
            <span className="text-sm text-gray-500">Pmax</span>
          </div>
          <p className="text-2xl font-bold">{kpiData.pmax_kw ?? '-'} <span className="text-sm font-normal text-gray-400">kW</span></p>
          <p className="text-xs text-gray-400 mt-1">P95: {kpiData.p95_kw ?? '-'} kW | P99: {kpiData.p99_kw ?? '-'} kW</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={18} className="text-blue-500" />
            <span className="text-sm text-gray-500">Load Factor</span>
          </div>
          <p className="text-2xl font-bold">{kpiData.load_factor ? (kpiData.load_factor * 100).toFixed(1) : '-'}<span className="text-sm font-normal text-gray-400">%</span></p>
          <p className="text-xs text-gray-400 mt-1">Peak/Avg: {kpiData.peak_to_average ?? '-'}x</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center gap-2 mb-2">
            <Shield size={18} className={riskScore !== null ? riskColor(riskScore) : 'text-gray-400'} />
            <span className="text-sm text-gray-500">Risque Puissance</span>
          </div>
          <p className={`text-2xl font-bold ${riskScore !== null ? riskColor(riskScore) : ''}`}>
            {riskScore !== null ? riskScore : '-'}<span className="text-sm font-normal text-gray-400">/100</span>
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={18} className={qualityScore !== null ? scoreColor(qualityScore) : 'text-gray-400'} />
            <span className="text-sm text-gray-500">Qualite Donnees</span>
          </div>
          <p className={`text-2xl font-bold ${qualityScore !== null ? scoreColor(qualityScore) : ''}`}>
            {qualityScore !== null ? qualityScore : '-'}<span className="text-sm font-normal text-gray-400">/100</span>
          </p>
        </div>
      </div>

      {/* KPI Details + Power Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* KPI Details */}
        <div className="bg-white rounded-lg shadow p-5">
          <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <TrendingUp size={18} /> KPIs Detailles
          </h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Pmean</span><span className="font-medium">{kpiData.pmean_kw ?? '-'} kW</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Pbase (talon)</span><span className="font-medium">{kpiData.pbase_kw ?? '-'} kW</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Base nuit</span><span className="font-medium">{kpiData.pbase_night_kw ?? '-'} kW</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Total kWh</span><span className="font-medium">{kpiData.total_kwh ? kpiData.total_kwh.toLocaleString() : '-'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Weekend ratio</span><span className="font-medium">{kpiData.weekend_ratio ? (kpiData.weekend_ratio * 100).toFixed(1) + '%' : '-'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Night ratio</span><span className="font-medium">{kpiData.night_ratio ? (kpiData.night_ratio * 100).toFixed(1) + '%' : '-'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Ramp rate max</span><span className="font-medium">{kpiData.ramp_rate_max_kw_h ?? '-'} kW/h</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Readings</span><span className="font-medium">{kpiData.readings_count ?? '-'}</span></div>
          </div>
        </div>

        {/* Jour-type Profile (ASCII bar chart) */}
        <div className="bg-white rounded-lg shadow p-5">
          <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Clock size={18} /> Profil Jour-Type (kW par heure)
          </h2>
          <div className="space-y-1">
            {(kpiData.weekday_profile_kw || []).map((val, h) => {
              const maxVal = Math.max(...(kpiData.weekday_profile_kw || [1]), 1);
              const pct = (val / maxVal) * 100;
              return (
                <div key={h} className="flex items-center gap-2 text-xs">
                  <span className="w-6 text-right text-gray-400">{String(h).padStart(2, '0')}h</span>
                  <div className="flex-1 bg-gray-100 rounded-sm h-3 overflow-hidden">
                    <div
                      className="bg-blue-500 h-full rounded-sm"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-14 text-right text-gray-500">{val} kW</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-white rounded-lg shadow p-5 mb-8">
        <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <AlertTriangle size={18} className="text-orange-500" />
          Alertes Monitoring ({alerts.length})
        </h2>
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-400">Aucune alerte. Lancez une analyse pour detecter les anomalies.</p>
        ) : (
          <div className="space-y-3">
            {alerts.map(a => (
              <div key={a.id} className={`border rounded-lg p-4 ${severityBg(a.severity)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBadge(a.status)}`}>
                        {a.status.toUpperCase()}
                      </span>
                      <span className="font-medium text-sm">{a.alert_type}</span>
                      <span className="text-xs opacity-60">{a.severity}</span>
                    </div>
                    <p className="text-sm mt-1">{a.explanation}</p>
                    {a.recommended_action && (
                      <p className="text-xs mt-1 opacity-70">Action: {a.recommended_action}</p>
                    )}
                    {(a.estimated_impact_kwh || a.estimated_impact_eur) && (
                      <p className="text-xs mt-1 opacity-60">
                        Impact: {a.estimated_impact_kwh ? `${a.estimated_impact_kwh} kWh` : ''}
                        {a.estimated_impact_eur ? ` / ${a.estimated_impact_eur} EUR` : ''}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    {a.status === 'open' && (
                      <button
                        onClick={() => ackAlert(a.id)}
                        className="px-3 py-1 bg-yellow-500 text-white rounded text-xs hover:bg-yellow-600"
                      >
                        ACK
                      </button>
                    )}
                    {(a.status === 'open' || a.status === 'ack') && (
                      <button
                        onClick={() => resolveAlert(a.id)}
                        className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Snapshots History */}
      <div className="bg-white rounded-lg shadow p-5">
        <h2 className="font-semibold text-gray-700 mb-4">Historique Snapshots</h2>
        {snapshots.length === 0 ? (
          <p className="text-sm text-gray-400">Aucun snapshot disponible.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="pb-2">ID</th>
                <th className="pb-2">Periode</th>
                <th className="pb-2">Qualite</th>
                <th className="pb-2">Risque</th>
                <th className="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.map(s => (
                <tr key={s.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{s.id}</td>
                  <td className="py-2">{s.period}</td>
                  <td className={`py-2 font-medium ${scoreColor(s.data_quality_score || 0)}`}>
                    {s.data_quality_score ?? '-'}
                  </td>
                  <td className={`py-2 font-medium ${riskColor(s.risk_power_score || 0)}`}>
                    {s.risk_power_score ?? '-'}
                  </td>
                  <td className="py-2 text-gray-400">{s.created_at?.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default MonitoringPage;
