/**
 * PROMEOS Design System — FilterBar
 * Horizontal filter row with children slots, optional reset button, and result count.
 */
import { X } from 'lucide-react';

export default function FilterBar({ children, onReset, count, className = '' }) {
  return (
    <div className={`flex items-center gap-3 flex-wrap ${className}`}>
      {children}
      {onReset && (
        <button
          onClick={onReset}
          className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 px-2 py-1.5 rounded hover:bg-gray-100 transition"
        >
          <X size={12} />
          Reset
        </button>
      )}
      {count != null && (
        <span className="ml-auto text-xs text-gray-400">
          {count} resultat{count !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  );
}
