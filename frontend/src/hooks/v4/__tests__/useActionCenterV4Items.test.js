// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Items (renderHook, jsdom requis).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItems: vi.fn(),
}));

import { fetchItems } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Items } from '../useActionCenterV4Items';

describe('useActionCenterV4Items', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads items on mount', async () => {
    fetchItems.mockResolvedValue({
      data: { items: [{ id: '1' }], total: 1, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Items());
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual({
      items: [{ id: '1' }],
      total: 1,
      offset: 0,
      limit: 50,
    });
    expect(result.current.error).toBeNull();
  });

  test('handles error with promeos detail', async () => {
    const err = new Error('Network');
    err.promeos = { code: 'INTERNAL', message: 'Server error', status: 500 };
    fetchItems.mockRejectedValue(err);

    const { result } = renderHook(() => useActionCenterV4Items());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toEqual({
      code: 'INTERNAL',
      message: 'Server error',
      status: 500,
    });
  });

  test('refetch reruns the request', async () => {
    fetchItems.mockResolvedValue({
      data: { items: [], total: 0, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Items());
    await waitFor(() => expect(result.current.loading).toBe(false));

    fetchItems.mockClear();
    await act(async () => {
      await result.current.refetch();
    });

    expect(fetchItems).toHaveBeenCalledTimes(1);
  });
});
