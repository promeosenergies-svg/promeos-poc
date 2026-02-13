/**
 * PROMEOS Design System — KpiCard
 * Unified KPI display card with icon, value, sub-metric, and optional badge.
 */
import Card, { CardBody } from './Card';
import Badge from './Badge';

export default function KpiCard({ icon: Icon, title, value, sub, badge, badgeStatus, color = 'bg-blue-600', onClick, className = '' }) {
  const Wrapper = onClick ? 'button' : 'div';
  return (
    <Card className={`${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}>
      <CardBody>
        <Wrapper
          onClick={onClick}
          className={`flex items-start gap-4 w-full text-left ${onClick ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg' : ''}`}
          {...(onClick ? { type: 'button' } : {})}
        >
          {Icon && (
            <div className={`p-3 rounded-lg ${color} shrink-0`}>
              <Icon size={22} className="text-white" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value ?? '-'}</p>
            {sub && <p className="text-sm text-gray-500 mt-0.5">{sub}</p>}
          </div>
          {badge && <Badge status={badgeStatus}>{badge}</Badge>}
        </Wrapper>
      </CardBody>
    </Card>
  );
}
