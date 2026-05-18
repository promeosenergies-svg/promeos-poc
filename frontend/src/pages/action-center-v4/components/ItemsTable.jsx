import { Table, Thead, Tbody, Tr, Th, Td } from '../../../ui/Table';

import { COPY, KIND_LABELS, A11Y_COPY } from '../constants';
import { formatRelativeDate } from '../utils/date';
import { LifecycleBadge } from './LifecycleBadge';
import { PriorityBadge } from './PriorityBadge';

// Classes du `Tr` du DS répliquées + focus-visible clavier. On rend des `<tr>`
// natifs pour les lignes de données (le `Tr` du DS ne forwarde pas
// tabIndex/role/onKeyDown/aria-label) — `src/ui/Table.jsx` reste intouché.
const ROW_CLASS =
  'hover:bg-gray-50 transition cursor-pointer ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

/**
 * M2-5.3.A / M2-5.8.B — Tableau des items V4 (5 colonnes).
 *
 * Colonnes : Titre · Priorité · État · Type · Mis à jour. La colonne Type
 * affiche le `kind` en FR (info principale) + le `domain` en sous-texte.
 *
 * Accessibilité clavier (P0-4 audit M2-5, WCAG 2.1.1) : chaque ligne ouvrable
 * est `tabIndex=0` + `role="button"` + `aria-label` explicite, activable par
 * Entrée ou Espace, avec un anneau de focus visible.
 */
export function ItemsTable({ items, onOpenItem }) {
  return (
    <Table>
      <Thead>
        <Tr>
          <Th>{COPY.columnTitle}</Th>
          <Th>{COPY.columnPriority}</Th>
          <Th>{COPY.columnState}</Th>
          <Th>{COPY.columnType}</Th>
          <Th>{COPY.columnUpdated}</Th>
        </Tr>
      </Thead>
      <Tbody>
        {items.map((item) => {
          const kindLabel = KIND_LABELS[item.kind] || A11Y_COPY.unknownKindLabel;
          const open = () => onOpenItem(item);
          return (
            <tr
              key={item.id}
              className={ROW_CLASS}
              onClick={open}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault(); // Espace : évite le scroll de page
                  open();
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={A11Y_COPY.rowAriaLabel(item.title)}
            >
              <Td>{item.title}</Td>
              <Td>
                <PriorityBadge bracket={item.priority_bracket} />
              </Td>
              <Td>
                <LifecycleBadge state={item.lifecycle_state} />
              </Td>
              <Td>
                <div>{kindLabel}</div>
                {item.domain && <div className="mt-0.5 text-xs text-gray-500">{item.domain}</div>}
              </Td>
              <Td>{formatRelativeDate(item.updated_at || item.created_at)}</Td>
            </tr>
          );
        })}
      </Tbody>
    </Table>
  );
}
