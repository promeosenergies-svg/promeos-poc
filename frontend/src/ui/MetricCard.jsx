/**
 * PROMEOS Design System — MetricCard v3 (Phase 6)
 * Neutral-first + controlled accent: left bar + icon pill + optional trend.
 * No colored backgrounds. Accent via 3px left border + tinted icon container.
 */
import Card, { CardBody } from './Card';
import { ACCENT_BAR, KPI_ACCENTS } from './colorTokens';

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

/**
 * MetricCard v3
 * @param {string} accent - KPI accent key from colorTokens (conformite, risque, alertes, etc.)
 * @param {React.ComponentType} icon - Lucide icon to display in tinted pill
 * @param {string} label - KPI label (uppercase)
 * @param {string|number} value - Main value
 * @param {string} sub - Secondary text
 * @param {string} trend - 'up' | 'down' | 'flat'
 * @param {string} trendLabel - Trend text
 * @param {string} status - StatusDot severity (ok, warn, crit, info, neutral)
 * @param {Function} onClick - Click handler
 */
export default function MetricCard({
  label,
  value,
  sub,
  trend,
  trendLabel,
  status,
  accent,
  icon: Icon,
  onClick,
  className = '',
}) {
  const Wrapper = onClick ? 'button' : 'div';
  const accentConfig = accent ? KPI_ACCENTS[accent] || KPI_ACCENTS.neutral : null;
  const barColor = accentConfig ? ACCENT_BAR[accentConfig.accent] || ACCENT_BAR.gray : null;

  return (
    <Card
      className={`${onClick ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all' : ''} ${className} overflow-hidden`}
    >
      <div className="flex">
        {/* Left accent bar */}
        {barColor && <div className={`w-[3px] shrink-0 ${barColor} rounded-l-lg`} />}
        <CardBody className="flex-1">
          <Wrapper
            onClick={onClick}
            className={`w-full text-left ${onClick ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg' : ''}`}
            {...(onClick ? { type: 'button' } : {})}
          >
            <div className="flex items-start gap-3">
              {/* Icon pill */}
              {Icon && accentConfig && (
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${accentConfig.iconBg}`}
                >
                  <Icon size={18} className={accentConfig.iconText} />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                    {label}
                  </p>
                  {status && <StatusDot status={status} />}
                </div>
                <p className="text-2xl font-bold text-gray-900">{value ?? '\u2014'}</p>
                <div className="flex items-center gap-2 mt-1">
                  {sub && <p className="text-sm text-gray-500">{sub}</p>}
                  {trend && (
                    <span
                      className={`text-xs font-medium ${TREND_STYLE[trend] || TREND_STYLE.flat}`}
                    >
                      {TREND_ARROW[trend]} {trendLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Wrapper>
        </CardBody>
      </div>
    </Card>
  );
}
