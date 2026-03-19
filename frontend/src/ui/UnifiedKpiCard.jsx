/**
 * PROMEOS — UnifiedKpiCard
 * Composant KPI canonique unique avec metadata traçable.
 * Remplace progressivement KpiCard/MetricCard/KpiTile/MiniCard.
 */

const STATUS_STYLES = {
  success: 'border-l-green-500 bg-green-50/30',
  warning: 'border-l-amber-500 bg-amber-50/30',
  danger: 'border-l-red-500 bg-red-50/30',
  info: 'border-l-blue-500 bg-blue-50/30',
  neutral: 'border-l-gray-300 bg-white',
};

const STATUS_DOT = {
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
  neutral: 'bg-gray-400',
};

export default function UnifiedKpiCard({
  title,
  value,
  unit,
  periodLabel,
  scopeLabel,
  status = 'neutral',
  lastUpdatedAt,
  tooltip,
  helperText,
  icon: Icon,
  trend,
  trendLabel,
  onClick,
  children,
}) {
  const borderStyle = STATUS_STYLES[status] || STATUS_STYLES.neutral;
  const dotStyle = STATUS_DOT[status] || STATUS_DOT.neutral;

  return (
    <div
      className={`border border-l-4 rounded-lg p-4 transition-shadow ${borderStyle} ${onClick ? 'cursor-pointer hover:shadow-md' : ''}`}
      onClick={onClick}
      title={tooltip}
    >
      {/* Header: icon + title + status dot */}
      <div className="flex items-center gap-2 mb-2">
        {Icon && (
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
            <Icon size={16} className="text-gray-600" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide truncate">
              {title}
            </span>
            <span className={`w-2 h-2 rounded-full shrink-0 ${dotStyle}`} />
          </div>
        </div>
      </div>

      {/* Value + unit */}
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-2xl font-bold text-gray-900">{value ?? '—'}</span>
        {unit && <span className="text-sm text-gray-400">{unit}</span>}
        {trend && (
          <span
            className={`text-xs ml-2 ${trend > 0 ? 'text-red-600' : trend < 0 ? 'text-green-600' : 'text-gray-400'}`}
          >
            {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {trendLabel || ''}
          </span>
        )}
      </div>

      {/* Helper text */}
      {helperText && <p className="text-xs text-gray-500 mb-2">{helperText}</p>}

      {/* Children (custom content) */}
      {children}

      {/* Metadata footer: period + scope + lastUpdated */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100 text-[10px] text-gray-400">
        {scopeLabel && <span>{scopeLabel}</span>}
        {scopeLabel && periodLabel && <span>·</span>}
        {periodLabel && <span>{periodLabel}</span>}
        {lastUpdatedAt && (
          <>
            <span>·</span>
            <span>
              {typeof lastUpdatedAt === 'string'
                ? lastUpdatedAt
                : new Date(lastUpdatedAt).toLocaleDateString('fr-FR')}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * UnifiedKpiCardGrid — grid wrapper for consistent layout.
 */
export function UnifiedKpiCardGrid({ children, cols = 4 }) {
  const colClass = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  };
  return <div className={`grid ${colClass[cols] || colClass[4]} gap-4`}>{children}</div>;
}
