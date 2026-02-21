/**
 * PROMEOS — BriefingHeroCard (Cockpit Sprint)
 * "Briefing du jour" hero section above the KPI grid.
 * Shows up to 3 priority action items from buildBriefing().
 * Empty state: "Tout est sous contrôle".
 *
 * Props:
 *   briefing    {BriefingItem[]} — from buildBriefing(kpis, watchlist)
 *   onNavigate  {fn}            — navigate(path)
 */
import { Sparkles, ArrowRight, AlertCircle, AlertTriangle, Info } from 'lucide-react';

// ── Severity config ────────────────────────────────────────────────────────────

const SEVERITY = {
  critical: {
    dot: 'bg-red-500',
    icon: AlertCircle,
    iconClass: 'text-red-500',
  },
  high: {
    dot: 'bg-amber-500',
    icon: AlertTriangle,
    iconClass: 'text-amber-500',
  },
  warn: {
    dot: 'bg-yellow-400',
    icon: Info,
    iconClass: 'text-yellow-500',
  },
  info: {
    dot: 'bg-blue-400',
    icon: Info,
    iconClass: 'text-blue-500',
  },
};

// ── Briefing item row ─────────────────────────────────────────────────────────

function BriefingItem({ item, onNavigate }) {
  const cfg = SEVERITY[item.severity] || SEVERITY.info;
  const ItemIcon = cfg.icon;

  return (
    <button
      onClick={() => onNavigate?.(item.path)}
      className="w-full flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-gray-50 transition text-left focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
    >
      <div className="flex items-center gap-3 min-w-0">
        <ItemIcon size={14} className={`shrink-0 ${cfg.iconClass}`} />
        <span className="text-sm text-gray-800 truncate">{item.label}</span>
      </div>
      <ArrowRight size={13} className="text-gray-300 shrink-0" />
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function BriefingHeroCard({ briefing = [], onNavigate }) {
  // Empty / all-green state
  if (!briefing.length) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 bg-emerald-50 border border-emerald-100 rounded-xl">
        <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
          <Sparkles size={16} className="text-emerald-600" />
        </div>
        <p className="text-sm font-medium text-emerald-800 flex-1">
          Tout est sous contrôle — aucune action urgente.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">
        Briefing du jour
      </p>
      <div className="rounded-xl border border-gray-100 bg-white divide-y divide-gray-50 shadow-sm">
        {briefing.map((item) => (
          <BriefingItem key={item.id} item={item} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}
