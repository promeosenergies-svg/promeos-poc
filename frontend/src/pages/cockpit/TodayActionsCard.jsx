/**
 * PROMEOS — TodayActionsCard (Cockpit V2)
 * "À traiter aujourd'hui" — top-5 deduped actions from buildTodayActions().
 * Severity-sorted, click navigates to the relevant module.
 *
 * Props:
 *   actions    {TodayAction[]} — from buildTodayActions()
 *   onNavigate {fn}           — navigate(path)
 *   title      {string}       — card heading (default "À traiter aujourd'hui")
 */
import { ArrowRight, CheckCircle2, AlertCircle, AlertTriangle, Info, Lightbulb } from 'lucide-react';
import { SEVERITY_TINT } from '../../ui/colorTokens';

// ── Severity icon map ─────────────────────────────────────────────────────────

const SEV_ICONS = {
  critical: AlertCircle,
  high:     AlertTriangle,
  warn:     AlertTriangle,
  medium:   Info,
  info:     Lightbulb,
};

// ── Action row ────────────────────────────────────────────────────────────────

function ActionItem({ action, index, onNavigate }) {
  const sev = SEVERITY_TINT[action.severity] || SEVERITY_TINT.neutral;
  const SevIcon = SEV_ICONS[action.severity] || Info;

  return (
    <button
      type="button"
      onClick={() => action.path && onNavigate?.(action.path)}
      className="flex items-center gap-3 w-full px-4 py-3 text-left rounded-lg
        hover:bg-gray-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      {/* Rank badge */}
      <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-[10px] font-bold shrink-0">
        {index + 1}
      </span>

      {/* Severity icon */}
      <SevIcon size={13} className={`shrink-0 ${sev.chipText.replace('text-', 'text-')}`} />

      {/* Label */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 leading-snug truncate">{action.label}</p>
        {action.cta && (
          <p className="text-xs text-gray-400 mt-0.5">{action.cta}</p>
        )}
      </div>

      {/* Severity chip */}
      <span className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${sev.chipBg} ${sev.chipText} ${sev.chipBorder}`}>
        {sev.label}
      </span>

      <ArrowRight size={13} className="text-gray-300 shrink-0" />
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function TodayActionsCard({
  actions = [],
  onNavigate,
  title = 'À traiter aujourd\'hui',
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-50 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        {actions.length > 0 && (
          <span className="text-xs text-gray-400">{actions.length} élément{actions.length > 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Body */}
      {actions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
          <div className="w-9 h-9 rounded-full bg-emerald-50 flex items-center justify-center">
            <CheckCircle2 size={18} className="text-emerald-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Aucune action requise</p>
          <p className="text-xs text-gray-400">Toutes les priorités sont à jour.</p>
        </div>
      ) : (
        <div className="py-1 divide-y divide-gray-50">
          {actions.map((action, i) => (
            <ActionItem key={action.id} action={action} index={i} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}
