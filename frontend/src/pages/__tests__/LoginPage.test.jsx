// @vitest-environment jsdom
/**
 * M2-5.8.A.bis — Tests du bouton de connexion démo sur LoginPage (jsdom).
 *
 * Le formulaire email + password legacy n'est PAS testé ici (intouché par le
 * sprint) — seuls le probe DEMO_MODE et le bouton démo sont couverts.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: vi.fn() }),
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));
vi.mock('../LoginBackground', () => ({
  default: () => null,
}));

import api from '../../services/api';
import LoginPage from '../LoginPage';

const realLocation = window.location;

afterEach(() => {
  cleanup();
  Object.defineProperty(window, 'location', { configurable: true, value: realLocation });
  localStorage.clear();
});
beforeEach(() => {
  vi.clearAllMocks();
});

const DEMO_BTN = { name: /connexion démo helios/i };

describe('LoginPage — bouton connexion démo (M2-5.8.A.bis)', () => {
  test('no demo button when the probe reports available=false', async () => {
    api.get.mockResolvedValue({ data: { available: false } });
    render(<LoginPage />);
    // Laisse le probe se résoudre.
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/auth/demo-login/available'));
    expect(screen.queryByRole('button', DEMO_BTN)).not.toBeInTheDocument();
  });

  test('demo button appears when the probe reports available=true', async () => {
    api.get.mockResolvedValue({ data: { available: true } });
    render(<LoginPage />);
    await waitFor(() => expect(screen.getByRole('button', DEMO_BTN)).toBeInTheDocument());
  });

  test('no demo button when the probe fails (network / 5xx)', async () => {
    api.get.mockRejectedValue(new Error('Network'));
    render(<LoginPage />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByRole('button', DEMO_BTN)).not.toBeInTheDocument();
  });

  test('clicking the demo button calls /auth/demo-login and stores the token', async () => {
    api.get.mockResolvedValue({ data: { available: true } });
    api.post.mockResolvedValue({ data: { access_token: 'demo-jwt-xyz' } });
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { assign: vi.fn() },
    });

    render(<LoginPage />);
    await waitFor(() => screen.getByRole('button', DEMO_BTN));
    fireEvent.click(screen.getByRole('button', DEMO_BTN));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/demo-login');
      expect(localStorage.getItem('promeos_token')).toBe('demo-jwt-xyz');
      // M2-5.10.bis clôture — atterrissage Pilotage par défaut (audit CS/UX).
      expect(window.location.assign).toHaveBeenCalledWith('/action-center-v4/pilotage');
    });
  });

  test('a demo-login error shows an error message', async () => {
    api.get.mockResolvedValue({ data: { available: true } });
    api.post.mockRejectedValue({
      response: { data: { detail: { message: 'Connexion démo refusée' } } },
    });

    render(<LoginPage />);
    await waitFor(() => screen.getByRole('button', DEMO_BTN));
    fireEvent.click(screen.getByRole('button', DEMO_BTN));

    await waitFor(() => {
      expect(screen.getByText(/connexion démo refusée/i)).toBeInTheDocument();
    });
  });
});
