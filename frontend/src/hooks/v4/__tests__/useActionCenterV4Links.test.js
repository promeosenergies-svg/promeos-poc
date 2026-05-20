// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Links.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItemLinks: vi.fn(),
}));

import { fetchItemLinks } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Links } from '../useActionCenterV4Links';

describe('useActionCenterV4Links', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads links on mount for a given item', async () => {
    fetchItemLinks.mockResolvedValue({
      data: { links: [{ id: 'l1' }], total: 1, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Links('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItemLinks).toHaveBeenCalledWith('item-1', { offset: 0, limit: 50 });
    expect(result.current.data.links).toEqual([{ id: 'l1' }]);
  });
});
