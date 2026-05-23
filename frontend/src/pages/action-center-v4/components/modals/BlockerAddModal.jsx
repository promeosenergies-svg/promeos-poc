import { useCallback, useState } from 'react';

import Select from '../../../../ui/Select';
import { useToast } from '../../../../ui/ToastProvider';

import { useAddBlocker } from '../../../../hooks/v4';
import { BLOCKER_ADD_COPY, BLOCKER_TYPE_LABELS } from '../../constants';
import { classifyError, toastMessageForError } from '../../utils/errorClassifier';
import { SolButton } from '../shared/SolButton';
import { SolInlineError } from '../shared/SolInlineError';
import { V4Modal } from './V4Modal';

const BLOCKER_TYPE_OPTIONS = Object.keys(BLOCKER_TYPE_LABELS);
const MIN_JUSTIFICATION = 3;

/**
 * M2-5.6 / M2-5.11.A — Modal de signalement d'un blocage
 * (POST /items/{id}/blockers).
 *
 * Réplique le pattern UI write figé M2-5.4/.5. Select contraint aux 7
 * BlockerType. `justification` est validée client-side (requise, ≥ 3 car. —
 * cohérent `BlockerCreate.justification` min_length=3 backend).
 *
 * M2-5.11.A — passage sur V4Modal + SolButton + SolInlineError + textarea
 * stylé tokens Sol (vs `border-gray-300 focus:ring-blue-500` Tailwind).
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
    <V4Modal
      open={open}
      onClose={handleClose}
      title={BLOCKER_ADD_COPY.modalTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {BLOCKER_ADD_COPY.cancelButton}
          </SolButton>
          <SolButton onClick={handleSubmit} disabled={!canSubmit} loading={loading}>
            {loading ? BLOCKER_ADD_COPY.submitLoading : BLOCKER_ADD_COPY.submitButton}
          </SolButton>
        </>
      }
    >
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
            className="mb-1 block text-[12px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {BLOCKER_ADD_COPY.fieldJustification}
          </label>
          <textarea
            id="blocker-justification"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            maxLength={2000}
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
            {BLOCKER_ADD_COPY.fieldJustificationHint}
          </p>
        </div>

        <SolInlineError error={inlineError} />
      </div>
    </V4Modal>
  );
}
