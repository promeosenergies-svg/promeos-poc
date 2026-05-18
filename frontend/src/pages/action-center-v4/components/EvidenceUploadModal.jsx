import { useCallback, useRef, useState } from 'react';

import Button from '../../../ui/Button';
import Input from '../../../ui/Input';
import Modal from '../../../ui/Modal';
import { useToast } from '../../../ui/ToastProvider';

import { useUploadEvidence } from '../../../hooks/v4';
import { UPLOAD_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';
import { ACCEPTED_MIME_TYPES, validateEvidenceFile } from '../utils/evidenceValidation';
import { formatFileSize } from '../utils/fileSize';

/**
 * M2-5.5 — Modal d'upload d'une preuve (multipart POST).
 *
 * Réplique le pattern UI write figé M2-5.4 : pessimistic, erreur inline 422
 * corrigeable / toast infra + close, refetch au succès via `onSuccess`.
 *
 * Q1 : validation MIME côté client (defense in depth) — le backend reste
 * l'autorité (magic bytes + 10 Mo). Q2 : loading simple, pas de progress bar.
 */
export function EvidenceUploadModal({ open, onClose, itemId, onSuccess }) {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [clientError, setClientError] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const fileInputRef = useRef(null);

  const { execute, loading, reset } = useUploadEvidence();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    setFile(null);
    setDescription('');
    setClientError(null);
    setInlineError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    reset();
    onClose();
  }, [onClose, reset]);

  const handleFileChange = useCallback((e) => {
    const selected = e.target.files?.[0] || null;
    setClientError(null);
    setInlineError(null);
    if (selected) {
      const errMsg = validateEvidenceFile(selected);
      if (errMsg) {
        setClientError(errMsg);
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
      }
    }
    setFile(selected);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!file) return;
    setInlineError(null);

    try {
      await execute(itemId, file, {
        description: description.trim() || undefined,
      });
      toast(UPLOAD_COPY.successToast, 'success');
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
  }, [file, description, itemId, execute, toast, onSuccess, handleClose]);

  const canSubmit = Boolean(file) && !clientError && !loading;

  return (
    <Modal open={open} onClose={handleClose} title={UPLOAD_COPY.modalTitle}>
      <div className="space-y-4">
        <div>
          <label
            htmlFor="evidence-file-input"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            {UPLOAD_COPY.fieldFile}
          </label>
          <input
            id="evidence-file-input"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_MIME_TYPES.join(',')}
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-700 file:mr-3 file:cursor-pointer
              file:rounded file:border-0 file:bg-blue-50 file:px-4 file:py-2
              file:text-blue-700 hover:file:bg-blue-100"
          />
          <p className="mt-1 text-xs text-gray-500">{UPLOAD_COPY.fieldFileHint}</p>
          {file && !clientError && (
            <p className="mt-1 text-xs text-gray-600">
              {file.name} · {formatFileSize(file.size)}
            </p>
          )}
        </div>

        <Input
          label={UPLOAD_COPY.fieldDescription}
          aria-label={UPLOAD_COPY.fieldDescription}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={500}
        />

        {clientError && (
          <div
            role="alert"
            className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          >
            {clientError}
          </div>
        )}

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
            {UPLOAD_COPY.cancelButton}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {loading ? UPLOAD_COPY.submitLoading : UPLOAD_COPY.submitButton}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
