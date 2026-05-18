import FilterBar from '../../../ui/FilterBar';
import Select from '../../../ui/Select';

import { COPY, LIFECYCLE_LABELS, LIFECYCLE_ORDER } from '../constants';

/**
 * M2-5.2 — Filtres de la liste V4.
 *
 * Filtre lifecycle uniquement (recherche texte différée — backend M2-4.2 sans
 * paramètre search). Domaine visible en colonne, pas filtrable ici.
 *
 * Le filtre est client-side sur la page courante (cf. `filterScopeNote`) — un
 * micro-texte discret le signale dès qu'un filtre est actif (dette UX MV3
 * assumée et tracée ; vrai filtrage serveur = chantier backend M3).
 */
export function ListFilterBar({ stateFilter, onStateFilterChange }) {
  const options = [
    { value: '', label: COPY.filterAllStates },
    ...LIFECYCLE_ORDER.map((state) => ({
      value: state,
      label: LIFECYCLE_LABELS[state],
    })),
  ];

  return (
    <div>
      <FilterBar>
        <Select
          label={COPY.filterByState}
          aria-label={COPY.filterByState}
          value={stateFilter || ''}
          onChange={(e) => onStateFilterChange(e.target.value || null)}
          options={options}
        />
      </FilterBar>
      {stateFilter && <p className="text-xs text-gray-400 mt-1 px-1">{COPY.filterScopeNote}</p>}
    </div>
  );
}
