/**
 * PROMEOS — ModuleLaunchers (Sprint WOW Phase 7.0)
 * Row of 5 navigation tiles using tint.module() — no hard-coded colors.
 * Marché + Admin hidden for non-Expert users.
 *
 * Props:
 *   kpis       {object}   — from Cockpit kpis useMemo
 *   isExpert   {boolean}
 *   onNavigate {fn}       — navigate(path)
 */
import { NAV_MODULES } from '../../layout/NavRegistry';
import { tint } from '../../ui/colorTokens';
import { formatPercentFR } from '../../utils/format';

// ── Module → route + key metric ──────────────────────────────────────────────

function getModuleConfig(moduleKey, kpis) {
  switch (moduleKey) {
    case 'cockpit':
      return {
        route: '/cockpit',
        metric:
          kpis.total > 0 ? `${kpis.total} site${kpis.total > 1 ? 's' : ''} actifs` : 'Aucun site',
        cta: 'Vue executive',
      };
    case 'operations':
      return {
        route: '/conformite',
        metric:
          kpis.compliance_score != null
            ? `Score conformité : ${Math.round(kpis.compliance_score)} / 100`
            : kpis.total > 0
              ? `${kpis.conformes} / ${kpis.total} sites conformes`
              : 'Conformité',
        cta: 'Conformité',
      };
    case 'analyse':
      return {
        route: '/consommations/explorer',
        metric:
          kpis.couvertureDonnees != null
            ? `${formatPercentFR(kpis.couvertureDonnees)} données couvertes`
            : 'Consommations',
        cta: 'Consommations',
      };
    case 'marche':
      return {
        route: '/billing',
        metric: 'Factures & contrats',
        cta: 'Facturation',
      };
    case 'admin':
      return {
        route: '/import',
        metric: 'Connexions & données',
        cta: 'Administration',
      };
    default:
      return { route: '/', metric: '', cta: 'Ouvrir' };
  }
}

// ── Tile ──────────────────────────────────────────────────────────────────────

function ModuleTile({ mod, kpis, onNavigate }) {
  const cfg = getModuleConfig(mod.key, kpis);
  const t = tint.module(mod.key);
  const Icon = mod.icon;

  return (
    <button
      onClick={() => onNavigate?.(cfg.route)}
      className={`flex-1 rounded-xl px-4 py-4 flex flex-col items-start gap-2 text-left hover:shadow-sm transition focus-visible:ring-2 focus-visible:ring-blue-500 ${t.softBg()}`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${t.softBg()}`}>
        <Icon size={18} className={t.icon()} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-gray-800 truncate">{mod.label}</p>
        <p className="text-[11px] text-gray-500 leading-snug mt-0.5 truncate">{cfg.metric}</p>
      </div>
      <span className="text-[11px] font-medium text-gray-600">{cfg.cta} →</span>
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ModuleLaunchers({ kpis = {}, isExpert = false, onNavigate }) {
  const visibleModules = NAV_MODULES.filter((m) => !m.expertOnly || isExpert);

  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2.5">
        Explorer
      </p>
      <div className="flex gap-3 flex-wrap sm:flex-nowrap">
        {visibleModules.map((mod) => (
          <ModuleTile key={mod.key} mod={mod} kpis={kpis} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}
