import { useCallback, useMemo, useState } from 'react';

import Button from '../../../ui/Button';
import Input from '../../../ui/Input';
import Modal from '../../../ui/Modal';
import Select from '../../../ui/Select';
import { useToast } from '../../../ui/ToastProvider';

import { useTransitionLifecycle } from '../../../hooks/v4';
import { CLOSURE_REASON_LABELS, LIFECYCLE_LABELS, TRANSITION_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';
import {
  USER_FACING_CLOSURE_REASONS,
  getAvailableTransitions,
  transitionRequiresReason,
} from '../utils/lifecycleTransitions';

/**
 * M2-5.4 — Modal de transition lifecycle (premier write V4).
 *
 * Validation client : options new_state filtrées selon la matrice de
 * transitions depuis currentState, closure_reason affiché si requis. Le
 * backend reste l'autorité finale (re-validation). Pessimistic : on attend
 * la réponse serveur, le parent refetch au succès via `onSuccess`.
 *
 * Erreurs : 422 corrigeable → inline (modal reste ouverte) ; sinon → toast
 * + fermeture (cf. utils/errorClassifier).
 */
export function LifecycleTransitionModal({ open, onClose, itemId, currentState, onSuccess }) {
  const [newState, setNewState] = useState('');
  const [closureReason, setClosureReason] = useState('');
  const [comment, setComment] = useState('');
  const [inlineError, setInlineError] = useState(null);

  const { execute, loading, reset } = useTransitionLifecycle();
  const { toast } = useToast();

  const availableTransitions = useMemo(() => getAvailableTransitions(currentState), [currentState]);

  const requiresReason = newState ? transitionRequiresReason(currentState, newState) : false;

  const handleClose = useCallback(() => {
    setNewState('');
    setClosureReason('');
    setComment('');
    setInlineError(null);
    reset();
    onClose();
  }, [onClose, reset]);

  const handleSubmit = useCallback(async () => {
    if (!newState) return;
    setInlineError(null);

    const payload = { new_state: newState };
    if (requiresReason) payload.closure_reason = closureReason;
    if (comment.trim()) payload.comment = comment.trim();

    try {
      await execute(itemId, payload);
      toast(TRANSITION_COPY.successToast, 'success');
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
  }, [
    newState,
    closureReason,
    comment,
    requiresReason,
    itemId,
    execute,
    toast,
    onSuccess,
    handleClose,
  ]);

  const canSubmit = Boolean(newState) && (!requiresReason || Boolean(closureReason)) && !loading;

  if (availableTransitions.length === 0) {
    return (
      <Modal open={open} onClose={handleClose} title={TRANSITION_COPY.modalTitle}>
        <p className="text-sm text-gray-600">{TRANSITION_COPY.noTransitionsAvailable}</p>
        <div className="mt-4 flex justify-end">
          <Button variant="ghost" onClick={handleClose}>
            {TRANSITION_COPY.cancelButton}
          </Button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={handleClose} title={TRANSITION_COPY.modalTitle}>
      <div className="space-y-4">
        <Select
          label={TRANSITION_COPY.fieldNewState}
          aria-label={TRANSITION_COPY.fieldNewState}
          value={newState}
          onChange={(e) => setNewState(e.target.value)}
          options={[
            { value: '', label: TRANSITION_COPY.selectPlaceholder },
            ...availableTransitions.map(({ to }) => ({
              value: to,
              label: LIFECYCLE_LABELS[to],
            })),
          ]}
        />

        {requiresReason && (
          <Select
            label={TRANSITION_COPY.fieldClosureReason}
            aria-label={TRANSITION_COPY.fieldClosureReason}
            value={closureReason}
            onChange={(e) => setClosureReason(e.target.value)}
            options={[
              { value: '', label: TRANSITION_COPY.closurePlaceholder },
              ...USER_FACING_CLOSURE_REASONS.map((r) => ({
                value: r,
                label: CLOSURE_REASON_LABELS[r],
              })),
            ]}
          />
        )}

        <Input
          label={TRANSITION_COPY.fieldComment}
          aria-label={TRANSITION_COPY.fieldComment}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={500}
        />

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
            {TRANSITION_COPY.cancelButton}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {loading ? TRANSITION_COPY.submitLoading : TRANSITION_COPY.submitButton}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
