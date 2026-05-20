// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useCreateItem.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  createItem: vi.fn(),
}));

import { createItem } from '../../../services/api/v4ActionCenter';
import { useCreateItem } from '../useCreateItem';

describe('useCreateItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute success returns data and sets state', async () => {
    createItem.mockResolvedValue({ data: { id: 'new-1', title: 'T' } });

    const { result } = renderHook(() => useCreateItem());

    let returned;
    await act(async () => {
      returned = await result.current.execute({ title: 'T' });
    });

    expect(returned).toEqual({ id: 'new-1', title: 'T' });
    expect(result.current.data).toEqual({ id: 'new-1', title: 'T' });
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  test('execute error sets normalized error and rethrows', async () => {
    const err = new Error('Bad');
    err.promeos = { code: 'VALIDATION', message: 'Invalid', status: 422 };
    createItem.mockRejectedValue(err);

    const { result } = renderHook(() => useCreateItem());

    await act(async () => {
      await expect(result.current.execute({})).rejects.toThrow('Bad');
    });

    expect(result.current.error).toEqual({
      code: 'VALIDATION',
      message: 'Invalid',
      status: 422,
    });
  });
});
