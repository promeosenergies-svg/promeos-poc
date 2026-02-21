/**
 * PROMEOS — ScopeDebugPanel (dev-only)
 * Floating terminal panel visible when ?debug=1 in URL.
 * Shows current scope state: orgId, org.nom, sitesLoading, orgSites.length, etc.
 * Zero impact on production — returns null unless debug flag is present.
 */
import { useScope } from '../contexts/ScopeContext';

export default function ScopeDebugPanel() {
  const { scope, org, orgSites, sitesLoading, sitesCount, scopeLabel, selectedSiteId } = useScope();
  const isDebug = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('debug');
  if (!isDebug) return null;

  const rows = [
    ['orgId', scope?.orgId ?? 'null'],
    ['org.nom', org?.nom ?? 'null'],
    ['sitesLoading', String(sitesLoading)],
    ['orgSites.length', orgSites.length],
    ['sitesCount', sitesCount],
    ['selectedSiteId', selectedSiteId ?? 'null'],
    ['scopeLabel', scopeLabel],
  ];

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] bg-gray-900 text-green-400 font-mono text-xs rounded-lg shadow-xl p-3 w-72 opacity-90 select-none pointer-events-none"
      aria-label="Scope Debug Panel"
    >
      <p className="text-green-300 font-bold mb-2 uppercase tracking-wider text-[10px]">
        Scope Debug
      </p>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2 leading-5">
          <span className="text-gray-400">{k}</span>
          <span className="text-green-300 truncate max-w-[55%] text-right">{String(v)}</span>
        </div>
      ))}
    </div>
  );
}
