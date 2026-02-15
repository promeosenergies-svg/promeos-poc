/**
 * PROMEOS — NavRail
 * Vertical icon rail: 5 module icons with active state + tooltip.
 * Always visible (~56px wide). Drives which module's panel is open.
 */
import { Tooltip } from '../ui';

/* ── Rail active/hover tints per module ── */
const RAIL_TINTS = {
  cockpit:    { active: 'bg-blue-50 text-blue-600',    hover: 'hover:bg-blue-50/50' },
  operations: { active: 'bg-emerald-50 text-emerald-600', hover: 'hover:bg-emerald-50/50' },
  analyse:    { active: 'bg-indigo-50 text-indigo-600',  hover: 'hover:bg-indigo-50/50' },
  marche:     { active: 'bg-violet-50 text-violet-600',  hover: 'hover:bg-violet-50/50' },
  donnees:    { active: 'bg-slate-100 text-slate-700',   hover: 'hover:bg-slate-50' },
};

export default function NavRail({ modules, activeModule, onModuleSelect, hasBadge }) {
  return (
    <div className="flex flex-col items-center w-14 bg-white border-r border-slate-200/70 py-3 gap-1 shrink-0" role="tablist" aria-label="Modules">
      {/* Logo */}
      <div className="mb-3 flex items-center justify-center">
        <span className="text-lg font-bold text-blue-600">P</span>
      </div>

      {/* Module icons */}
      {modules.map((mod) => {
        const isActive = activeModule === mod.key;
        const tint = RAIL_TINTS[mod.key] || RAIL_TINTS.cockpit;
        const Icon = mod.icon;
        const badge = hasBadge?.(mod.key);

        return (
          <Tooltip key={mod.key} text={mod.label} position="right">
            <button
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${mod.key}`}
              onClick={() => onModuleSelect(mod.key)}
              className={`relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-150
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
                ${isActive
                  ? tint.active
                  : `text-slate-400 ${tint.hover} hover:text-slate-600`
                }`}
            >
              <Icon size={20} />
              {badge && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              )}
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}
