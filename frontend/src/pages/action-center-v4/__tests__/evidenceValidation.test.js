/**
 * M2-5.5 — Tests de la validation client evidence (environnement node).
 */
import { describe, expect, test } from 'vitest';

import {
  ACCEPTED_MIME_TYPES,
  MAX_FILE_SIZE_BYTES,
  validateEvidenceFile,
} from '../utils/evidenceValidation';

function fakeFile(name, type, size = 10) {
  const file = new File(['x'], name, { type });
  if (size !== 10) {
    Object.defineProperty(file, 'size', { value: size });
  }
  return file;
}

describe('validateEvidenceFile', () => {
  test('returns a message when the file is null', () => {
    expect(validateEvidenceFile(null)).toMatch(/sélectionner/i);
  });

  test.each([
    ['doc.pdf', 'application/pdf'],
    ['img.jpg', 'image/jpeg'],
    ['img.png', 'image/png'],
  ])('accepts %s (%s)', (name, type) => {
    expect(validateEvidenceFile(fakeFile(name, type))).toBeNull();
  });

  test('rejects a DOCX file', () => {
    const file = fakeFile(
      'doc.docx',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
    expect(validateEvidenceFile(file)).toMatch(/format/i);
  });

  test('rejects a file larger than 10 MB', () => {
    const file = fakeFile('big.pdf', 'application/pdf', 11 * 1024 * 1024);
    expect(validateEvidenceFile(file)).toMatch(/10 Mo/i);
  });

  test('ACCEPTED_MIME_TYPES holds exactly pdf / jpeg / png', () => {
    expect(ACCEPTED_MIME_TYPES).toEqual(['application/pdf', 'image/jpeg', 'image/png']);
  });

  test('MAX_FILE_SIZE_BYTES is 10 MB', () => {
    expect(MAX_FILE_SIZE_BYTES).toBe(10 * 1024 * 1024);
  });
});
