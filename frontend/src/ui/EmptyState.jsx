/**
 * PROMEOS — EmptyState standardisé
 * 4 variantes : empty (aucune donnée), partial (données partielles),
 * unconfigured (non configuré), error (erreur légère actionnable).
 */
import { Inbox, AlertTriangle, Settings, Info } from 'lucide-react';

const VARIANTS = {
  empty: { icon: Inbox, title: 'Aucune donnée', color: 'text-gray-400', bg: 'bg-gray-50' },
  partial: { icon: Info, title: 'Données partielles', color: 'text-amber-500', bg: 'bg-amber-50' },
  unconfigured: {
    icon: Settings,
    title: 'Non configuré',
    color: 'text-blue-500',
    bg: 'bg-blue-50',
  },
  error: { icon: AlertTriangle, title: 'Erreur', color: 'text-red-500', bg: 'bg-red-50' },
};

export default function EmptyState({
  variant = 'empty',
  icon: CustomIcon,
  title,
  text,
  ctaLabel,
  onCta,
  actions,
}) {
  const v = VARIANTS[variant] || VARIANTS.empty;
  const Icon = CustomIcon || v.icon;

  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 rounded-lg ${v.bg}`}>
      <div
        className={`w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center mb-3 ${v.color}`}
      >
        <Icon size={24} />
      </div>
      <h3 className="text-sm font-semibold text-gray-700 mb-1">{title || v.title}</h3>
      {text && <p className="text-xs text-gray-500 text-center max-w-sm mb-3">{text}</p>}
      {ctaLabel && onCta && (
        <button
          onClick={onCta}
          className="text-sm bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700"
        >
          {ctaLabel}
        </button>
      )}
      {actions && <div className="flex gap-2 mt-2">{actions}</div>}
    </div>
  );
}
