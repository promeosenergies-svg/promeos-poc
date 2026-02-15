/**
 * PROMEOS — NavRail (Premium 5-Module Rail)
 * Vertical icon strip. Active module gets tinted bg + ring + colored icon.
 * Tooltip on hover. Logo at top, expert badge at bottom.
 */
import { Tooltip } from '../ui';
import { NAV_MODULES, SIDEBAR_ITEM_TINTS } from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';

/* ── Rail icon button for one module ── */
function RailIcon({ mod, isActive, onClick }) {
  const tint = SIDEBAR_ITEM_TINTS[mod.tint] || SIDEBAR_ITEM_TINTS.blue;
  const Icon = mod.icon;

  return (
    <Tooltip text={mod.label} position="right">
      <button
        onClick={() => onClick(mod.key)}
        className={`relative flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-150
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
          ${isActive
            ? `${tint.activeBg} ring-1 ${tint.activeBorder.replace('border-', 'ring-')} ${tint.activeText}`
            : 'text-slate-400 hover:bg-slate-50 hover:text-slate-600'
          }`}
        aria-label={mod.label}
        aria-current={isActive ? 'true' : undefined}
      >
        <Icon size={20} />
      </button>
    </Tooltip>
  );
}

/* ── Main Rail ── */
export default function NavRail({ activeModule, onSelectModule }) {
  const { isExpert } = useExpertMode();

  const visibleModules = isExpert
    ? NAV_MODULES
    : NAV_MODULES.filter((m) => !m.expertOnly);

  return (
    <div
      className="flex flex-col items-center w-16 h-screen bg-white border-r border-slate-200/70 shrink-0 py-3 gap-1"
      role="navigation"
      aria-label="Modules"
    >
      {/* Logo */}
      <div className="flex items-center justify-center w-10 h-10 mb-3">
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
          />
        ))}
      </div>

      {/* Expert badge */}
      {isExpert && (
        <div className="mt-auto pt-2">
          <span className="px-1.5 py-0.5 text-[9px] font-bold bg-indigo-50 text-indigo-600 rounded tracking-wide">
            PRO
          </span>
        </div>
      )}
    </div>
  );
}
