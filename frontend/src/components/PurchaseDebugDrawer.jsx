/**
 * PROMEOS — Purchase Debug Drawer (Brique 3, dev only)
 * Shows internal state of the purchase wizard for debugging.
 * Only visible in development mode (import.meta.env.DEV).
 */
import { useState } from 'react';
import { Bug, ChevronDown, ChevronUp, X } from 'lucide-react';

function DebugSection({ title, data, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50"
      >
        {title}
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <pre className="px-3 pb-2 text-[10px] text-gray-700 whitespace-pre-wrap overflow-auto max-h-48 bg-gray-50 rounded-b">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function PurchaseDebugDrawer({
  assumptions,
  preferences,
  scenarios,
  portfolioData,
  selectedSiteId,
  seedResult,
}) {
  const [open, setOpen] = useState(false);

  // Only render in dev mode
  if (!import.meta.env.DEV) return null;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-40 p-2.5 bg-gray-800 text-white rounded-full shadow-lg hover:bg-gray-700 transition"
        title="Debug Drawer (dev only)"
      >
        <Bug size={16} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 right-0 z-50 w-80 max-h-[70vh] bg-white border-l border-t border-gray-300 shadow-2xl rounded-tl-xl overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 text-white">
        <span className="text-xs font-bold flex items-center gap-1.5">
          <Bug size={12} /> Purchase Debug
        </span>
        <button onClick={() => setOpen(false)} className="hover:bg-gray-700 rounded p-0.5">
          <X size={14} />
        </button>
      </div>
      <div className="overflow-y-auto flex-1">
        <DebugSection title="Selected Site" data={{ selectedSiteId }} defaultOpen />
        <DebugSection title="Assumptions" data={assumptions} defaultOpen />
        <DebugSection title="Preferences" data={preferences} />
        <DebugSection title={`Scenarios (${scenarios?.length || 0})`} data={scenarios} />
        <DebugSection title="Portfolio" data={portfolioData?.portfolio || null} />
        <DebugSection title={`Portfolio Sites (${portfolioData?.sites?.length || 0})`} data={portfolioData?.sites?.map(s => ({ site_id: s.site_id, reco: s.scenarios?.find(sc => sc.is_recommended)?.strategy })) || null} />
        {seedResult && <DebugSection title="Last Seed Result" data={seedResult} />}
      </div>
    </div>
  );
}
