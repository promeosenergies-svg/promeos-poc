/**
 * PROMEOS Design System — PageShell
 * Standard page wrapper: icon + title + subtitle + actions + children.
 * Replaces the repeated <div className="px-6 py-6"><h2>...</h2></div> pattern.
 */
import { tint } from './colorTokens';

export default function PageShell({
  icon: Icon,
  title,
  subtitle,
  actions,
  children,
  className = '',
  tintColor = 'text-blue-600',
  moduleKey,
}) {
  return (
    <div className={`px-6 py-6 space-y-6 animate-[slideInUp_0.3s_ease-out] ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0 flex-1" style={{ minWidth: '280px' }}>
          {Icon && (
            <Icon
              size={26}
              className={`${moduleKey ? tint.module(moduleKey).icon() : tintColor} shrink-0`}
            />
          )}
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-bold text-gray-900 truncate">{title}</h1>
            {subtitle && <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 flex-wrap shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
