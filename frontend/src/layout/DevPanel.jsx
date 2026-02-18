/**
 * PROMEOS — DevPanel (dev-only)
 * Enhanced debug panel visible when ?debug is in URL.
 * Tabs: Scope | API | Cache | Env
 * Replaces ScopeDebugPanel in AppShell.
 */
import { useState, useMemo } from 'react';
import { Bug, X } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { getLastRequests } from '../services/api';

const TABS = ['Scope', 'API', 'Cache', 'Env'];

function ScopeTab() {
  const { scope, org, orgSites, sitesLoading, sitesCount, scopeLabel, selectedSiteId } = useScope();
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
    <div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2 leading-5">
          <span className="text-gray-400">{k}</span>
          <span className="text-green-300 truncate max-w-[55%] text-right">{String(v)}</span>
        </div>
      ))}
    </div>
  );
}

function ApiTab() {
  const requests = getLastRequests();
  if (requests.length === 0) {
    return <p className="text-gray-500 text-[10px]">Aucun appel API enregistre</p>;
  }
  return (
    <div className="space-y-1 max-h-52 overflow-y-auto">
      {[...requests].reverse().map((r) => (
        <div key={r.id} className="flex items-center gap-2 text-[10px] leading-4">
          <span className={r.error ? 'text-red-400' : r.status >= 400 ? 'text-yellow-400' : 'text-green-400'}>
            {r.status || '---'}
          </span>
          <span className="text-gray-400">{r.method || '?'}</span>
          <span className="text-green-300 truncate flex-1">{r.url}</span>
          <span className="text-gray-500 shrink-0">{r.duration}ms</span>
        </div>
      ))}
    </div>
  );
}

function CacheTab() {
  const keys = useMemo(() => {
    const result = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('promeos_')) {
          const val = localStorage.getItem(key) || '';
          result.push({ key, size: val.length });
        }
      }
    } catch { /* private browsing */ }
    return result;
  }, []);

  if (keys.length === 0) {
    return <p className="text-gray-500 text-[10px]">Aucune cle promeos_* dans localStorage</p>;
  }
  return (
    <div className="space-y-1">
      {keys.map(({ key, size }) => (
        <div key={key} className="flex justify-between gap-2 text-[10px] leading-4">
          <span className="text-green-300 truncate">{key}</span>
          <span className="text-gray-500 shrink-0">{size} chars</span>
        </div>
      ))}
    </div>
  );
}

function EnvTab() {
  const rows = [
    ['MODE', import.meta.env.MODE],
    ['VITE_API_URL', import.meta.env.VITE_API_URL || '(default /api)'],
    ['VITE_SENTRY_DSN', import.meta.env.VITE_SENTRY_DSN ? '***' : '(non defini)'],
    ['DEV', String(import.meta.env.DEV)],
  ];
  return (
    <div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2 leading-5">
          <span className="text-gray-400">{k}</span>
          <span className="text-green-300 truncate max-w-[55%] text-right">{String(v)}</span>
        </div>
      ))}
    </div>
  );
}

const TAB_COMPONENTS = { Scope: ScopeTab, API: ApiTab, Cache: CacheTab, Env: EnvTab };

export default function DevPanel() {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('Scope');

  const isDebug = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('debug');
  if (!isDebug) return null;

  const TabContent = TAB_COMPONENTS[activeTab];

  return (
    <>
      {/* Floating toggle button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-4 right-4 z-[9999] w-10 h-10 rounded-full bg-gray-900 text-green-400
            flex items-center justify-center shadow-xl hover:bg-gray-800 transition"
          aria-label="Open DevPanel"
        >
          <Bug size={18} />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-4 right-4 z-[9999] bg-gray-900 text-green-400 font-mono text-xs
            rounded-lg shadow-xl w-80 max-h-[420px] flex flex-col opacity-95"
          aria-label="Dev Panel"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
            <span className="text-green-300 font-bold uppercase tracking-wider text-[10px]">
              PROMEOS DevPanel
            </span>
            <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-300 transition">
              <X size={14} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-700">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-1.5 text-[10px] font-semibold uppercase tracking-wider transition
                  ${activeTab === tab
                    ? 'text-green-400 border-b-2 border-green-400'
                    : 'text-gray-500 hover:text-gray-300'}`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-3 overflow-y-auto flex-1">
            <TabContent />
          </div>
        </div>
      )}
    </>
  );
}
