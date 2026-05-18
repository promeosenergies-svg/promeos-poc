import EmptyState from '../../../ui/EmptyState';

import { DRAWER_COPY } from '../constants';

/**
 * M2-5.3.A — Placeholder pour les onglets Preuves / Blocages / Liens.
 *
 * M2-5.3.B remplacera ces placeholders par les vrais onglets read-only
 * (EvidencesTab / BlockersTab / LinksTab).
 */
export function TabPlaceholder() {
  return (
    <EmptyState
      variant="empty"
      title={DRAWER_COPY.tabPlaceholderTitle}
      text={DRAWER_COPY.tabPlaceholderText}
    />
  );
}
