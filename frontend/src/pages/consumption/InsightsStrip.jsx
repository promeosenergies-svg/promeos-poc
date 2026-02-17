/**
 * PROMEOS — InsightsStrip
 * Horizontal scrollable strip of auto-generated insight badges.
 * Displayed below the tab bar, above the active panel.
 *
 * Props:
 *   insights  {object[]}  array of { id, label, severity, detail }
 *                         severity: 'info' | 'warn' | 'crit'
 */
import { useState } from 'react';
import { Info, AlertTriangle, AlertOctagon, X } from 'lucide-react';

const SEVERITY_STYLES = {
  crit: {
    bg: 'bg-red-50 border-red-200',
    text: 'text-red-700',
    dot: 'bg-red-500',
    Icon: AlertOctagon,
  },
  warn: {
    bg: 'bg-amber-50 border-amber-200',
    text: 'text-amber-700',
    dot: 'bg-amber-500',
    Icon: AlertTriangle,
  },
  info: {
    bg: 'bg-blue-50 border-blue-200',
    text: 'text-blue-700',
    dot: 'bg-blue-400',
    Icon: Info,
  },
};

function InsightBadge({ insight, onDismiss }) {
  const [expanded, setExpanded] = useState(false);
  const style = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;
  const Icon = style.Icon;

  return (
    <div className={`relative flex-shrink-0 border rounded-lg px-3 py-1.5 ${style.bg} ${style.text} max-w-xs`}>
      <button
        className="flex items-center gap-1.5 text-xs font-medium"
        onClick={() => setExpanded(v => !v)}
        title="Voir le detail"
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
        <Icon size={12} className="shrink-0" />
        <span>{insight.label}</span>
      </button>

      {/* Detail tooltip on click */}
      {expanded && insight.detail && (
        <div className="absolute top-full left-0 mt-1 z-30 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs text-gray-700 w-64">
          {insight.detail}
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(false); }}
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Dismiss */}
      {onDismiss && (
        <button
          onClick={() => onDismiss(insight.id)}
          className={`ml-1.5 opacity-50 hover:opacity-100 transition ${style.text}`}
          title="Ignorer"
        >
          <X size={10} />
        </button>
      )}
    </div>
  );
}

export default function InsightsStrip({ insights = [] }) {
  const [dismissed, setDismissed] = useState(new Set());

  const visible = insights.filter(i => !dismissed.has(i.id));
  if (!visible.length) return null;

  const dismiss = (id) => setDismissed(prev => new Set([...prev, id]));

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
      <span className="text-xs font-semibold text-gray-500 shrink-0">Insights :</span>
      {visible.map(insight => (
        <InsightBadge key={insight.id} insight={insight} onDismiss={dismiss} />
      ))}
    </div>
  );
}
