/**
 * PROMEOS — ExecutiveKpiRow (Cockpit V2)
 * 4 executive KPI tuiles: Conformité / Risque / Maturité / Couverture données.
 * Data from buildExecutiveKpis(kpis, sites) — no hard-coded colors.
 *
 * Props:
 *   kpis       {ExecKpi[]}  — from buildExecutiveKpis()
 *   onNavigate {fn}         — navigate(path)
 */
import { ShieldCheck, TrendingDown, BarChart3, Database } from 'lucide-react';
import { KPI_ACCENTS } from '../../ui/colorTokens';

// ── Icon map ──────────────────────────────────────────────────────────────────

const KPI_ICONS = {
  conformite: ShieldCheck,
  risque:     TrendingDown,
  maturite:   BarChart3,
  couverture: Database,
  neutral:    Database,
};

// ── Status dot ────────────────────────────────────────────────────────────────

const STATUS_DOT = {
  crit:    'bg-red-500',
  warn:    'bg-amber-400',
  ok:      'bg-emerald-500',
  neutral: 'bg-gray-300',
};

// ── KPI tile ──────────────────────────────────────────────────────────────────

function KpiTile({ kpi, onNavigate }) {
  const acc = KPI_ACCENTS[kpi.accentKey] || KPI_ACCENTS.neutral;
  const Icon = KPI_ICONS[kpi.id] || KPI_ICONS[kpi.accentKey] || Database;
  const dotClass = STATUS_DOT[kpi.status] || STATUS_DOT.neutral;
  const El = kpi.path ? 'button' : 'div';

  return (
    <El
      {...(kpi.path ? { onClick: () => onNavigate?.(kpi.path), type: 'button' } : {})}
      className={`rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-start gap-3 transition-shadow
        ${kpi.path ? 'hover:shadow-sm cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500' : ''}`}
    >
      {/* Icon pill */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${acc.iconBg}`}>
        <Icon size={18} className={acc.iconText} />
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">{kpi.label}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <p className="text-lg font-bold text-gray-900 leading-tight truncate">{kpi.value}</p>
          <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} aria-hidden="true" />
        </div>
        {kpi.sub && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">{kpi.sub}</p>
        )}
      </div>
    </El>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ExecutiveKpiRow({ kpis = [], onNavigate }) {
  if (!kpis.length) return null;

  return (
    <div className={`grid gap-3 grid-cols-2 ${kpis.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
      {kpis.map((kpi) => (
        <KpiTile key={kpi.id} kpi={kpi} onNavigate={onNavigate} />
      ))}
    </div>
  );
}
