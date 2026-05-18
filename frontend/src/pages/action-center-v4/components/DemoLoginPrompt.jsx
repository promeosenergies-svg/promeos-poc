import { useCallback } from 'react';

import Button from '../../../ui/Button';

import { useDemoLogin } from '../../../hooks/v4/useDemoLogin';
import { DEMO_LOGIN_COPY } from '../constants';

/**
 * M2-5.8.A — Prompt inline affiché à la place de la liste quand le pilote n'a
 * pas de token (résout le P0-1 de l'audit M2-5). UX : 2 clics maximum — ouvrir
 * l'URL puis « Se connecter ». Pas de redirection vers un écran de login.
 */
export function DemoLoginPrompt({ onLoginSuccess }) {
  const { execute, loading, error } = useDemoLogin();

  const handleClick = useCallback(async () => {
    try {
      await execute();
      onLoginSuccess?.();
    } catch {
      // Erreur déjà exposée via `error` (state du hook) — rien à faire ici.
    }
  }, [execute, onLoginSuccess]);

  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <h2 className="mb-2 text-lg font-semibold text-gray-900">{DEMO_LOGIN_COPY.title}</h2>
      <p className="mb-6 max-w-md text-sm text-gray-600">{DEMO_LOGIN_COPY.description}</p>
      <Button onClick={handleClick} disabled={loading}>
        {loading ? DEMO_LOGIN_COPY.buttonLoading : DEMO_LOGIN_COPY.buttonLabel}
      </Button>
      {error && (
        <div
          role="alert"
          className="mt-4 max-w-md rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900"
        >
          {error.message}
        </div>
      )}
    </div>
  );
}
