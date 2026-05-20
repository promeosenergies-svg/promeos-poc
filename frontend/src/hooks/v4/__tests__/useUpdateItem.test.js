// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useUpdateItem.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  updateItem: vi.fn(),
}));

import { updateItem } from '../../../services/api/v4ActionCenter';
import { useUpdateItem } from '../useUpdateItem';

describe('useUpdateItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute patches the item and returns data', async () => {
    updateItem.mockResolvedValue({ data: { id: 'item-1', title: 'X' } });

    const { result } = renderHook(() => useUpdateItem());

    let returned;
    await act(async () => {
      returned = await result.current.execute('item-1', { title: 'X' });
    });

    expect(updateItem).toHaveBeenCalledWith('item-1', { title: 'X' });
    expect(returned).toEqual({ id: 'item-1', title: 'X' });
    expect(result.current.error).toBeNull();
  });
});
