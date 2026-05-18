import { useCallback, useEffect, useState } from 'react';

import Drawer from '../../../ui/Drawer';
import Tabs from '../../../ui/Tabs';

import { useActionCenterV4Item } from '../../../hooks/v4';
import { DRAWER_COPY, TAB_IDS, TAB_LABELS } from '../constants';
import { BlockersTab } from './BlockersTab';
import { EvidencesTab } from './EvidencesTab';
import { ItemHeader } from './ItemHeader';
import { LinksTab } from './LinksTab';
import { TimelineTab } from './TimelineTab';

const TAB_LIST = [
  { id: TAB_IDS.timeline, label: TAB_LABELS[TAB_IDS.timeline] },
  { id: TAB_IDS.evidences, label: TAB_LABELS[TAB_IDS.evidences] },
  { id: TAB_IDS.blockers, label: TAB_LABELS[TAB_IDS.blockers] },
  { id: TAB_IDS.links, label: TAB_LABELS[TAB_IDS.links] },
];

/**
 * M2-5.3.A/B — Drawer détail d'un item V4 (lecture seule, aucune mutation).
 *
 * Fetch l'item via useActionCenterV4Item(itemId). Lazy par onglet : un onglet
 * ne monte son contenu qu'au premier clic (Set `loadedTabs`) ; les 4 onglets
 * sont read-only (Historique / Preuves / Blocages / Liens).
 */
export function ItemDetailDrawer({ itemId, open, onClose }) {
  const [activeTab, setActiveTab] = useState(TAB_IDS.timeline);
  const [loadedTabs, setLoadedTabs] = useState(() => new Set([TAB_IDS.timeline]));

  // Reset à la fermeture → la prochaine ouverture repart sur Timeline.
  useEffect(() => {
    if (!open) {
      setActiveTab(TAB_IDS.timeline);
      setLoadedTabs(new Set([TAB_IDS.timeline]));
    }
  }, [open]);

  const handleTabChange = useCallback((tabId) => {
    setActiveTab(tabId);
    setLoadedTabs((prev) => {
      if (prev.has(tabId)) return prev;
      const next = new Set(prev);
      next.add(tabId);
      return next;
    });
  }, []);

  const { data: item, loading: itemLoading, error: itemError } = useActionCenterV4Item(itemId);

  if (!open || !itemId) return null;

  return (
    <Drawer open={open} onClose={onClose} title={DRAWER_COPY.drawerTitle} wide>
      <ItemHeader item={item} loading={itemLoading} error={itemError} />

      <div className="mt-4">
        <Tabs tabs={TAB_LIST} active={activeTab} onChange={handleTabChange} />
      </div>

      <div className="mt-4">
        {activeTab === TAB_IDS.timeline && loadedTabs.has(TAB_IDS.timeline) && (
          <TimelineTab itemId={itemId} />
        )}
        {activeTab === TAB_IDS.evidences && loadedTabs.has(TAB_IDS.evidences) && (
          <EvidencesTab itemId={itemId} />
        )}
        {activeTab === TAB_IDS.blockers && loadedTabs.has(TAB_IDS.blockers) && (
          <BlockersTab itemId={itemId} />
        )}
        {activeTab === TAB_IDS.links && loadedTabs.has(TAB_IDS.links) && (
          <LinksTab itemId={itemId} />
        )}
      </div>
    </Drawer>
  );
}
