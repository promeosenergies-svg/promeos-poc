/**
 * PROMEOS — ExplorerDebugPanel (Sprint V14.3-B)
 * Terminal-style diagnostic overlay for /consommations/explorer?debug=1
 *
 * Props:
 *   params       {object}   Current query params (siteIds, energy, days, unit, mode, etc.)
 *   tsState      {object}   useEmsTimeseries state (status, meta, granularity, debugInfo, error)
 *   availability {object}   from useExplorerMotor
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, CheckCircle } from 'lucide-react';

function Row({ label, value }) {
  if (value == null || value === '' || value === undefined) return null;
  const display = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return (
    <div className="flex gap-2 text-xs font-mono">
      <span className="text-green-500 shrink-0 w-36">{label}</span>
      <span className="text-green-200 break-all">{display}</span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-3">
      <p className="text-[10px] font-bold text-green-600 uppercase tracking-widest mb-1">
        ▸ {title}
      </p>
      <div className="space-y-0.5 pl-2">{children}</div>
    </div>
  );
}

export default function ExplorerDebugPanel({ params = {}, tsState = {}, availability = null, scope = null }) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);

  const {
    siteIds, energyType, days, unit, mode, startDate, endDate,
  } = params;

  const {
    status, meta, granularity, debugInfo, error,
  } = tsState;

  const avail = availability || {};

  const handleCopy = () => {
    const payload = JSON.stringify({
      scope,
      params,
      tsState: { status, meta, granularity, error, debugInfo },
      availability: avail,
    }, null, 2);
    try {
      navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div className="rounded-lg border border-green-900 bg-gray-950 text-green-400 select-none overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(v => !v)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-900 hover:bg-gray-800 transition"
      >
        <span className="text-xs font-mono font-bold text-green-400">
          🔧 PROMEOS Debug — Explorer
        </span>
        <div className="flex items-center gap-2">
          {!collapsed && (
            <button
              onClick={(e) => { e.stopPropagation(); handleCopy(); }}
              className="flex items-center gap-1 text-[10px] text-green-600 hover:text-green-300 transition"
            >
              {copied ? <CheckCircle size={12} /> : <Copy size={12} />}
              {copied ? 'Copié' : 'Copier diagnostic'}
            </button>
          )}
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </div>
      </button>

      {!collapsed && (
        <div className="px-4 py-3 space-y-0 overflow-x-auto max-h-96 overflow-y-auto">
          {/* Scope (V16-A) */}
          {scope && (
            <Section title="Scope global">
              <Row label="orgId" value={scope.orgId} />
              <Row label="selectedSiteId" value={scope.selectedSiteId} />
              <Row label="scopeLabel" value={scope.scopeLabel} />
              <Row label="sitesCount" value={scope.sitesCount} />
            </Section>
          )}

          {/* Query params */}
          <Section title="Paramètres requête">
            <Row label="siteIds" value={siteIds?.join(', ') || '(vide)'} />
            <Row label="energyType" value={energyType} />
            <Row label="days" value={days} />
            <Row label="unit" value={unit} />
            <Row label="mode" value={mode} />
            <Row label="startDate" value={startDate} />
            <Row label="endDate" value={endDate} />
          </Section>

          {/* Timeseries state */}
          <Section title="État série temporelle (EMS)">
            <Row label="status" value={status} />
            <Row label="granularity" value={granularity} />
            <Row label="meta.n_points" value={meta?.n_points} />
            <Row label="meta.n_meters" value={meta?.n_meters} />
            <Row label="meta.date_from" value={meta?.date_from} />
            <Row label="meta.date_to" value={meta?.date_to} />
            <Row label="error" value={error} />
          </Section>

          {/* Debug info from hook */}
          {debugInfo && (
            <Section title="API debug">
              <Row label="endpoint" value={debugInfo.endpoint} />
              <Row label="params" value={debugInfo.params} />
              <Row label="responseMs" value={debugInfo.responseMs != null ? `${debugInfo.responseMs} ms` : null} />
              <Row label="seriesCount" value={debugInfo.seriesCount} />
              <Row label="pointsCount" value={debugInfo.pointsCount} />
              <Row label="yMin" value={debugInfo.yMin} />
              <Row label="yMax" value={debugInfo.yMax} />
            </Section>
          )}

          {/* Availability */}
          <Section title="Disponibilité données (Motor)">
            <Row label="has_data" value={String(avail.has_data ?? 'null')} />
            <Row label="reasons" value={avail.reasons?.join(', ')} />
            <Row label="readings_count" value={avail.readings_count} />
            <Row label="first_ts" value={avail.first_ts} />
            <Row label="last_ts" value={avail.last_ts} />
            <Row label="energy_types" value={avail.energy_types?.join(', ')} />
          </Section>
        </div>
      )}
    </div>
  );
}
