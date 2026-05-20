import { AlertCircle } from 'lucide-react';

/**
 * M2-5.11.A — Bandeau d'erreur inline Sol pour les modals V4 (audit UI
 * Sol P1-3 — remplace `rounded border-red-200 bg-red-50` Tailwind).
 *
 * Couleurs `--sol-refuse-*` (palette « dérive » émotionnelle). Affiche
 * `message` obligatoire + `hint` optionnel sur une 2e ligne italique.
 * Posé avec `role="alert"` pour annonce aux lecteurs d'écran.
 */
export function SolInlineError({ error }) {
  if (!error) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-[6px] border p-3 text-[12.5px] leading-[1.45]"
      style={{
        background: 'var(--sol-refuse-bg)',
        borderColor: 'var(--sol-refuse-line)',
        color: 'var(--sol-refuse-fg)',
      }}
    >
      <AlertCircle
        size={14}
        aria-hidden="true"
        style={{ color: 'var(--sol-refuse-fg)', flexShrink: 0, marginTop: '1px' }}
      />
      <div className="flex-1">
        <div className="font-medium" style={{ color: 'var(--sol-refuse-fg)' }}>
          {error.message}
        </div>
        {error.hint && (
          <div
            className="mt-1 text-[11.5px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-refuse-fg)',
              opacity: 0.85,
            }}
          >
            {error.hint}
          </div>
        )}
      </div>
    </div>
  );
}
