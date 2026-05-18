import { useCallback, useEffect, useState } from 'react';

import Drawer from '../../../ui/Drawer';
import Tabs from '../../../ui/Tabs';

import { useActionCenterV4Item } from '../../../hooks/v4';
import { DRAWER_COPY, TAB_IDS, TAB_LABELS } from '../constants';
import { ItemHeader } from './ItemHeader';
import { TabPlaceholder } from './TabPlaceholder';
import { TimelineTab } from './TimelineTab';

const TAB_LIST = [
  { id: TAB_IDS.timeline, label: TAB_LABELS[TAB_IDS.timeline] },
  { id: TAB_IDS.evidences, label: TAB_LABELS[TAB_IDS.evidences] },
  { id: TAB_IDS.blockers, label: TAB_LABELS[TAB_IDS.blockers] },
  { id: TAB_IDS.links, label: TAB_LABELS[TAB_IDS.links] },
];

/**
 * M2-5.3.A — Drawer détail d'un item V4 (lecture seule, aucune mutation).
 *
 * Fetch l'item via useActionCenterV4Item(itemId) — données fraîches, pas
 * l'objet de la liste. Lazy par onglet : Timeline charge à l'ouverture, les
 * autres onglets au premier clic (Set `loadedTabs`). En M2-5.3.A les 3 autres
 * onglets affichent un TabPlaceholder — M2-5.3.B les activera.
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
        {activeTab === TAB_IDS.evidences && <TabPlaceholder />}
        {activeTab === TAB_IDS.blockers && <TabPlaceholder />}
        {activeTab === TAB_IDS.links && <TabPlaceholder />}
      </div>
    </Drawer>
  );
}
