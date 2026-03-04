import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, RefreshCw, Server, Database, Code, Activity } from 'lucide-react';

const API_BASE = ''; // Vite proxy handles /api/*

function StatusPage() {
  const [status, setStatus] = useState(null);
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastCheck, setLastCheck] = useState(null);

  const checks = [
    { name: 'Backend /health', url: '/health', key: 'health' },
    { name: 'API Sites', url: '/api/sites', key: 'sites' },
    { name: 'API Cockpit', url: '/api/cockpit', key: 'cockpit' },
    { name: 'API KB Stats', url: '/api/kb/stats', key: 'kb' },
    { name: 'API Monitoring', url: '/api/monitoring/alerts', key: 'monitoring' },
    { name: 'API Bill Rules', url: '/api/bill/rules', key: 'bill' },
    { name: 'OpenAPI Schema', url: '/openapi.json', key: 'openapi' },
  ];

  const runChecks = async () => {
    setLoading(true);
    const results = {};

    // Health check
    try {
      const r = await fetch(`${API_BASE}/health`);
      const data = await r.json();
      results.health = { ok: r.ok, data };
    } catch (e) {
      results.health = { ok: false, error: e.message };
    }

    // Endpoint checks
    const endpointResults = [];
    for (const check of checks.slice(1)) {
      try {
        const r = await fetch(`${API_BASE}${check.url}`);
        results[check.key] = { ok: r.ok, status: r.status };
        endpointResults.push({ ...check, ok: r.ok, status: r.status });
      } catch (e) {
        results[check.key] = { ok: false, error: e.message };
        endpointResults.push({ ...check, ok: false, error: e.message });
      }
    }

    // OpenAPI path count
    if (results.openapi?.ok) {
      try {
        const r = await fetch(`${API_BASE}/openapi.json`);
        const schema = await r.json();
        results.endpointCount = Object.keys(schema.paths || {}).length;
      } catch {
        /* ignore */
      }
    }

    setStatus(results);
    setEndpoints(endpointResults);
    setLastCheck(new Date().toLocaleTimeString());
    setLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    runChecks();
  }, []);

  const backendOk = status?.health?.ok;
  const version = status?.health?.data?.version || '-';
  const _allOk =
    status && Object.values(status).every((v) => (typeof v === 'object' ? v.ok !== false : true));

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Server size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Statut PROMEOS</h1>
        </div>
        <button
          onClick={runChecks}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Rafraichir
        </button>
      </div>

      {/* Global Status */}
      <div
        className={`rounded-lg p-6 mb-6 ${backendOk ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}
      >
        <div className="flex items-center gap-3">
          {backendOk ? (
            <CheckCircle size={32} className="text-green-500" />
          ) : (
            <XCircle size={32} className="text-red-500" />
          )}
          <div>
            <p className="text-lg font-semibold">
              {backendOk ? 'Backend connecte' : 'Backend injoignable'}
            </p>
            <p className="text-sm text-gray-500">
              Version: {version} | Derniere verification: {lastCheck || '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-1">
            <Code size={16} className="text-blue-500" />
            <span className="text-sm text-gray-500">Endpoints API</span>
          </div>
          <p className="text-2xl font-bold">{status?.endpointCount || '-'}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-1">
            <Activity size={16} className="text-green-500" />
            <span className="text-sm text-gray-500">Checks OK</span>
          </div>
          <p className="text-2xl font-bold">
            {endpoints.filter((e) => e.ok).length}/{endpoints.length}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-1">
            <Database size={16} className="text-purple-500" />
            <span className="text-sm text-gray-500">Base de données</span>
          </div>
          <p className="text-2xl font-bold">{backendOk ? 'SQLite' : '-'}</p>
        </div>
      </div>

      {/* Endpoint Checks */}
      <div className="bg-white rounded-lg shadow p-5">
        <h2 className="font-semibold text-gray-700 mb-4">Verification des endpoints</h2>
        <div className="space-y-2">
          {checks.map((check) => {
            const result = status?.[check.key];
            const ok = result?.ok;
            return (
              <div
                key={check.key}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-2">
                  {ok === true && <CheckCircle size={16} className="text-green-500" />}
                  {ok === false && <XCircle size={16} className="text-red-500" />}
                  {ok === undefined && <div className="w-4 h-4 rounded-full bg-gray-200" />}
                  <span className="text-sm">{check.name}</span>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${ok ? 'bg-green-100 text-green-700' : ok === false ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'}`}
                >
                  {ok ? 'OK' : ok === false ? result?.error || `HTTP ${result?.status}` : '...'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tech Info */}
      <div className="mt-6 text-xs text-gray-400 text-center">
        PROMEOS POC | FastAPI + React + SQLite | 427 tests | 97 endpoints | 9 pages
      </div>
    </div>
  );
}

export default StatusPage;
