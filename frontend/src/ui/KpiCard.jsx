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
  title, label,
  value,
  sub, sublabel,
  badge, badgeStatus,
  color = 'bg-blue-600',
  onClick,
  className = '',
}) {
  const iconNode = resolveIcon(icon, { size: 22, className: 'text-white' });

  // Alias: label → title, sublabel → sub
  const resolvedTitle = title || label;
  const resolvedSub = sub || sublabel;

  const Wrapper = onClick ? 'button' : 'div';
  return (
    <Card className={`${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}>
      <CardBody>
        <Wrapper
          onClick={onClick}
          className={`flex items-start gap-4 w-full text-left ${onClick ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg' : ''}`}
          {...(onClick ? { type: 'button' } : {})}
        >
          {iconNode && (
            <div className={`p-3 rounded-lg ${color} shrink-0`}>
              {iconNode}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider truncate">{resolvedTitle}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1 truncate">{value ?? '-'}</p>
            {resolvedSub && <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{resolvedSub}</p>}
          </div>
          {badge && <Badge status={badgeStatus}>{badge}</Badge>}
        </Wrapper>
      </CardBody>
    </Card>
  );
}
