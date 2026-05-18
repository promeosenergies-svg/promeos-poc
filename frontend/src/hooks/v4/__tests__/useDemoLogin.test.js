// @vitest-environment jsdom
/**
 * M2-5.8.A — Tests du hook useDemoLogin (renderHook, jsdom requis).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../../services/api/v4Auth', () => ({
  demoLogin: vi.fn(),
}));

import { demoLogin } from '../../../services/api/v4Auth';
import { useDemoLogin } from '../useDemoLogin';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useDemoLogin', () => {
  test('execute resolves and clears the loading state', async () => {
    demoLogin.mockResolvedValue({ user_email: 'marie.dupont@helios.demo', organisation_id: 1 });
    const { result } = renderHook(() => useDemoLogin());

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  test('a 404 sets an explicit "demo mode off" error message', async () => {
    const err = new Error('Not Found');
    err.response = { status: 404 };
    demoLogin.mockRejectedValue(err);

    const { result } = renderHook(() => useDemoLogin());
    await act(async () => {
      try {
        await result.current.execute();
      } catch {
        /* erreur propagée — capturée par le composant appelant */
      }
    });

    expect(result.current.error.message).toMatch(/mode démo n.est pas activé/i);
  });

  test('reset clears the error', async () => {
    const err = new Error('fail');
    err.response = { status: 500 };
    demoLogin.mockRejectedValue(err);

    const { result } = renderHook(() => useDemoLogin());
    await act(async () => {
      try {
        await result.current.execute();
      } catch {
        /* attendu */
      }
    });
    expect(result.current.error).not.toBeNull();

    act(() => result.current.reset());
    expect(result.current.error).toBeNull();
  });
});
