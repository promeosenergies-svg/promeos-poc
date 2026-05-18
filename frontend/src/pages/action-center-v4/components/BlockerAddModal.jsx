import { useCallback, useState } from 'react';

import Button from '../../../ui/Button';
import Modal from '../../../ui/Modal';
import Select from '../../../ui/Select';
import { useToast } from '../../../ui/ToastProvider';

import { useAddBlocker } from '../../../hooks/v4';
import { BLOCKER_ADD_COPY, BLOCKER_TYPE_LABELS } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';

const BLOCKER_TYPE_OPTIONS = Object.keys(BLOCKER_TYPE_LABELS);
const MIN_JUSTIFICATION = 3;

/**
 * M2-5.6 — Modal de signalement d'un blocage (POST /items/{id}/blockers).
 *
 * Réplique le pattern UI write figé M2-5.4/.5. Select contraint aux 7
 * BlockerType. `justification` est validée client-side (requise, ≥ 3 car. —
 * cohérent `BlockerCreate.justification` min_length=3 backend).
 */
export function BlockerAddModal({ open, onClose, itemId, onSuccess }) {
  const [blockerType, setBlockerType] = useState('');
  const [justification, setJustification] = useState('');
  const [inlineError, setInlineError] = useState(null);

  const { execute, loading, reset } = useAddBlocker();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    setBlockerType('');
    setJustification('');
    setInlineError(null);
    reset();
    onClose();
  }, [onClose, reset]);

  const handleSubmit = useCallback(async () => {
    const trimmed = justification.trim();
    if (!blockerType || trimmed.length < MIN_JUSTIFICATION) return;
    setInlineError(null);

    try {
      await execute(itemId, {
        blocker_type: blockerType,
        justification: trimmed,
      });
      toast(BLOCKER_ADD_COPY.successToast, 'success');
      onSuccess?.();
      handleClose();
    } catch (err) {
      const normalized = err.promeos || {
        message: err.message,
        status: err.response?.status,
      };
      if (classifyError(normalized) === 'inline') {
        setInlineError(normalized);
      } else {
        toast(toastMessageForError(normalized), 'error');
        handleClose();
      }
    }
  }, [blockerType, justification, itemId, execute, toast, onSuccess, handleClose]);

  const canSubmit =
    Boolean(blockerType) && justification.trim().length >= MIN_JUSTIFICATION && !loading;

  return (
    <Modal open={open} onClose={handleClose} title={BLOCKER_ADD_COPY.modalTitle}>
      <div className="space-y-4">
        <Select
          label={BLOCKER_ADD_COPY.fieldType}
          aria-label={BLOCKER_ADD_COPY.fieldType}
          value={blockerType}
          onChange={(e) => setBlockerType(e.target.value)}
          options={[
            { value: '', label: BLOCKER_ADD_COPY.fieldTypePlaceholder },
            ...BLOCKER_TYPE_OPTIONS.map((type) => ({
              value: type,
              label: BLOCKER_TYPE_LABELS[type],
            })),
          ]}
        />

        <div>
          <label
            htmlFor="blocker-justification"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            {BLOCKER_ADD_COPY.fieldJustification}
          </label>
          <textarea
            id="blocker-justification"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            maxLength={2000}
            rows={3}
            className="w-full rounded border border-gray-300 p-2 text-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">{BLOCKER_ADD_COPY.fieldJustificationHint}</p>
        </div>

        {inlineError && (
          <div
            role="alert"
            className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900"
          >
            <div className="font-medium">{inlineError.message}</div>
            {inlineError.hint && (
              <div className="mt-1 text-xs text-red-700">{inlineError.hint}</div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            {BLOCKER_ADD_COPY.cancelButton}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {loading ? BLOCKER_ADD_COPY.submitLoading : BLOCKER_ADD_COPY.submitButton}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
