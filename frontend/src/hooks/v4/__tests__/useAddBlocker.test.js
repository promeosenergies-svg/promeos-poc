// @vitest-environment jsdom
/**
 * M2-5.1 — Tests hook mutation useAddBlocker.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4ActionCenter', () => ({
  addBlocker: vi.fn(),
}));

import { addBlocker } from '../../../services/api/v4ActionCenter';
import { useAddBlocker } from '../useAddBlocker';

describe('useAddBlocker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('execute adds the blocker and returns data', async () => {
    addBlocker.mockResolvedValue({ data: { id: 'b-1', reason: 'Attente facture' } });

    const { result } = renderHook(() => useAddBlocker());

    let returned;
    await act(async () => {
      returned = await result.current.execute('item-1', { reason: 'Attente facture' });
    });

    expect(addBlocker).toHaveBeenCalledWith('item-1', { reason: 'Attente facture' });
    expect(returned).toEqual({ id: 'b-1', reason: 'Attente facture' });
  });
});
