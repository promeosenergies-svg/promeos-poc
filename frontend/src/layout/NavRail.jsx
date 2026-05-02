/**
 * PROMEOS — NavRail (Premium 6-Module Rail)
 * Glass surface with tinted active states from TINT_PALETTE.
 * Tooltip on hover. Logo at top, expert badge at bottom.
 *
 * Phase 1.E — P0.5 (audit navigation_audit_20260501.md §4 + §7 Q4) :
 * rendering du séparateur `groupBoundary` avant les modules qui portent
 * cette propriété (NAV_MODULES.patrimoine = 'config'). Discret, sans
 * label texte — anti-pattern §6.2 strict.
 */
import { Fragment } from 'react';
import { TooltipPortal } from '../ui';
import { TINT_PALETTE, getOrderedModules } from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';

/* ── Module → badge key mapping ── */
const MODULE_BADGE_KEY = {
  conformite: 'alerts',
  energie: 'monitoring',
};

/* ── Rail icon button for one module ── */
function RailIcon({ mod, isActive, onClick, badgeCount }) {
  const t = TINT_PALETTE[mod.tint] || TINT_PALETTE.slate;
  const Icon = mod.icon;
  const tipText = mod.label;

  return (
    <TooltipPortal text={tipText} position="right">
      <button
        onClick={() => onClick(mod.key)}
        className={`relative flex flex-col items-center justify-center w-12 h-14 rounded-xl transition-all duration-150
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
          ${
            isActive
              ? `${t.railActiveBg} ring-1 ${t.railActiveRing} ${t.railActiveText}`
              : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
          }`}
        aria-label={tipText}
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
  const { role } = useAuth();

  // Order modules based on user role (DG sees Achat first, EM sees Énergie first, etc.)
  const visibleModules = getOrderedModules(role, isExpert);

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
        {visibleModules.map((mod, idx) => (
          <Fragment key={mod.key}>
            {/* Phase 1.E — P0.5 : séparateur graphique avant les modules
                portant `groupBoundary` (Patrimoine = 'config'). Discret,
                sans label, non focusable — détache visuellement les
                modules de référentiel des modules opérationnels. */}
            {mod.groupBoundary && idx > 0 && (
              <div
                role="separator"
                aria-orientation="vertical"
                data-group-boundary={mod.groupBoundary}
                className="w-8 h-[0.5px] my-2 bg-slate-300/60"
              />
            )}
            <RailIcon
              mod={mod}
              isActive={activeModule === mod.key}
              onClick={onSelectModule}
              badgeCount={badges[MODULE_BADGE_KEY[mod.key]] || 0}
            />
          </Fragment>
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
