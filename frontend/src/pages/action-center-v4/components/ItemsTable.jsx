import { Table, Thead, Tbody, Tr, Th, Td } from '../../../ui/Table';

import { COPY } from '../constants';
import { formatRelativeDate } from '../utils/date';
import { LifecycleBadge } from './LifecycleBadge';

/**
 * M2-5.3.A — Tableau des items V4.
 *
 * Lignes cliquables : `onClick` sur `Tr` ouvre le drawer détail via
 * `onOpenItem`. Le `cursor-pointer` ajouté par `Tr` (src/ui/Table.jsx)
 * est désormais une affordance correcte — la ligne fait quelque chose.
 */
export function ItemsTable({ items, onOpenItem }) {
  return (
    <Table>
      <Thead>
        <Tr>
          <Th>{COPY.columnTitle}</Th>
          <Th>{COPY.columnState}</Th>
          <Th>{COPY.columnDomain}</Th>
          <Th>{COPY.columnUpdated}</Th>
        </Tr>
      </Thead>
      <Tbody>
        {items.map((item) => (
          <Tr key={item.id} onClick={() => onOpenItem(item)}>
            <Td>{item.title}</Td>
            <Td>
              <LifecycleBadge state={item.lifecycle_state} />
            </Td>
            <Td>{item.domain || '—'}</Td>
            <Td>{formatRelativeDate(item.updated_at || item.created_at)}</Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
