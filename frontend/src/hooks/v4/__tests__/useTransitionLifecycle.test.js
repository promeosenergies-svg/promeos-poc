// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useTransitionLifecycle.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  transitionLifecycle: vi.fn(),
}));

import { transitionLifecycle } from '../../../services/api/v4ActionCenter';
import { useTransitionLifecycle } from '../useTransitionLifecycle';

describe('useTransitionLifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute transitions the item and returns data', async () => {
    transitionLifecycle.mockResolvedValue({
      data: { id: 'item-1', lifecycle_state: 'triaged' },
    });

    const { result } = renderHook(() => useTransitionLifecycle());

    let returned;
    await act(async () => {
      returned = await result.current.execute('item-1', { to_state: 'triaged' });
    });

    expect(transitionLifecycle).toHaveBeenCalledWith('item-1', { to_state: 'triaged' });
    expect(returned).toEqual({ id: 'item-1', lifecycle_state: 'triaged' });
    expect(result.current.data).toEqual({ id: 'item-1', lifecycle_state: 'triaged' });
  });

  test('reset clears data and error', async () => {
    transitionLifecycle.mockResolvedValue({ data: { id: 'item-1' } });

    const { result } = renderHook(() => useTransitionLifecycle());

    await act(async () => {
      await result.current.execute('item-1', { to_state: 'planned' });
    });
    expect(result.current.data).not.toBeNull();

    act(() => {
      result.current.reset();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
