/**
 * Dev-only badges for the Conformite page (API status + scope debug).
 */
import { useState, useEffect } from 'react';
import { Database } from 'lucide-react';
import { getApiHealth } from '../../services/api';
import { resolveScopeLabel } from './conformiteUtils';

export function DevApiBadge() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getApiHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(false));
  }, []);

  if (health === null) return null; // loading

  const isOk = health && health.ok;
  return (
    <span
      data-testid="api-badge"
      className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full ${
        isOk ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      }`}
      title={isOk ? `v${health.version} \u00B7 ${health.git_sha}` : 'API injoignable'}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isOk ? 'bg-green-500' : 'bg-red-500'}`} />
      {isOk ? 'API : Connect\u00E9e' : 'API : Hors ligne'}
      {!isOk && <span className="ml-1 text-[9px] text-red-500">API indisponible</span>}
    </span>
  );
}

export function DevScopeBadge({ scope, scopedSites }) {
  const [copied, setCopied] = useState(false);
  const { scopeType, scopeId, label } = resolveScopeLabel(scope);

  const handleCopy = () => {
    navigator.clipboard.writeText(
      JSON.stringify({ scope_type: scopeType, scope_id: scopeId, sites_count: scopedSites.length })
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <span
      data-testid="scope-badge"
      className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 cursor-pointer"
      onClick={handleCopy}
      title={`Copier le p\u00E9rim\u00E8tre : ${label} (${scopedSites.length} sites)`}
    >
      <Database size={10} />
      {label}
      <span className="text-indigo-400">({scopedSites.length})</span>
      {copied && <span className="text-green-600 font-medium">copi\u00E9</span>}
    </span>
  );
}
