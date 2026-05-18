// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useVerifyEvidence.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  verifyEvidence: vi.fn(),
}));

import { verifyEvidence } from '../../../services/api/v4ActionCenter';
import { useVerifyEvidence } from '../useVerifyEvidence';

describe('useVerifyEvidence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute verifies the evidence and returns data', async () => {
    verifyEvidence.mockResolvedValue({ data: { id: 'ev-1', status: 'verified' } });

    const { result } = renderHook(() => useVerifyEvidence());

    let returned;
    await act(async () => {
      returned = await result.current.execute('ev-1', { note: 'conforme' });
    });

    expect(verifyEvidence).toHaveBeenCalledWith('ev-1', { note: 'conforme' });
    expect(returned).toEqual({ id: 'ev-1', status: 'verified' });
  });
});
