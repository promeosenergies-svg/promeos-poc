// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook useActionCenterV4Events (timeline, garde itemId).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  fetchItemEvents: vi.fn(),
}));

import { fetchItemEvents } from '../../../services/api/v4ActionCenter';
import { useActionCenterV4Events } from '../useActionCenterV4Events';

describe('useActionCenterV4Events', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads events on mount for a given item', async () => {
    fetchItemEvents.mockResolvedValue({
      data: { events: [{ id: 'e1' }], total: 1, offset: 0, limit: 50 },
    });

    const { result } = renderHook(() => useActionCenterV4Events('item-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItemEvents).toHaveBeenCalledWith('item-1', { offset: 0, limit: 50 });
    expect(result.current.data.events).toEqual([{ id: 'e1' }]);
  });

  test('does not fetch when itemId is absent', async () => {
    const { result } = renderHook(() => useActionCenterV4Events(undefined));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchItemEvents).not.toHaveBeenCalled();
    expect(result.current.data).toBeNull();
  });
});
