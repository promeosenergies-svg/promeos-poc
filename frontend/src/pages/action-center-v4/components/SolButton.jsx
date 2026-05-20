/**
 * M2-5.11.A — Bouton Sol pour les modals V4 (variants primary / ghost /
 * danger). Remplace `src/ui/Button` Tailwind dans les 5 modals Sol
 * (LifecycleTransition / EvidenceUpload / EvidenceVerify / BlockerAdd /
 * BlockerResolve).
 *
 * Variantes :
 * - `primary` : sombre ink-900 sur paper (CTA principal modal)
 * - `ghost`   : transparent + ink-700 (annuler / actions secondaires)
 * - `danger`  : refuse-bg / refuse-fg (suppressions, transitions terminales)
 *
 * `loading` désactive le bouton et permet à l'appelant de changer le label
 * (cf. `submitLoading` dans les constants modals).
 */
const BASE =
  'inline-flex items-center justify-center gap-1.5 rounded-[6px] border px-3.5 py-2 font-sans text-[12.5px] font-semibold transition ' +
  'disabled:cursor-not-allowed disabled:opacity-50 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]';

const VARIANTS = {
  primary: {
    background: 'var(--sol-ink-900)',
    color: 'var(--sol-bg-paper)',
    borderColor: 'var(--sol-ink-900)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--sol-ink-700)',
    borderColor: 'transparent',
  },
  danger: {
    background: 'var(--sol-refuse-bg)',
    color: 'var(--sol-refuse-fg)',
    borderColor: 'var(--sol-refuse-line)',
  },
  secondary: {
    background: 'var(--sol-bg-paper)',
    color: 'var(--sol-ink-900)',
    borderColor: 'var(--sol-ink-300)',
  },
};

export function SolButton({
  variant = 'primary',
  type = 'button',
  disabled = false,
  loading = false,
  onClick,
  children,
  className = '',
  ...rest
}) {
  const style = VARIANTS[variant] || VARIANTS.primary;
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${BASE} ${className}`}
      style={style}
      {...rest}
    >
      {children}
    </button>
  );
}
