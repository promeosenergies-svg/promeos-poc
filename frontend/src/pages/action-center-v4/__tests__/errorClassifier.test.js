/**
 * M2-5.4 — Tests du classifieur d'erreurs (environnement node).
 */
import { describe, expect, test } from 'vitest';

import { classifyError, toastMessageForError } from '../utils/errorClassifier';

describe('classifyError', () => {
  test('returns null for a null error', () => {
    expect(classifyError(null)).toBeNull();
  });

  test.each(['CLOSURE_REASON_REQUIRED', 'CLOSURE_REASON_UNEXPECTED', 'CLOSURE_REASON_SYSTEM_ONLY'])(
    'returns "inline" for the corrigeable code %s',
    (code) => {
      expect(classifyError({ code })).toBe('inline');
    }
  );

  test('returns "toast" for LIFECYCLE_TRANSITION_FORBIDDEN', () => {
    expect(classifyError({ code: 'LIFECYCLE_TRANSITION_FORBIDDEN' })).toBe('toast');
  });

  test.each([401, 403, 429, 500])('returns "toast" for HTTP status %i without a code', (status) => {
    expect(classifyError({ status })).toBe('toast');
  });

  test.each(['FILE_TOO_LARGE', 'UNSUPPORTED_MEDIA_TYPE', 'MAGIC_BYTES_MISMATCH'])(
    'returns "inline" for the corrigeable evidence code %s',
    (code) => {
      expect(classifyError({ code })).toBe('inline');
    }
  );
});

describe('toastMessageForError', () => {
  test('returns a generic message for a null error', () => {
    expect(toastMessageForError(null)).toBe('Erreur inconnue');
  });

  test.each([
    [401, /session expirée/i],
    [403, /non autorisée/i],
    [429, /trop de requêtes/i],
    [500, /erreur serveur/i],
    [502, /erreur serveur/i],
  ])('status %i yields a message matching %s', (status, pattern) => {
    expect(toastMessageForError({ status })).toMatch(pattern);
  });

  test('LIFECYCLE_TRANSITION_FORBIDDEN uses the backend message', () => {
    expect(
      toastMessageForError({
        code: 'LIFECYCLE_TRANSITION_FORBIDDEN',
        message: 'custom msg',
      })
    ).toBe('custom msg');
  });
});
