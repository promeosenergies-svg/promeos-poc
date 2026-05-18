// @vitest-environment jsdom
/**
 * M2-5.8.A — Tests du composant DemoLoginPrompt (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4/useDemoLogin', () => ({
  useDemoLogin: vi.fn(),
}));

import { useDemoLogin } from '../../../hooks/v4/useDemoLogin';
import { DemoLoginPrompt } from '../components/DemoLoginPrompt';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe('DemoLoginPrompt', () => {
  test('renders the title and the connect button', () => {
    useDemoLogin.mockReturnValue({ execute: vi.fn(), loading: false, error: null, reset: vi.fn() });
    render(<DemoLoginPrompt />);
    expect(screen.getByText(/mode démo helios/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /se connecter/i })).toBeInTheDocument();
  });

  test('clicking the button calls execute then onLoginSuccess on success', async () => {
    const execute = vi.fn().mockResolvedValue({});
    const onLoginSuccess = vi.fn();
    useDemoLogin.mockReturnValue({ execute, loading: false, error: null, reset: vi.fn() });

    render(<DemoLoginPrompt onLoginSuccess={onLoginSuccess} />);
    fireEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalled();
      expect(onLoginSuccess).toHaveBeenCalled();
    });
  });

  test('the loading state disables the button and changes its label', () => {
    useDemoLogin.mockReturnValue({ execute: vi.fn(), loading: true, error: null, reset: vi.fn() });
    render(<DemoLoginPrompt />);
    expect(screen.getByText(/connexion…/i)).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  test('displays the error message when an error is present', () => {
    useDemoLogin.mockReturnValue({
      execute: vi.fn(),
      loading: false,
      error: { message: "Le mode démo n'est pas activé" },
      reset: vi.fn(),
    });
    render(<DemoLoginPrompt />);
    expect(screen.getByText(/mode démo n.est pas activé/i)).toBeInTheDocument();
  });
});
