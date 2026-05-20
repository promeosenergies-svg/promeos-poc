import { MASTHEAD_COPY } from '../constants';

/**
 * M2-5.10.A / .bis — Masthead Sol éditorial (maquette §8.3 lignes 703-707).
 *
 * Bandeau italique au-dessus des filtres : titre + sous-titre + date « MAJ
 * live ». Posé via la prop `editorialHeader` de `PageShell` pour court-
 * circuiter le H1 sans-serif Tailwind par défaut (audit M2-5.10.A — anti-
 * pattern doctrine Sol §6.1 « triptyque typographique brisé »).
 *
 * `total` est injecté côté `ActionCenterV4ListPage` depuis le hook V4 — c'est
 * le compteur backend (pas un nombre d'items filtrés). Pluralisation gérée
 * par `MASTHEAD_COPY.itemsSuffix`.
 */
export function Masthead({ total = 0, liveDate }) {
  // Si liveDate non fourni, fallback à la date courante (dériver inline plutôt
  // qu'en useMemo : la date n'est pas une dérivée props/state, et un useMemo
  // vide la fige au montage — leçon audit code-reviewer M2-5.10.A).
  const date =
    liveDate ||
    new Date().toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

  return (
    <div
      className="flex w-full items-baseline justify-between gap-4 pb-2.5"
      style={{ borderBottom: '1px solid var(--sol-ink-900)' }}
    >
      <div
        className="text-[13px] italic"
        style={{
          fontFamily: 'var(--sol-font-display)',
          color: 'var(--sol-ink-900)',
          letterSpacing: '0.02em',
        }}
      >
        <span className="font-semibold not-italic">{MASTHEAD_COPY.title}</span> ·{' '}
        {MASTHEAD_COPY.subtitle}
        {total > 0 && (
          <>
            {' · '}
            <span className="not-italic" style={{ color: 'var(--sol-ink-500)' }}>
              {MASTHEAD_COPY.itemsSuffix(total)}
            </span>
          </>
        )}
      </div>
      <div
        className="font-mono text-[10.5px] uppercase tracking-[0.16em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        {date} · {MASTHEAD_COPY.dateLive}
      </div>
    </div>
  );
}
