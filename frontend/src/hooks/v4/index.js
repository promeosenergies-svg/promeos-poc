/**
 * M2-5.1 — Index des hooks data V4 (Centre d'Action).
 *
 * 14 hooks = 1 par endpoint V4 (6 read + 8 write).
 * Read pattern  : { data, loading, error, refetch }
 * Write pattern : { execute, loading, error, data, reset }
 */

// Read hooks
export { useActionCenterV4Items } from './useActionCenterV4Items';
export { useActionCenterV4Item } from './useActionCenterV4Item';
export { useActionCenterV4Events } from './useActionCenterV4Events';
export { useActionCenterV4Evidences } from './useActionCenterV4Evidences';
export { useActionCenterV4Blockers } from './useActionCenterV4Blockers';
export { useActionCenterV4Links } from './useActionCenterV4Links';
// M2-5.10.C — Impact financier 4 quadrants par item.
export { useActionCenterV4Impact } from './useActionCenterV4Impact';
// M2-5.10.D — File prioritaire pilotage (top N items P0/P1 actifs).
export { usePilotageFilePrioritaire } from './usePilotageFilePrioritaire';
// M2-5.10.E — Journal org-wide cross-items (fenêtre N jours).
export { usePilotageJournal } from './usePilotageJournal';
// M2-5.11.C — Summary org (5 compteurs CFO pour la NarrativeBar Sol).
export { useActionCenterV4Summary } from './useActionCenterV4Summary';

// Write hooks
export { useCreateItem } from './useCreateItem';
export { useUpdateItem } from './useUpdateItem';
export { useTransitionLifecycle } from './useTransitionLifecycle';
export { useUploadEvidence } from './useUploadEvidence';
export { useVerifyEvidence } from './useVerifyEvidence';
export { useAddBlocker } from './useAddBlocker';
export { useResolveBlocker } from './useResolveBlocker';
export { useCreateLink } from './useCreateLink';
// M2-5.11.E — Assignation pilote (PATCH /items/{id}/assign).
export { useAssignOwner } from './useAssignOwner';
