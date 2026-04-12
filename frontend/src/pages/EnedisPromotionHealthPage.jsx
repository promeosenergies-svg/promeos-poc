/**
 * PROMEOS - Enedis Promotion Health Dashboard
 * Monitoring du pipeline SF5 : dernier run, volumes, backlog, alertes.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Database,
  PlayCircle,
} from 'lucide-react';
import {
  getPromotionHealth,
  getPromotionRuns,
  getPromotionBacklog,
  triggerPromotion,
  getOpendataFreshness,
  refreshOpendata,
} from '../services/api/enedis';
import { PageShell } from '../ui';
import { useToast } from '../ui/ToastProvider';

const STATUS_CONFIG = {
  healthy: { color: 'bg-green-100 text-green-700', icon: CheckCircle2, label: 'En bonne santé' },
  warning: { color: 'bg-yellow-100 text-yellow-700', icon: AlertTriangle, label: 'Attention' },
  stale: { color: 'bg-orange-100 text-orange-700', icon: Clock, label: 'Données périmées' },
  error: { color: 'bg-red-100 text-red-700', icon: XCircle, label: 'Erreur' },
  running: { color: 'bg-blue-100 text-blue-700', icon: Activity, label: 'En cours' },
  never_ran: { color: 'bg-gray-100 text-gray-700', icon: Clock, label: 'Jamais exécuté' },
  unknown: { color: 'bg-gray-100 text-gray-700', icon: Clock, label: 'Inconnu' },
};

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.unknown;
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${config.color}`}
    >
      <Icon size={16} />
      {config.label}
    </span>
  );
}

function KpiTile({ label, value, sublabel, icon: Icon, color = 'text-gray-700' }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
        {Icon && <Icon size={16} className="text-gray-400" />}
      </div>
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
    </div>
  );
}

function formatDateTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function formatNumber(n) {
  if (n == null) return '—';
  return n.toLocaleString('fr-FR');
}

export default function EnedisPromotionHealthPage() {
  const [health, setHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [backlog, setBacklog] = useState([]);
  const [freshness, setFreshness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [refreshingOds, setRefreshingOds] = useState(false);
  const toast = useToast();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [h, r, b, f] = await Promise.all([
        getPromotionHealth(),
        getPromotionRuns(10, 0),
        getPromotionBacklog('pending', 20),
        getOpendataFreshness().catch(() => null),
      ]);
      setHealth(h);
      setRuns(r.items || []);
      setBacklog(b.items || []);
      setFreshness(f);
    } catch (e) {
      toast?.error?.('Erreur chargement du health pipeline');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const handleRefreshOds = async () => {
    setRefreshingOds(true);
    try {
      const result = await refreshOpendata('sup36');
      toast?.success?.(`ODS refresh : ${result.total_rows || 0} rows importées`);
      fetchAll();
    } catch (e) {
      toast?.error?.(`Erreur ODS refresh : ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRefreshingOds(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000); // Auto-refresh 30s
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleTrigger = async (dryRun = false) => {
    setTriggering(true);
    try {
      const result = await triggerPromotion('incremental', dryRun);
      toast?.success?.(
        `Run #${result.run_id} : ${result.prms_matched}/${result.prms_total} PRMs, ${result.rows_load_curve} CDC`
      );
      fetchAll();
    } catch (e) {
      toast?.error?.(`Erreur : ${e?.response?.data?.detail || e.message}`);
    } finally {
      setTriggering(false);
    }
  };

  if (loading && !health) {
    return (
      <PageShell title="Enedis — Promotion Pipeline">
        <div className="text-gray-400 animate-pulse">Chargement…</div>
      </PageShell>
    );
  }

  const lastRun = health?.last_run;
  const volumes = health?.volumes || {};

  return (
    <PageShell
      title="Enedis — Promotion Pipeline"
      subtitle="Monitoring SF5 — staging → tables fonctionnelles"
    >
      {/* Status banner + actions */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <StatusBadge status={health?.status} />
          <span className="text-sm text-gray-500">
            Vérifié : {formatDateTime(health?.checked_at)}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => fetchAll()}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <RefreshCw size={14} />
            Rafraîchir
          </button>
          <button
            onClick={() => handleTrigger(true)}
            disabled={triggering || health?.status === 'running'}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            <PlayCircle size={14} />
            Dry-run
          </button>
          <button
            onClick={() => handleTrigger(false)}
            disabled={triggering || health?.status === 'running'}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            <PlayCircle size={14} />
            Lancer promotion
          </button>
        </div>
      </div>

      {/* Alerts */}
      {health?.alerts?.length > 0 && (
        <div className="mb-6 space-y-2">
          {health.alerts.map((alert, i) => (
            <div
              key={i}
              className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800"
            >
              <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
              <span>{alert}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiTile
          label="CDC promues"
          value={formatNumber(volumes.meter_load_curve_total)}
          sublabel="meter_load_curve"
          icon={Database}
          color="text-blue-700"
        />
        <KpiTile
          label="PRMs en backlog"
          value={formatNumber(volumes.backlog_pending)}
          sublabel={`${volumes.backlog_resolved || 0} résolus`}
          icon={AlertTriangle}
          color={volumes.backlog_pending > 100 ? 'text-red-600' : 'text-gray-700'}
        />
        <KpiTile
          label="Dernier run"
          value={lastRun ? `#${lastRun.id}` : '—'}
          sublabel={
            lastRun ? `${lastRun.mode} — ${formatDateTime(lastRun.started_at)}` : 'Aucun run'
          }
          icon={Activity}
        />
        <KpiTile
          label="PRMs matchés"
          value={lastRun ? `${lastRun.prms_matched}/${lastRun.prms_total}` : '—'}
          sublabel={lastRun ? `${lastRun.rows_promoted || 0} rows promues` : ''}
          icon={CheckCircle2}
          color="text-green-700"
        />
      </div>

      {/* ODS Freshness section */}
      {freshness && (
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">
              Open Data Enedis — fraîcheur des benchmarks NAF
            </h2>
            <button
              onClick={handleRefreshOds}
              disabled={refreshingOds}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw size={12} />
              {refreshingOds ? 'Import…' : 'Refresh ODS'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div
                className={`w-2 h-2 rounded-full ${
                  freshness.status === 'fresh'
                    ? 'bg-green-500'
                    : freshness.status === 'aging'
                      ? 'bg-yellow-500'
                      : freshness.status === 'stale'
                        ? 'bg-orange-500'
                        : 'bg-gray-400'
                }`}
              />
              <div>
                <div className="text-xs text-gray-500 uppercase">Status</div>
                <div className="text-sm font-medium">{freshness.status}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase">conso-sup36</div>
              <div className="text-sm">
                {formatNumber(freshness.sup36?.count)} rows
                {freshness.sup36?.age_days != null && (
                  <span className="text-gray-500 ml-2">(il y a {freshness.sup36.age_days}j)</span>
                )}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase">conso-inf36</div>
              <div className="text-sm">
                {formatNumber(freshness.inf36?.count)} rows
                {freshness.inf36?.age_days != null && (
                  <span className="text-gray-500 ml-2">(il y a {freshness.inf36.age_days}j)</span>
                )}
              </div>
            </div>
          </div>
          {freshness.alerts?.length > 0 && (
            <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
              {freshness.alerts.join(' — ')}
            </div>
          )}
        </div>
      )}

      {/* Last run detail */}
      {lastRun && (
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Dernier run (détails)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">ID</div>
              <div className="font-mono">#{lastRun.id}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">Status</div>
              <div>{lastRun.status}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">Mode</div>
              <div>{lastRun.mode}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">Déclencheur</div>
              <div>{lastRun.triggered_by}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">Démarré</div>
              <div>{formatDateTime(lastRun.started_at)}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">Terminé</div>
              <div>{formatDateTime(lastRun.finished_at)}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">PRMs total</div>
              <div>{formatNumber(lastRun.prms_total)}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs uppercase mb-1">PRMs non matchés</div>
              <div className={lastRun.prms_unmatched > 0 ? 'text-orange-600' : ''}>
                {formatNumber(lastRun.prms_unmatched)}
              </div>
            </div>
          </div>
          {lastRun.error_message && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 font-mono">
              {lastRun.error_message}
            </div>
          )}
        </div>
      )}

      {/* Recent runs */}
      {runs.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Runs récents ({runs.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 uppercase border-b">
                <tr>
                  <th className="text-left py-2 px-2">ID</th>
                  <th className="text-left py-2 px-2">Status</th>
                  <th className="text-left py-2 px-2">Mode</th>
                  <th className="text-left py-2 px-2">Démarré</th>
                  <th className="text-right py-2 px-2">PRMs</th>
                  <th className="text-right py-2 px-2">CDC</th>
                  <th className="text-right py-2 px-2">Index</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-b border-gray-100">
                    <td className="py-2 px-2 font-mono text-xs">#{r.id}</td>
                    <td className="py-2 px-2">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs ${
                          r.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : r.status === 'failed'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-gray-600">{r.mode}</td>
                    <td className="py-2 px-2 text-gray-600 text-xs">
                      {formatDateTime(r.started_at)}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {r.prms_matched}/{r.prms_total}
                    </td>
                    <td className="py-2 px-2 text-right">{formatNumber(r.rows_load_curve)}</td>
                    <td className="py-2 px-2 text-right">{formatNumber(r.rows_energy_index)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Backlog */}
      {backlog.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Backlog PRMs non résolus ({backlog.length})
          </h2>
          <div className="space-y-2">
            {backlog.slice(0, 10).map((u) => (
              <div
                key={u.id}
                className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-gray-700">{u.point_id}</span>
                  <span className="text-orange-600">{u.block_reason}</span>
                </div>
                <div className="text-gray-500">
                  {u.measures_count} mesures — {formatDateTime(u.last_seen_at)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  );
}
