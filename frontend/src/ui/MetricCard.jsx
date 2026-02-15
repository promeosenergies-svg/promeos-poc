/**
 * PROMEOS Design System — MetricCard v2
 * Neutral metric display: big value + label + optional trend + severity dot.
 * No colored backgrounds — severity communicated through StatusDot only.
 */
import Card, { CardBody } from './Card';

const TREND_STYLE = {
  up: 'text-red-600',
  down: 'text-green-600',
  flat: 'text-gray-400',
};

const TREND_ARROW = { up: '\u2191', down: '\u2193', flat: '\u2192' };

export function StatusDot({ status = 'neutral', className = '' }) {
  const colors = {
    ok: 'bg-green-500',
    warn: 'bg-amber-500',
    crit: 'bg-red-500',
    info: 'bg-blue-500',
    neutral: 'bg-gray-300',
  };
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${colors[status] || colors.neutral} ${className}`}
      aria-label={status}
    />
  );
}

export default function MetricCard({
  label,
  value,
  sub,
  trend,
  trendLabel,
  status,
  onClick,
  className = '',
}) {
  const Wrapper = onClick ? 'button' : 'div';
  return (
    <Card className={`${onClick ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all' : ''} ${className}`}>
      <CardBody>
        <Wrapper
          onClick={onClick}
          className={`w-full text-left ${onClick ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg' : ''}`}
          {...(onClick ? { type: 'button' } : {})}
        >
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
            {status && <StatusDot status={status} />}
          </div>
          <p className="text-2xl font-bold text-gray-900">{value ?? '\u2014'}</p>
          <div className="flex items-center gap-2 mt-1">
            {sub && <p className="text-sm text-gray-500">{sub}</p>}
            {trend && (
              <span className={`text-xs font-medium ${TREND_STYLE[trend] || TREND_STYLE.flat}`}>
                {TREND_ARROW[trend]} {trendLabel}
              </span>
            )}
          </div>
        </Wrapper>
      </CardBody>
    </Card>
  );
}
