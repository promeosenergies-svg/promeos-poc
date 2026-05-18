import { useCallback } from 'react';

import Button from '../../../ui/Button';
import Modal from '../../../ui/Modal';
import { useToast } from '../../../ui/ToastProvider';

import { useVerifyEvidence } from '../../../hooks/v4';
import { VERIFY_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';

/**
 * M2-5.5 — Confirm dialog de vérification d'une preuve.
 *
 * Q3 : simple confirmation, aucun champ expires_at (le backend pose le défaut
 * +90 jours). Toujours toast + close : un confirm dialog n'a pas de champ à
 * corriger — `EVIDENCE_ALREADY_VERIFIED` → toast warning (jaune) pour adoucir.
 */
export function EvidenceVerifyDialog({ open, onClose, evidenceId, onSuccess }) {
  const { execute, loading, reset } = useVerifyEvidence();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [onClose, reset]);

  const handleConfirm = useCallback(async () => {
    try {
      await execute(evidenceId, {}); // payload vide → backend pose expires_at +90j
      toast(VERIFY_COPY.successToast, 'success');
      onSuccess?.();
      handleClose();
    } catch (err) {
      const normalized = err.promeos || {
        message: err.message,
        status: err.response?.status,
      };
      // Confirm dialog : aucune correction possible → toast + close dans tous
      // les cas. Le code corrigeable EVIDENCE_ALREADY_VERIFIED est juste
      // adouci en warning.
      const tone = classifyError(normalized) === 'inline' ? 'warning' : 'error';
      toast(toastMessageForError(normalized), tone);
      handleClose();
    }
  }, [evidenceId, execute, toast, onSuccess, handleClose]);

  return (
    <Modal open={open} onClose={handleClose} title={VERIFY_COPY.dialogTitle}>
      <p className="text-sm text-gray-700">{VERIFY_COPY.dialogMessage}</p>
      <div className="flex justify-end gap-2 pt-4">
        <Button variant="ghost" onClick={handleClose} disabled={loading}>
          {VERIFY_COPY.cancelButton}
        </Button>
        <Button onClick={handleConfirm} disabled={loading}>
          {loading ? VERIFY_COPY.confirmLoading : VERIFY_COPY.confirmButton}
        </Button>
      </div>
    </Modal>
  );
}
