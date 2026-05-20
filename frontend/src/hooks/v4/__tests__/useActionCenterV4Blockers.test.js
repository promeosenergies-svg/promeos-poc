// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Blockers.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItemBlockers: vi.fn(),
}));

import { fetchItemBlockers } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Blockers } from '../useActionCenterV4Blockers';

describe('useActionCenterV4Blockers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads blockers on mount for a given item', async () => {
    fetchItemBlockers.mockResolvedValue({
      data: { blockers: [{ id: 'b1' }], total: 1, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Blockers('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItemBlockers).toHaveBeenCalledWith('item-1', { offset: 0, limit: 50 });
    expect(result.current.data.blockers).toEqual([{ id: 'b1' }]);
  });
});
