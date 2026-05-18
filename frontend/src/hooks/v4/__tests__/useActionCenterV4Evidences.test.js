// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Evidences.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItemEvidences: vi.fn(),
}));

import { fetchItemEvidences } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Evidences } from '../useActionCenterV4Evidences';

describe('useActionCenterV4Evidences', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads evidences on mount', async () => {
    fetchItemEvidences.mockResolvedValue({
      data: { evidences: [{ id: 'ev1' }], total: 1, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Evidences('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data.evidences).toEqual([{ id: 'ev1' }]);
    expect(result.current.error).toBeNull();
  });

  test('falls back to UNKNOWN error when no promeos detail', async () => {
    fetchItemEvidences.mockRejectedValue(new Error('boom'));

    const { result } = renderHook(() => useActionCenterV4Evidences('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toEqual({ code: 'UNKNOWN', message: 'boom' });
  });
});
