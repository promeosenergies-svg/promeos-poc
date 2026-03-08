/**
 * PROMEOS — InsightsStrip
 * Horizontal scrollable strip of auto-generated insight badges.
 * Displayed below the tab bar, above the active panel.
 * V2: detail popup portaled to body (escapes sticky/overflow clipping).
 *
 * Props:
 *   insights  {object[]}  array of { id, label, severity, detail }
 *                         severity: 'info' | 'warn' | 'crit'
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
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
  const [coords, setCoords] = useState(null);
  const badgeRef = useRef(null);
  const popupRef = useRef(null);
  const style = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;
  const Icon = style.Icon;

  const close = useCallback(() => setExpanded(false), []);

  // ESC to close + click-outside
  useEffect(() => {
    if (!expanded) return;
    const onKey = (e) => {
      if (e.key === 'Escape') close();
    };
    const onClick = (e) => {
      if (
        popupRef.current &&
        !popupRef.current.contains(e.target) &&
        badgeRef.current &&
        !badgeRef.current.contains(e.target)
      ) {
        close();
      }
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [expanded, close]);

  const handleToggle = () => {
    if (!expanded && badgeRef.current) {
      const r = badgeRef.current.getBoundingClientRect();
      setCoords({ top: r.bottom + 4, left: r.left });
    }
    setExpanded((v) => !v);
  };

  return (
    <div
      ref={badgeRef}
      className={`relative flex-shrink-0 border rounded-lg px-3 py-1.5 ${style.bg} ${style.text} max-w-xs`}
    >
      <button
        className="flex items-center gap-1.5 text-xs font-medium"
        onClick={handleToggle}
        title="Voir le détail"
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
        <Icon size={12} className="shrink-0" />
        <span>{insight.label}</span>
      </button>

      {/* Detail popup on click — portaled to escape overflow/stacking clipping */}
      {expanded &&
        insight.detail &&
        coords &&
        createPortal(
          <div
            ref={popupRef}
            className="fixed z-[120] bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs text-gray-700 w-64"
            style={{ top: coords.top, left: coords.left }}
          >
            {insight.detail}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(false);
              }}
              className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
            >
              <X size={12} />
            </button>
          </div>,
          document.body
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

  const visible = insights.filter((i) => !dismissed.has(i.id));
  if (!visible.length) return null;

  const dismiss = (id) => setDismissed((prev) => new Set([...prev, id]));

  const MAX_VISIBLE = 4;
  const shown = visible.slice(0, MAX_VISIBLE);
  const overflow = visible.length - MAX_VISIBLE;

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
      <span className="text-xs font-semibold text-gray-500 shrink-0">Analyses :</span>
      {shown.map((insight) => (
        <InsightBadge key={insight.id} insight={insight} onDismiss={dismiss} />
      ))}
      {overflow > 0 && (
        <span className="text-xs text-gray-400 font-medium shrink-0 px-2 py-1 bg-gray-100 rounded-full">
          +{overflow}
        </span>
      )}
    </div>
  );
}
