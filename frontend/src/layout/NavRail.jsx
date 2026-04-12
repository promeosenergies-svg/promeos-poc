/**
 * PROMEOS — NavRail (Premium 5-Module Rail)
 * Glass surface with tinted active states from TINT_PALETTE.
 * Tooltip on hover. Logo at top, expert badge at bottom.
 */
import { TooltipPortal } from '../ui';
import { NAV_MODULES, TINT_PALETTE } from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';

/* ── Module → badge key mapping ── */
const MODULE_BADGE_KEY = {
  conformite: 'alerts',
  energie: 'monitoring',
};

/* ── Rail icon button for one module ── */
function RailIcon({ mod, isActive, onClick, badgeCount }) {
  const t = TINT_PALETTE[mod.tint] || TINT_PALETTE.slate;
  const Icon = mod.icon;

  return (
    <TooltipPortal text={mod.label} position="right">
      <button
        onClick={() => onClick(mod.key)}
        className={`relative flex flex-col items-center justify-center w-12 h-14 rounded-xl transition-all duration-150
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
          ${
            isActive
              ? `${t.railActiveBg} ring-1 ${t.railActiveRing} ${t.railActiveText}`
              : 'text-slate-400 hover:bg-slate-100/60 hover:text-slate-600'
          }`}
        aria-label={mod.label}
        aria-current={isActive ? 'true' : undefined}
      >
        <Icon size={20} />
        {badgeCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 flex items-center justify-center text-[8px] font-bold bg-red-500 text-white rounded-full leading-none">
            {badgeCount > 9 ? '9+' : badgeCount}
          </span>
        )}
        <span className="text-[10px] mt-0.5 leading-tight opacity-80">{mod.label}</span>
      </button>
    </TooltipPortal>
  );
}

/* ── Main Rail ── */
export default function NavRail({ activeModule, onSelectModule, badges = {} }) {
  const { isExpert } = useExpertMode();

  const visibleModules = isExpert ? NAV_MODULES : NAV_MODULES.filter((m) => !m.expertOnly);

  return (
    <div
      className="flex flex-col items-center w-16 h-screen bg-slate-50/60 backdrop-blur-sm border-r border-slate-200/60 shrink-0 py-3 gap-1"
      role="navigation"
      aria-label="Modules"
    >
      {/* Logo */}
      <div className="flex items-center justify-center w-10 h-10 mb-3 rounded-xl bg-white/80 shadow-sm ring-1 ring-slate-200/50">
        <span className="text-lg font-bold text-blue-600">P</span>
      </div>

      {/* Module icons */}
      <div className="flex-1 flex flex-col items-center gap-1.5">
        {visibleModules.map((mod) => (
          <RailIcon
            key={mod.key}
            mod={mod}
            isActive={activeModule === mod.key}
            onClick={onSelectModule}
            badgeCount={badges[MODULE_BADGE_KEY[mod.key]] || 0}
          />
        ))}
      </div>

      {/* Expert badge */}
      {isExpert && (
        <div className="mt-auto pt-2" title="Affiche source, confiance et détails techniques">
          <span className="px-1.5 py-0.5 text-[9px] font-bold bg-indigo-50 text-indigo-600 rounded tracking-wide ring-1 ring-indigo-200/50">
            PRO
          </span>
        </div>
      )}
    </div>
  );
}
