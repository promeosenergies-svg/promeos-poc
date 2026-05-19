import { useCallback, useState } from 'react';

import Button from '../../../ui/Button';
import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Evidences } from '../../../hooks/v4';
import { TAB_COPY, UPLOAD_COPY } from '../constants';
import { EvidenceItem } from './EvidenceItem';
import { EvidenceUploadModal } from './EvidenceUploadModal';

const LIMIT = 20;

/**
 * M2-5.3.B / M2-5.5 — Onglet Preuves du drawer.
 *
 * Lecture lazy + actions write M2-5.5 : « Ajouter une preuve » (upload modal)
 * et « Vérifier » par evidence (dialog dans EvidenceItem). Au succès d'une
 * mutation : refetch local + `onEvidenceMutated` pour rafraîchir la Timeline.
 *
 * M2-5.9.bis — `itemClosed` masque « Ajouter une preuve » sur un item clôturé
 * (un item terminal ne reçoit plus de nouvelle preuve). La vérification d'une
 * preuve déjà présente reste possible (état propre de l'evidence).
 */
export function EvidencesTab({ itemId, itemClosed = false, onEvidenceMutated }) {
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const { data, loading, error, refetch } = useActionCenterV4Evidences(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  const handleSuccess = useCallback(() => {
    refetch();
    onEvidenceMutated?.();
  }, [refetch, onEvidenceMutated]);

  const evidences = data?.items || [];

  return (
    <div className="space-y-3">
      {!itemClosed && (
        <div className="flex justify-end">
          <Button onClick={() => setUploadModalOpen(true)}>{UPLOAD_COPY.buttonAddEvidence}</Button>
        </div>
      )}

      {loading && <Skeleton rows={3} />}

      {!loading && error && (
        <ErrorState
          title={TAB_COPY.evidencesErrorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {!loading && !error && evidences.length === 0 && (
        <EmptyState
          variant="empty"
          title={TAB_COPY.evidencesEmptyTitle}
          text={TAB_COPY.evidencesEmptyText}
        />
      )}

      {!loading && !error && evidences.length > 0 && (
        <ol className="space-y-2">
          {evidences.map((evidence) => (
            <li key={evidence.id}>
              <EvidenceItem evidence={evidence} onVerifySuccess={handleSuccess} />
            </li>
          ))}
        </ol>
      )}

      {uploadModalOpen && (
        <EvidenceUploadModal
          open
          onClose={() => setUploadModalOpen(false)}
          itemId={itemId}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
