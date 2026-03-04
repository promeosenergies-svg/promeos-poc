/**
 * PROMEOS — HealthSummary (Health & Messaging System)
 * Unified health banner: GREEN / AMBER / RED.
 * Reusable across Dashboard, Cockpit, Conformite.
 *
 * Props:
 *   healthState  {HealthState} — from computeHealthState()
 *   onNavigate   {fn}          — navigate(path)
 *   compact      {boolean}     — true = mini banner (for sub-pages), false = full card
 */
import { Sparkles, AlertCircle, AlertTriangle, ArrowRight, Plus } from 'lucide-react';
import { Button } from '../ui';
import { SEVERITY_TINT } from '../ui/colorTokens';

const LEVEL_CONFIG = {
  GREEN: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-100',
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
    titleText: 'text-emerald-800',
    subtitleText: 'text-emerald-600',
    Icon: Sparkles,
  },
  AMBER: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    iconBg: 'bg-amber-100',
    iconText: 'text-amber-600',
    titleText: 'text-amber-800',
    subtitleText: 'text-amber-700',
    Icon: AlertTriangle,
  },
  RED: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    iconBg: 'bg-red-100',
    iconText: 'text-red-600',
    titleText: 'text-red-800',
    subtitleText: 'text-red-700',
    Icon: AlertCircle,
  },
};

function ReasonRow({ reason, onNavigate, onCreateAction }) {
  const sev = SEVERITY_TINT[reason.severity] || SEVERITY_TINT.neutral;
  return (
    <div className="flex items-center gap-1 px-1">
      <button
        onClick={() => onNavigate?.(reason.link)}
        className="flex-1 flex items-center justify-between gap-3 px-3 py-2 hover:bg-white/60 transition text-left rounded-lg focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${sev.dot}`} />
          <span className="text-sm text-gray-700 truncate">{reason.label}</span>
        </div>
        <ArrowRight size={13} className="text-gray-300 shrink-0" />
      </button>
      {onCreateAction && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCreateAction(reason);
          }}
          className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition shrink-0"
          title="Créer une action"
        >
          <Plus size={12} /> Action
        </button>
      )}
    </div>
  );
}

export default function HealthSummary({
  healthState,
  onNavigate,
  onCreateAction,
  compact = false,
  trend,
}) {
  if (!healthState) return null;

  const cfg = LEVEL_CONFIG[healthState.level] || LEVEL_CONFIG.GREEN;
  const { Icon } = cfg;

  return (
    <div className={`rounded-xl border ${cfg.bg} ${cfg.border}`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-8 h-8 rounded-lg ${cfg.iconBg} flex items-center justify-center shrink-0`}
          >
            <Icon size={16} className={cfg.iconText} />
          </div>
          <div className="min-w-0">
            <p className={`text-sm font-semibold ${cfg.titleText}`}>{healthState.title}</p>
            <p className={`text-xs ${cfg.subtitleText} leading-snug`}>{healthState.subtitle}</p>
            {trend && trend.direction !== 'stable' && (
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-medium mt-0.5 ${
                  trend.direction === 'improving' ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                {trend.direction === 'improving' ? '↓' : '↑'} {trend.label}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {healthState.secondaryCta && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate?.(healthState.secondaryCta.to)}
              className="text-xs"
            >
              {healthState.secondaryCta.label}
            </Button>
          )}
          <Button
            size="sm"
            variant={healthState.level === 'GREEN' ? 'ghost' : 'secondary'}
            onClick={() => onNavigate?.(healthState.primaryCta.to)}
          >
            {healthState.primaryCta.label} <ArrowRight size={14} />
          </Button>
        </div>
      </div>

      {/* Reasons (full mode only, skip for GREEN) */}
      {!compact && healthState.level !== 'GREEN' && healthState.reasons.length > 0 && (
        <div className="border-t border-black/5 px-1 py-1">
          {healthState.reasons.map((reason) => (
            <ReasonRow
              key={reason.id}
              reason={reason}
              onNavigate={onNavigate}
              onCreateAction={onCreateAction}
            />
          ))}
        </div>
      )}
    </div>
  );
}
