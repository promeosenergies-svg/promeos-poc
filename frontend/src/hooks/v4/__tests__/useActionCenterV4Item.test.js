// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Item (objet unique, garde itemId).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItem: vi.fn(),
}));

import { fetchItem } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Item } from '../useActionCenterV4Item';

describe('useActionCenterV4Item', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads the item detail on mount', async () => {
    fetchItem.mockResolvedValue({ data: { id: 'item-1', title: 'Audit Q3' } });

    const { result } = renderHook(() => useActionCenterV4Item('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItem).toHaveBeenCalledWith('item-1');
    expect(result.current.data).toEqual({ id: 'item-1', title: 'Audit Q3' });
    expect(result.current.error).toBeNull();
  });

  test('does not fetch when itemId is absent', async () => {
    const { result } = renderHook(() => useActionCenterV4Item(null));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItem).not.toHaveBeenCalled();
    expect(result.current.data).toBeNull();
  });
});
