/**
 * PROMEOS — ExecutiveSummaryCard (Cockpit V2)
 * "Résumé exécutif" — 3 bullets décideur (positif / négatif / opportunité).
 * Data from buildExecutiveSummary(kpis, topSites).
 *
 * Props:
 *   bullets  {ExecBullet[]} — from buildExecutiveSummary()
 *   onNavigate {fn}         — navigate(path)
 */
import { CheckCircle2, XCircle, AlertTriangle, Lightbulb } from 'lucide-react';

// ── Bullet type config ────────────────────────────────────────────────────────

const TYPE_CFG = {
  positive:    { Icon: CheckCircle2, iconClass: 'text-emerald-500', rowBg: '' },
  negative:    { Icon: XCircle,      iconClass: 'text-red-500',     rowBg: '' },
  warn:        { Icon: AlertTriangle,iconClass: 'text-amber-500',   rowBg: '' },
  opportunity: { Icon: Lightbulb,    iconClass: 'text-blue-500',    rowBg: '' },
};

// ── Bullet row ────────────────────────────────────────────────────────────────

function ExecBulletRow({ bullet, onNavigate }) {
  const cfg = TYPE_CFG[bullet.type] || TYPE_CFG.warn;
  const { Icon } = cfg;
  const El = bullet.path ? 'button' : 'div';

  return (
    <El
      {...(bullet.path ? { onClick: () => onNavigate?.(bullet.path), type: 'button' } : {})}
      className={`flex items-start gap-3 px-4 py-3 text-left w-full transition
        ${bullet.path ? 'hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg cursor-pointer' : ''}`}
    >
      <Icon size={15} className={`shrink-0 mt-0.5 ${cfg.iconClass}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 leading-snug">{bullet.label}</p>
        {bullet.sub && (
          <p className="text-xs text-gray-500 mt-0.5">{bullet.sub}</p>
        )}
      </div>
    </El>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ExecutiveSummaryCard({ bullets = [], onNavigate }) {
  if (!bullets.length) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">
        Résumé exécutif
      </p>
      <div className="rounded-xl border border-gray-100 bg-white divide-y divide-gray-50 shadow-sm">
        {bullets.map((b) => (
          <ExecBulletRow key={b.id} bullet={b} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}
