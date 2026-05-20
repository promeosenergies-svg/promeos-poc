import { useCallback, useState } from 'react';
import { FileUp } from 'lucide-react';

import EmptyState from '../../../ui/EmptyState';
import ErrorState from '../../../ui/ErrorState';
import Skeleton from '../../../ui/Skeleton';

import { useActionCenterV4Evidences } from '../../../hooks/v4';
import { EMPTY_STATE_CTA_COPY, TAB_COPY, UPLOAD_COPY } from '../constants';
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
          <button
            type="button"
            onClick={() => setUploadModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-[4px] border px-3 py-1.5 font-sans text-[11.5px] font-semibold cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-attention-fg)',
              borderColor: 'var(--sol-attention-line)',
            }}
          >
            <FileUp size={12} aria-hidden="true" />
            {UPLOAD_COPY.buttonAddEvidence}
          </button>
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
        <div>
          <EmptyState
            variant="empty"
            title={TAB_COPY.evidencesEmptyTitle}
            text={TAB_COPY.evidencesEmptyText}
          />
          {/* CTA inline — audit CS P1-3 : sans ce bouton, l'action est enfouie
              dans le menu Plus ▾ et l'utilisateur perd 30s+. */}
          {!itemClosed && (
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={() => setUploadModalOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-[4px] border px-3 py-1.5 font-sans text-[11.5px] font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
                style={{
                  background: 'var(--sol-bg-paper)',
                  color: 'var(--sol-attention-fg)',
                  borderColor: 'var(--sol-attention-line)',
                }}
              >
                <FileUp size={12} aria-hidden="true" />
                {EMPTY_STATE_CTA_COPY.addEvidence}
              </button>
            </div>
          )}
        </div>
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
