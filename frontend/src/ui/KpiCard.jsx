/**
 * PROMEOS Design System — KpiCard
 * Unified KPI display card with icon, value, sub-metric, and optional badge.
 *
 * Icon prop accepts:
 *   - A component reference: icon={Target}
 *   - A React element:       icon={<Target size={18} />}
 *   - null/undefined:        no icon rendered
 *
 * Also accepts `label` as alias for `title`, and `sublabel` as alias for `sub`.
 */
import { isValidElement, createElement } from 'react';
import Card, { CardBody } from './Card';
import Badge from './Badge';

/**
 * Resolve an icon prop to a valid React node.
 * Supports: Component reference, ReactElement, or null.
 * Exported for unit testing.
 */
export function resolveIcon(icon, props = {}) {
  if (isValidElement(icon)) return icon;
  if (typeof icon === 'function') return createElement(icon, props);
  return null;
}

export default function KpiCard({
  icon,
  title,
  label,
  value,
  sub,
  sublabel,
  badge,
  badgeStatus,
  color = 'bg-blue-600',
  onClick,
  className = '',
}) {
  const iconNode = resolveIcon(icon, { size: 18, className: 'text-white' });

  // Alias: label → title, sublabel → sub
  const resolvedTitle = title || label;
  const resolvedSub = sub || sublabel;

  const Wrapper = onClick ? 'button' : 'div';
  return (
    <Card
      className={`${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}
    >
      <CardBody>
        <Wrapper
          onClick={onClick}
          className={`flex items-start gap-3 w-full text-left ${onClick ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg' : ''}`}
          {...(onClick ? { type: 'button' } : {})}
        >
          {iconNode && <div className={`p-2 rounded-lg ${color} shrink-0 mt-0.5`}>{iconNode}</div>}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider truncate flex-1 min-w-0">
                {resolvedTitle}
              </p>
              {badge && (
                <span className="shrink-0">
                  <Badge status={badgeStatus}>{badge}</Badge>
                </span>
              )}
            </div>
            <p
              className="text-2xl font-bold text-gray-900 mt-1 tabular-nums break-words leading-tight"
              title={typeof value === 'string' ? value : undefined}
            >
              {value ?? '-'}
            </p>
            {resolvedSub && (
              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{resolvedSub}</p>
            )}
          </div>
        </Wrapper>
      </CardBody>
    </Card>
  );
}

/**
 * KpiCardInline — flat inline variant for secondary KPI displays.
 * Replaces local KpiCard duplicates in BacsOpsPanel, SiteBillingMini, AnomaliesPage, AperPage.
 */
export function KpiCardInline({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-gray-800',
  iconBg = 'bg-gray-50',
  loading,
  unit,
}) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-3 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${iconBg} shrink-0`}>
        <Icon size={16} className={color} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] text-gray-400 font-medium uppercase tracking-wider">{label}</p>
        {loading ? (
          <div className="h-5 w-12 bg-gray-100 rounded animate-pulse mt-0.5" />
        ) : (
          <p className="text-base font-bold text-gray-900 leading-tight break-words">
            {value}
            {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
          </p>
        )}
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

/**
 * KpiCardCompact — denser variant with active ring and click-to-filter.
 * Promoted from Patrimoine.jsx inline to shared design system.
 */
export function KpiCardCompact({ icon: Icon, color, label, value, detail, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-3 rounded-xl border bg-white transition-all
        ${active ? 'ring-2 ring-blue-500 border-blue-200 shadow-sm' : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'}`}
    >
      <div className="flex items-center gap-2.5">
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center shrink-0`}>
          <Icon size={16} className="text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider leading-none">
            {label}
          </p>
          <p className="text-lg font-bold text-gray-900 leading-tight mt-0.5">{value}</p>
        </div>
      </div>
      {detail && <p className="text-[11px] text-gray-400 mt-1 pl-[42px] leading-tight">{detail}</p>}
    </button>
  );
}
