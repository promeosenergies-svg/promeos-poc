// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useUploadEvidence (multipart).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  uploadEvidence: vi.fn(),
}));

import { uploadEvidence } from '../../../services/api/v4ActionCenter';
import { useUploadEvidence } from '../useUploadEvidence';

describe('useUploadEvidence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute uploads the file and returns the created evidence', async () => {
    uploadEvidence.mockResolvedValue({ data: { id: 'ev-1', status: 'pending' } });

    const { result } = renderHook(() => useUploadEvidence());
    const file = new File(['x'], 'facture.pdf', { type: 'application/pdf' });

    let returned;
    await act(async () => {
      returned = await result.current.execute('item-1', file, { description: 'Q3' });
    });

    expect(uploadEvidence).toHaveBeenCalledWith('item-1', file, { description: 'Q3' });
    expect(returned).toEqual({ id: 'ev-1', status: 'pending' });
    expect(result.current.error).toBeNull();
  });
});
