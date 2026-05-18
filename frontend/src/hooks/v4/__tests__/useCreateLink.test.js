// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useCreateLink.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  createLink: vi.fn(),
}));

import { createLink } from '../../../services/api/v4ActionCenter';
import { useCreateLink } from '../useCreateLink';

describe('useCreateLink', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute creates the link and returns data', async () => {
    createLink.mockResolvedValue({ data: { id: 'lk-1' } });

    const { result } = renderHook(() => useCreateLink());

    let returned;
    await act(async () => {
      returned = await result.current.execute('item-1', {
        target_module: 'invoice',
        target_id: 'inv-1',
      });
    });

    expect(createLink).toHaveBeenCalledWith('item-1', {
      target_module: 'invoice',
      target_id: 'inv-1',
    });
    expect(returned).toEqual({ id: 'lk-1' });
  });
});
