import { useCallback, useState } from 'react';

import { useToast } from '../../../../ui/ToastProvider';

import { useResolveBlocker } from '../../../../hooks/v4';
import { BLOCKER_RESOLVE_COPY } from '../../constants';
import { classifyError, toastMessageForError } from '../../utils/errorClassifier';
import { SolButton } from '../shared/SolButton';
import { V4Modal } from './V4Modal';

/**
 * M2-5.6 / M2-5.11.A — Modal de résolution d'un blocage
 * (PATCH /blockers/{id}/resolve).
 *
 * Q2 : `resolution_comment` optionnel (max 500, metadata de l'event
 * `blocker_removed`). Toujours toast + close : un confirm-style n'a rien à
 * corriger — BLOCKER_ALREADY_RESOLVED (classé inline) adouci en toast warning.
 *
 * M2-5.11.A — passage sur V4Modal + SolButton + textarea Sol.
 */
export function BlockerResolveModal({ open, onClose, blockerId, onSuccess }) {
  const [resolutionComment, setResolutionComment] = useState('');

  const { execute, loading, reset } = useResolveBlocker();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    setResolutionComment('');
    reset();
    onClose();
  }, [onClose, reset]);

  const handleSubmit = useCallback(async () => {
    const payload = {};
    const trimmed = resolutionComment.trim();
    if (trimmed) payload.resolution_comment = trimmed;

    try {
      await execute(blockerId, payload);
      toast(BLOCKER_RESOLVE_COPY.successToast, 'success');
      onSuccess?.();
      handleClose();
    } catch (err) {
      const normalized = err.promeos || {
        message: err.message,
        status: err.response?.status,
      };
      const tone = classifyError(normalized) === 'inline' ? 'warning' : 'error';
      toast(toastMessageForError(normalized), tone);
      handleClose();
    }
  }, [resolutionComment, blockerId, execute, toast, onSuccess, handleClose]);

  return (
    <V4Modal
      open={open}
      onClose={handleClose}
      title={BLOCKER_RESOLVE_COPY.modalTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {BLOCKER_RESOLVE_COPY.cancelButton}
          </SolButton>
          <SolButton onClick={handleSubmit} disabled={loading} loading={loading}>
            {loading ? BLOCKER_RESOLVE_COPY.submitLoading : BLOCKER_RESOLVE_COPY.submitButton}
          </SolButton>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label
            htmlFor="blocker-resolution-comment"
            className="mb-1 block text-[12px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {BLOCKER_RESOLVE_COPY.fieldNote}
          </label>
          <textarea
            id="blocker-resolution-comment"
            value={resolutionComment}
            onChange={(e) => setResolutionComment(e.target.value)}
            maxLength={500}
            rows={3}
            className="w-full rounded-[6px] border p-2 text-[13px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              borderColor: 'var(--sol-ink-300)',
              color: 'var(--sol-ink-900)',
              fontFamily: 'var(--sol-font-body)',
            }}
          />
          <p
            className="mt-1 text-[11px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {BLOCKER_RESOLVE_COPY.fieldNoteHint}
          </p>
        </div>
      </div>
    </V4Modal>
  );
}
