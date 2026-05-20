import { useCallback, useEffect, useState } from 'react';

import Tabs from '../../../ui/Tabs';

import { useActionCenterV4Item } from '../../../hooks/v4';
import {
  BREADCRUMB_DRAWER_COPY,
  DRAWER_COPY,
  DRAWER_FOOTER_COPY,
  DOMAIN_LABELS,
  KIND_LABELS,
  TAB_IDS,
  TAB_LABELS,
} from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { BlockersTab } from './BlockersTab';
import { Breadcrumb } from './Breadcrumb';
import { DrawerActions } from './DrawerActions';
import { EvidencesTab } from './EvidencesTab';
import { ImpactSection } from './ImpactSection';
import { ItemClosedBanner } from './ItemClosedBanner';
import { ItemHeader } from './ItemHeader';
import { LinksTab } from './LinksTab';
import { TimelineTab } from './TimelineTab';
import { V4Drawer } from './V4Drawer';

/**
 * M2-5.3 / M2-5.4 / M2-5.10.B / .bis — Drawer détail d'un item V4.
 *
 * Architecture (post-audit M2-5.10.B) :
 * - `V4Drawer` custom Sol (largeur 760px, header sticky, footer sticky,
 *   fond canvas) — contourne `src/ui/Drawer.jsx` legacy (audit UI Sol P0-1/2/3).
 * - Header sticky : `Breadcrumb` MONO + `DrawerActions` (3 boutons).
 * - Body : `ItemClosedBanner` (si terminal) + `ItemHeader` + `Tabs` + content.
 * - Footer sticky : créé + MAJ.
 *
 * Ordre onglets restauré (audit UX/CS) : Preuves → Blocages → Liens →
 * Historique (l'action prioritaire arrive en premier, l'audit a posteriori
 * vient en dernier).
 *
 * Lecture lazy par onglet (Set `loadedTabs`). Succès mutation → refetch item
 * + remount Timeline via `refreshKey` + liste parent.
 */
const TAB_LIST = [
  { id: TAB_IDS.evidences, label: TAB_LABELS[TAB_IDS.evidences] },
  { id: TAB_IDS.blockers, label: TAB_LABELS[TAB_IDS.blockers] },
  { id: TAB_IDS.links, label: TAB_LABELS[TAB_IDS.links] },
  { id: TAB_IDS.timeline, label: TAB_LABELS[TAB_IDS.timeline] },
];
const DEFAULT_TAB = TAB_IDS.evidences;

export function ItemDetailDrawer({ itemId, open, onClose, onRefreshList }) {
  const [activeTab, setActiveTab] = useState(DEFAULT_TAB);
  const [loadedTabs, setLoadedTabs] = useState(() => new Set([DEFAULT_TAB]));
  const [refreshKey, setRefreshKey] = useState(0);

  // Reset à la fermeture → la prochaine ouverture repart sur l'onglet par défaut.
  useEffect(() => {
    if (!open) {
      setActiveTab(DEFAULT_TAB);
      setLoadedTabs(new Set([DEFAULT_TAB]));
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

  // Succès transition lifecycle → refetch item + remount Timeline + liste parent.
  const handleTransitionSuccess = useCallback(() => {
    refetchItem();
    setRefreshKey((k) => k + 1);
    onRefreshList?.();
  }, [refetchItem, onRefreshList]);

  // Mutation evidence/blocker → remount Timeline pour exposer le nouvel event.
  const handleMutated = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  if (!open || !itemId) return null;

  // M2-5.11.F — Breadcrumb dynamique : 4-5 segments selon les données item
  // disponibles. La hiérarchie reflète le contexte décisionnel : section >
  // page > type d'item > domaine métier > « Détail » courant. Tant que l'item
  // n'est pas chargé (loading/erreur), on reste sur la version statique.
  const breadcrumbSegments = item
    ? [
        { label: BREADCRUMB_DRAWER_COPY.app, strong: true },
        { label: BREADCRUMB_DRAWER_COPY.section },
        { label: BREADCRUMB_DRAWER_COPY.page },
        // KIND_LABELS[item.kind] : 7 valeurs strict CHECK (cardinal V4) —
        // fallback défensif sur item.kind brut si label absent (audit
        // resilience M2-5.8.B).
        { label: KIND_LABELS[item.kind] || item.kind },
        // DOMAIN_LABELS[item.domain] : 7 valeurs, optionnel (item.domain
        // peut être NULL côté model). N'apparaît que si présent — pas de
        // segment fantôme.
        ...(item.domain ? [{ label: DOMAIN_LABELS[item.domain] || item.domain }] : []),
        { label: BREADCRUMB_DRAWER_COPY.current, strong: true },
      ]
    : undefined;

  const footer = item ? (
    <div
      className="flex flex-wrap items-baseline gap-x-3 font-mono text-[9.5px] uppercase tracking-[0.06em]"
      style={{ color: 'var(--sol-ink-500)' }}
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
  ) : null;

  return (
    <V4Drawer
      open={open}
      onClose={onClose}
      ariaLabel={DRAWER_COPY.drawerTitle}
      breadcrumb={<Breadcrumb items={breadcrumbSegments} />}
      headerActions={
        <DrawerActions
          item={item}
          onTransitionSuccess={handleTransitionSuccess}
          onMutated={handleMutated}
        />
      }
      footer={footer}
    >
      <ItemClosedBanner item={item} />
      <ItemHeader item={item} loading={itemLoading} error={itemError} />

      {/* M2-5.10.C — Impact financier 4 quadrants (audit Jean-Marc CFO P0-1).
          Section indépendante du fetch item : `useActionCenterV4Impact` est
          appelé en interne. Reste cachée si l'itemId est absent. */}
      {itemId && <ImpactSection itemId={itemId} />}

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
    </V4Drawer>
  );
}
