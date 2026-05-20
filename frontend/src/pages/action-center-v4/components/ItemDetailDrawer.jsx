import { useCallback, useEffect, useState } from 'react';

import Drawer from '../../../ui/Drawer';
import Tabs from '../../../ui/Tabs';

import { useActionCenterV4Item } from '../../../hooks/v4';
import { DRAWER_COPY, DRAWER_FOOTER_COPY, TAB_IDS, TAB_LABELS } from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { BlockersTab } from './BlockersTab';
import { DrawerActions } from './DrawerActions';
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
 * M2-5.3 / M2-5.4 / M2-5.10.B — Drawer détail d'un item V4.
 *
 * Lecture : item + 4 onglets read-only, lazy par onglet (Set `loadedTabs`).
 * Écriture : `DrawerActions` (3 boutons header maquette) déclenche les modals
 * Transitionner / Bloquer / Ajouter preuve. Le succès remonte un refetch
 * ciblé : item (header), events (remount TimelineTab via `refreshKey`,
 * cohérent avec le lazy), liste parent (`onRefreshList`).
 *
 * M2-5.10.B — restyle Sol pixel-perfect maquette §8.4 : DrawerActions en
 * haut, ItemHeader (title block + status row + métadonnées), Tabs, footer
 * MONO « créé X · MAJ Y ».
 */
export function ItemDetailDrawer({ itemId, open, onClose, onRefreshList }) {
  const [activeTab, setActiveTab] = useState(TAB_IDS.timeline);
  const [loadedTabs, setLoadedTabs] = useState(() => new Set([TAB_IDS.timeline]));
  const [refreshKey, setRefreshKey] = useState(0);

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

  const {
    data: item,
    loading: itemLoading,
    error: itemError,
    refetch: refetchItem,
  } = useActionCenterV4Item(itemId);

  // Succès transition lifecycle → refetch item (header) + remount Timeline +
  // liste parent. Toutes les mutations (transition/upload/add) → remount
  // Timeline pour exposer le nouvel event.
  const handleTransitionSuccess = useCallback(() => {
    refetchItem();
    setRefreshKey((k) => k + 1);
    onRefreshList?.();
  }, [refetchItem, onRefreshList]);

  const handleMutated = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  if (!open || !itemId) return null;

  return (
    <Drawer open={open} onClose={onClose} title={DRAWER_COPY.drawerTitle} wide>
      <DrawerActions
        item={item}
        onTransitionSuccess={handleTransitionSuccess}
        onMutated={handleMutated}
      />

      <ItemHeader item={item} loading={itemLoading} error={itemError} />

      <div className="mt-4">
        <Tabs tabs={TAB_LIST} active={activeTab} onChange={handleTabChange} />
      </div>

      <div className="mt-4">
        {activeTab === TAB_IDS.timeline && loadedTabs.has(TAB_IDS.timeline) && (
          <TimelineTab key={refreshKey} itemId={itemId} />
        )}
        {activeTab === TAB_IDS.evidences && loadedTabs.has(TAB_IDS.evidences) && (
          <EvidencesTab
            itemId={itemId}
            itemClosed={item?.lifecycle_state === 'closed'}
            onEvidenceMutated={handleMutated}
          />
        )}
        {activeTab === TAB_IDS.blockers && loadedTabs.has(TAB_IDS.blockers) && (
          <BlockersTab
            itemId={itemId}
            itemClosed={item?.lifecycle_state === 'closed'}
            onBlockerMutated={handleMutated}
          />
        )}
        {activeTab === TAB_IDS.links && loadedTabs.has(TAB_IDS.links) && (
          <LinksTab itemId={itemId} />
        )}
      </div>

      {/* Footer drawer maquette ligne 1124-1133. */}
      {item && (
        <div
          className="mt-6 flex flex-wrap items-baseline gap-x-3 pt-3 font-mono text-[9.5px] uppercase tracking-[0.06em]"
          style={{
            borderTop: '1px solid var(--sol-rule)',
            color: 'var(--sol-ink-500)',
          }}
        >
          <span>
            {DRAWER_FOOTER_COPY.createdPrefix}{' '}
            <span className="font-medium" style={{ color: 'var(--sol-ink-700)' }}>
              {formatDateTimeFR(item.created_at)}
            </span>
          </span>
          <span aria-hidden="true">·</span>
          <span>
            {DRAWER_FOOTER_COPY.updatedPrefix}{' '}
            <span className="font-medium" style={{ color: 'var(--sol-ink-700)' }}>
              {formatDateTimeFR(item.updated_at)}
            </span>
          </span>
        </div>
      )}
    </Drawer>
  );
}
