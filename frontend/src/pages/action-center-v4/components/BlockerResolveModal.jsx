import { useCallback, useState } from 'react';

import Button from '../../../ui/Button';
import Modal from '../../../ui/Modal';
import { useToast } from '../../../ui/ToastProvider';

import { useResolveBlocker } from '../../../hooks/v4';
import { BLOCKER_RESOLVE_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';

/**
 * M2-5.6 — Modal de résolution d'un blocage (PATCH /blockers/{id}/resolve).
 *
 * Q2 : `resolution_comment` optionnel (max 500, metadata de l'event
 * `blocker_removed`). Toujours toast + close : un confirm-style n'a rien à
 * corriger — BLOCKER_ALREADY_RESOLVED (classé inline) adouci en toast warning.
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
    <Modal open={open} onClose={handleClose} title={BLOCKER_RESOLVE_COPY.modalTitle}>
      <div className="space-y-4">
        <div>
          <label
            htmlFor="blocker-resolution-comment"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            {BLOCKER_RESOLVE_COPY.fieldNote}
          </label>
          <textarea
            id="blocker-resolution-comment"
            value={resolutionComment}
            onChange={(e) => setResolutionComment(e.target.value)}
            maxLength={500}
            rows={3}
            className="w-full rounded border border-gray-300 p-2 text-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">{BLOCKER_RESOLVE_COPY.fieldNoteHint}</p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            {BLOCKER_RESOLVE_COPY.cancelButton}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? BLOCKER_RESOLVE_COPY.submitLoading : BLOCKER_RESOLVE_COPY.submitButton}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
