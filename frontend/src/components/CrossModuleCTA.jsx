/**
 * PROMEOS — Cross-Module CTA
 * Bannière de suggestion pour transformer la nav passive en funnel.
 * Usage: <CrossModuleCTA icon={Zap} title="..." desc="..." to="..." label="..." tint="violet" />
 */
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const TINT_CLASSES = {
  violet: 'from-violet-50 to-purple-50 border-violet-100 text-violet-700 hover:bg-violet-100',
  amber: 'from-amber-50 to-yellow-50 border-amber-100 text-amber-700 hover:bg-amber-100',
  emerald: 'from-emerald-50 to-teal-50 border-emerald-100 text-emerald-700 hover:bg-emerald-100',
  indigo: 'from-indigo-50 to-blue-50 border-indigo-100 text-indigo-700 hover:bg-indigo-100',
  yellow: 'from-yellow-50 to-amber-50 border-yellow-100 text-yellow-700 hover:bg-yellow-100',
};

export default function CrossModuleCTA({ icon: Icon, title, desc, to, label, tint = 'violet' }) {
  const tintClass = TINT_CLASSES[tint] || TINT_CLASSES.violet;
  const [gradient, border, text, hover] = tintClass.split(' ');

  return (
    <Link
      to={to}
      className={`flex items-center gap-3 p-4 rounded-xl border ${border} bg-gradient-to-r ${gradient} transition-all group`}
    >
      {Icon && (
        <div className="p-2 bg-white/80 rounded-lg shrink-0">
          <Icon size={18} className={text} />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <h4 className={`text-sm font-semibold ${text}`}>{title}</h4>
        <p className="text-xs text-gray-600 mt-0.5 truncate">{desc}</p>
      </div>
      <div
        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white/80 border ${border} text-xs font-medium ${text} group-hover:${hover} transition`}
      >
        {label}
        <ArrowRight size={12} />
      </div>
    </Link>
  );
}
