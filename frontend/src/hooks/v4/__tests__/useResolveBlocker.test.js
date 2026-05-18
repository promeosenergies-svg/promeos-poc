// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useResolveBlocker.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  resolveBlocker: vi.fn(),
}));

import { resolveBlocker } from '../../../services/api/v4ActionCenter';
import { useResolveBlocker } from '../useResolveBlocker';

describe('useResolveBlocker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute resolves the blocker and returns data', async () => {
    resolveBlocker.mockResolvedValue({ data: { id: 'b-1', resolved: true } });

    const { result } = renderHook(() => useResolveBlocker());

    let returned;
    await act(async () => {
      returned = await result.current.execute('b-1', { resolution: 'reçue' });
    });

    expect(resolveBlocker).toHaveBeenCalledWith('b-1', { resolution: 'reçue' });
    expect(returned).toEqual({ id: 'b-1', resolved: true });
  });
});
