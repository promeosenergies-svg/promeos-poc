/**
 * PROMEOS - Admin KB Metrics Page
 * Observabilité KB : coverage, latence, top items, top missing fields.
 * Consomme /api/kb/metrics?since_days=N.
 */
import { useState, useEffect, useCallback } from 'react';
import { Activity, Database, Gauge, AlertTriangle, RefreshCw } from 'lucide-react';
import { getKBMetrics } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageShell, EmptyState } from '../ui';
import { useToast } from '../ui/ToastProvider';

const WINDOWS = [
  { days: 1, label: '24h' },
  { days: 7, label: '7j' },
  { days: 30, label: '30j' },
  { days: 90, label: '90j' },
];

function StatCard({ icon: Icon, label, value, hint, tone = 'default' }) {
  const toneMap = {
    default: 'bg-white border-gray-200 text-gray-900',
    good: 'bg-green-50 border-green-200 text-green-900',
    warn: 'bg-amber-50 border-amber-200 text-amber-900',
    bad: 'bg-red-50 border-red-200 text-red-900',
  };
  return (
    <div className={`rounded-lg border p-4 ${toneMap[tone]}`}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide opacity-70">
        <Icon size={14} />
        <span>{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs opacity-70">{hint}</div>}
    </div>
  );
}

function coverageTone(pct) {
  if (pct >= 80) return 'good';
  if (pct >= 50) return 'warn';
  return 'bad';
}

function latencyTone(p95) {
  if (p95 <= 50) return 'good';
  if (p95 <= 200) return 'warn';
  return 'bad';
}

export default function AdminKBMetricsPage() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sinceDays, setSinceDays] = useState(30);

  const load = useCallback(() => {
    setLoading(true);
    getKBMetrics(sinceDays)
      .then((data) => setMetrics(data))
      .catch(() => toast('Erreur lors du chargement des métriques KB', 'error'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sinceDays]);

  useEffect(() => {
    load();
  }, [load]);

  if (!hasPermission('admin')) {
    return (
      <PageShell icon={Database} title="Observabilité KB">
        <EmptyState
          icon={Database}
          title="Accès refusé"
          text="Vous n'avez pas les droits d'administration."
        />
      </PageShell>
    );
  }

  if (loading && !metrics) {
    return (
      <PageShell icon={Database} title="Observabilité KB" subtitle="Chargement...">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-lg" />
          ))}
        </div>
      </PageShell>
    );
  }

  const empty = !metrics || metrics.total_calls === 0;
  const coveragePct = metrics?.coverage?.coverage_pct ?? 0;
  const p95 = metrics?.latency_ms?.p95 ?? 0;

  return (
    <PageShell
      icon={Database}
      title="Observabilité KB"
      subtitle={`Fenêtre : ${sinceDays}j · ${metrics?.total_calls ?? 0} appels KBService.apply`}
    >
      {/* Controls */}
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.days}
              type="button"
              onClick={() => setSinceDays(w.days)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                sinceDays === w.days
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm bg-white border border-gray-200 hover:bg-gray-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Actualiser
        </button>
      </div>

      {empty ? (
        <EmptyState
          icon={Database}
          title="Aucun appel KB sur cette fenêtre"
          text="Les métriques apparaîtront dès que les agents PROMEOS interrogeront la KB via KBService.apply()."
        />
      ) : (
        <>
          {/* Top stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <StatCard
              icon={Activity}
              label="Appels totaux"
              value={metrics.total_calls.toLocaleString('fr-FR')}
              hint={`sur ${sinceDays} jour${sinceDays > 1 ? 's' : ''}`}
            />
            <StatCard
              icon={Gauge}
              label="Coverage"
              value={`${coveragePct}%`}
              hint={`${metrics.coverage.calls_with_matches} avec matches / ${metrics.coverage.calls_without_matches} sans`}
              tone={coverageTone(coveragePct)}
            />
            <StatCard
              icon={Gauge}
              label="Latence p95"
              value={`${p95} ms`}
              hint={`p50 ${metrics.latency_ms.p50} · max ${metrics.latency_ms.max}`}
              tone={latencyTone(p95)}
            />
            <StatCard
              icon={AlertTriangle}
              label="Champs manquants"
              value={metrics.top_missing_fields.length}
              hint="signaux pour compléter la KB"
              tone={metrics.top_missing_fields.length > 0 ? 'warn' : 'good'}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* By domain */}
            <section className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Appels par domaine</h3>
              {metrics.by_domain.length === 0 ? (
                <div className="text-xs text-gray-400 italic">
                  Aucun domaine ciblé sur cette fenêtre.
                </div>
              ) : (
                <ul className="space-y-2">
                  {metrics.by_domain.map((d) => {
                    const pct = metrics.total_calls
                      ? Math.round((d.calls / metrics.total_calls) * 100)
                      : 0;
                    return (
                      <li key={d.domain} className="text-sm">
                        <div className="flex justify-between mb-0.5">
                          <span className="font-medium text-gray-700">{d.domain}</span>
                          <span className="text-gray-500">
                            {d.calls} ({pct}%)
                          </span>
                        </div>
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full bg-indigo-500" style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            {/* Top items */}
            <section className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Top 10 items KB matchés</h3>
              {metrics.top_items.length === 0 ? (
                <div className="text-xs text-gray-400 italic">Aucun item matché.</div>
              ) : (
                <ul className="space-y-1.5">
                  {metrics.top_items.map((it) => (
                    <li
                      key={`${it.kb_item_id}-${it.domain}`}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono text-xs text-gray-500 truncate">
                          {it.kb_item_id}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                          {it.domain}
                        </span>
                      </div>
                      <span className="font-semibold text-gray-900 tabular-nums">{it.hits}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* Missing fields */}
          <section className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-1">
              Top 10 champs manquants dans le site_context
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              Signaux pour compléter la KB ou enrichir la donnée Site — plus l'occurrence est
              élevée, plus l'ajout du champ débloquera d'items KB.
            </p>
            {metrics.top_missing_fields.length === 0 ? (
              <div className="text-xs text-green-700 bg-green-50 rounded p-2">
                Aucun champ manquant sur cette fenêtre — couverture des contextes complète.
              </div>
            ) : (
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5">
                {metrics.top_missing_fields.map((f) => (
                  <li key={f.field} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-700">{f.field}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 tabular-nums">
                      {f.occurrences}x
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </PageShell>
  );
}
