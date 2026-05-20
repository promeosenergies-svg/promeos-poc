import { useCallback, useState } from 'react';

import { EVIDENCE_STATUS_LABELS, TAB_COPY, VERIFY_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { deriveEvidenceStatus } from '../utils/evidenceStatus';
import { formatFileSize } from '../utils/fileSize';
import { EvidenceVerifyDialog } from './EvidenceVerifyDialog';

/**
 * M2-5.3.B / M2-5.5 / M2-5.10.B — Card d'une evidence (restyle Sol).
 *
 * Restyle pixel-perfect inspiré de l'evidence-panel maquette (§8.4 lignes
 * 481-506) : fond papier + bordure rule + status badge MONO uppercase à
 * gauche + filename Display medium + actions inline. Le statut dérive de
 * verified_at + expires_at (jamais d'enum backend — doctrine ADR-029).
 *
 * Champs sensibles (storage_uri, payload) toujours non exposés.
 */

const STATUS_VARIANTS = {
  pending: {
    bg: 'var(--sol-attention-bg)',
    color: 'var(--sol-attention-fg)',
    border: 'var(--sol-attention-line)',
    borderStyle: 'dashed',
  },
  verified: {
    bg: 'var(--sol-succes-bg)',
    color: 'var(--sol-succes-fg)',
    border: 'var(--sol-succes-line)',
    borderStyle: 'solid',
  },
  expired: {
    bg: 'var(--sol-refuse-bg)',
    color: 'var(--sol-refuse-fg)',
    border: 'var(--sol-refuse-line)',
    borderStyle: 'solid',
  },
};

export function EvidenceItem({ evidence, onVerifySuccess }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const handleOpenDialog = useCallback(() => setDialogOpen(true), []);
  const handleCloseDialog = useCallback(() => setDialogOpen(false), []);

  const status = deriveEvidenceStatus(evidence);
  const label = EVIDENCE_STATUS_LABELS[status];
  const variant = STATUS_VARIANTS[status] || STATUS_VARIANTS.pending;

  return (
    <article
      className="rounded-[6px] border p-3"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div
            className="truncate text-[13.5px] font-medium"
            style={{
              fontFamily: 'var(--sol-font-body)',
              color: 'var(--sol-ink-900)',
            }}
          >
            {evidence.original_filename || '—'}
          </div>
          {evidence.description && (
            <div
              className="mt-0.5 text-[11.5px] italic"
              style={{
                fontFamily: 'var(--sol-font-display)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {evidence.description}
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <span
            className="inline-flex items-center rounded-[3px] border px-2 py-px font-mono text-[9.5px] font-semibold uppercase tracking-[0.14em]"
            style={{
              background: variant.bg,
              borderColor: variant.border,
              borderStyle: variant.borderStyle,
              color: variant.color,
            }}
          >
            {label}
          </span>
          {status === 'pending' && (
            <button
              type="button"
              onClick={handleOpenDialog}
              className="inline-flex items-center rounded-[4px] border px-2.5 py-1 font-sans text-[11.5px] font-semibold cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
              style={{
                background: 'var(--sol-bg-paper)',
                color: 'var(--sol-attention-fg)',
                borderColor: 'var(--sol-attention-line)',
              }}
            >
              {VERIFY_COPY.buttonVerify}
            </button>
          )}
        </div>
      </div>

      <div
        className="mt-2 font-mono text-[10px] tracking-[0.02em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        {TAB_COPY.uploadedAtLabel} {formatDateTimeFR(evidence.uploaded_at)}
        {evidence.file_size_bytes != null && (
          <span> · {formatFileSize(evidence.file_size_bytes)}</span>
        )}
        {status === 'verified' && evidence.verified_at && (
          <div className="mt-0.5">
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
          <div className="mt-0.5">
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
