import { Table, Thead, Tbody, Tr, Th, Td } from '../../../ui/Table';

import { COPY } from '../constants';
import { LifecycleBadge } from './LifecycleBadge';

/**
 * Formatage date courte FR : « aujourd'hui » / « hier » / « il y a 3 jours »
 * / « 12/05 » au-delà d'une semaine. « — » si date absente.
 */
function formatRelativeDate(isoDate) {
  if (!isoDate) return '—';
  const date = new Date(isoDate);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

  if (diffDays <= 0) return "aujourd'hui";
  if (diffDays === 1) return 'hier';
  if (diffDays < 7) return `il y a ${diffDays} jours`;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
}

/**
 * M2-5.2 — Tableau des items V4.
 *
 * Lignes NON cliquables en M2-5.2 : `Tr` ajoute `cursor-pointer` dès qu'un
 * `onClick` est fourni (src/ui/Table.jsx) — une ligne cliquable sans effet
 * serait une fausse affordance. L'ouverture du drawer est branchée en M2-5.3.
 */
export function ItemsTable({ items }) {
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
          <Tr key={item.id}>
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
