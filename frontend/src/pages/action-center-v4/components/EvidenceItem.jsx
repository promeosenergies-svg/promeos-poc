import { useCallback, useState } from 'react';

import Badge from '../../../ui/Badge';
import Button from '../../../ui/Button';

import {
  EVIDENCE_STATUS_BADGE_VARIANTS,
  EVIDENCE_STATUS_LABELS,
  TAB_COPY,
  VERIFY_COPY,
} from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { deriveEvidenceStatus } from '../utils/evidenceStatus';
import { formatFileSize } from '../utils/fileSize';
import { EvidenceVerifyDialog } from './EvidenceVerifyDialog';

/**
 * M2-5.3.B / M2-5.5 — Affichage d'une evidence.
 *
 * Status dérivé de verified_at + expires_at (jamais d'enum backend).
 * Les champs sensibles (URI de stockage, payload de validation) ne sont pas
 * exposés par l'API V4 — ce composant ne lit aucun champ sensible (test dédié).
 * M2-5.5 : bouton « Vérifier » si le status est `pending` → confirm dialog.
 */
export function EvidenceItem({ evidence, onVerifySuccess }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const handleOpenDialog = useCallback(() => setDialogOpen(true), []);
  const handleCloseDialog = useCallback(() => setDialogOpen(false), []);

  const status = deriveEvidenceStatus(evidence);
  const label = EVIDENCE_STATUS_LABELS[status];
  const variant = EVIDENCE_STATUS_BADGE_VARIANTS[status];

  return (
    <article className="rounded border border-gray-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-gray-900">
            {evidence.original_filename || '—'}
          </div>
          {evidence.description && (
            <div className="mt-0.5 text-xs text-gray-600">{evidence.description}</div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge status={variant}>{label}</Badge>
          {status === 'pending' && (
            <Button variant="ghost" size="sm" onClick={handleOpenDialog}>
              {VERIFY_COPY.buttonVerify}
            </Button>
          )}
        </div>
      </div>

      <div className="mt-2 space-y-0.5 text-xs text-gray-500">
        <div>
          {TAB_COPY.uploadedAtLabel} {formatDateTimeFR(evidence.uploaded_at)}
          {evidence.file_size_bytes != null && (
            <span> · {formatFileSize(evidence.file_size_bytes)}</span>
          )}
        </div>

        {status === 'verified' && evidence.verified_at && (
          <div>
            {TAB_COPY.verifiedAtLabel} {formatDateTimeFR(evidence.verified_at)}
            {evidence.expires_at && (
              <span>
                {' · '}
                {TAB_COPY.expiresAtLabel} {formatDateTimeFR(evidence.expires_at)}
              </span>
            )}
          </div>
        )}

        {status === 'expired' && evidence.expires_at && (
          <div>
            {TAB_COPY.expiresAtLabel} {formatDateTimeFR(evidence.expires_at)}
          </div>
        )}
      </div>

      {dialogOpen && (
        <EvidenceVerifyDialog
          open
          onClose={handleCloseDialog}
          evidenceId={evidence.id}
          onSuccess={onVerifySuccess}
        />
      )}
    </article>
  );
}
