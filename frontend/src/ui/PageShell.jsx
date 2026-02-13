/**
 * PROMEOS Design System — PageShell
 * Standard page wrapper: icon + title + subtitle + actions + children.
 * Replaces the repeated <div className="px-6 py-6"><h2>...</h2></div> pattern.
 */
export default function PageShell({ icon: Icon, title, subtitle, actions, children, className = '' }) {
  return (
    <div className={`px-6 py-6 space-y-6 ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          {Icon && <Icon size={26} className="text-blue-600 shrink-0" />}
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 truncate">{title}</h1>
            {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
