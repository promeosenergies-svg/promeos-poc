/**
 * PROMEOS Design System — ActiveFiltersBar (A.4)
 * Barre contextuelle affichant les filtres actifs avec chips, compteur, et reset.
 *
 * Props:
 *   filters   : [{ key, label, value, onRemove? }] — filtres actifs
 *   total     : number — nombre total de résultats (non filtré)
 *   filtered  : number — nombre de résultats après filtre
 *   onReset   : () => void — réinitialise tous les filtres
 *   className : string — classes CSS additionnelles
 */
import { X, Filter } from 'lucide-react';

export default function ActiveFiltersBar({
  filters = [],
  total,
  filtered,
  onReset,
  className = '',
}) {
  const active = filters.filter((f) => f.value != null && f.value !== '' && f.value !== 'all');
  const hasFilters = active.length > 0;

  if (!hasFilters && total == null) return null;

  return (
    <div
      className={`flex items-center gap-2 flex-wrap text-xs ${className}`}
      data-testid="active-filters-bar"
    >
      {/* Compteur de résultats */}
      {filtered != null && total != null && (
        <span className="text-gray-500 font-medium" data-testid="filter-count">
          {filtered === total
            ? `${total} résultat${total !== 1 ? 's' : ''}`
            : `${filtered} sur ${total}`}
        </span>
      )}

      {/* Séparateur */}
      {hasFilters && filtered != null && (
        <span className="text-gray-300">·</span>
      )}

      {/* Chips des filtres actifs */}
      {active.map((f) => (
        <span
          key={f.key}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200"
          data-testid={`filter-chip-${f.key}`}
        >
          <Filter size={10} />
          <span className="font-medium">{f.label}</span>
          <span className="text-blue-500">: {f.value}</span>
          {f.onRemove && (
            <button
              onClick={f.onRemove}
              className="ml-0.5 p-0.5 rounded-full hover:bg-blue-100 transition"
              aria-label={`Retirer le filtre ${f.label}`}
            >
              <X size={10} />
            </button>
          )}
        </span>
      ))}

      {/* Reset global */}
      {hasFilters && onReset && (
        <button
          onClick={onReset}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition"
          data-testid="filter-reset"
        >
          <X size={12} />
          Réinitialiser
        </button>
      )}
    </div>
  );
}
