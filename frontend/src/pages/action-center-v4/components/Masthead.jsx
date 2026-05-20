import { MASTHEAD_COPY } from '../constants';

/**
 * M2-5.10.A / .bis / M2-5.10.bis clôture — Masthead Sol éditorial (maquette §8.3
 * lignes 703-707).
 *
 * Bandeau italique au-dessus des filtres : titre + sous-titre contextuel +
 * compteur explicite. Posé via la prop `editorialHeader` de `PageShell`
 * pour court-circuiter le H1 sans-serif Tailwind par défaut (anti-pattern
 * doctrine Sol §6.1 « triptyque typographique brisé »).
 *
 * M2-5.10.bis clôture (audit cross-pages) : `subtitle` et `countLabel` sont
 * désormais props pour permettre à chaque page (Référentiel, Pilotage,
 * Journal) d'afficher son contexte propre. Sans ces props, fallback sur
 * `MASTHEAD_COPY.subtitle` (« Référentiel complet ») et le suffixe
 * pluralisé « N items » (compatibilité rétroactive Référentiel).
 *
 * `total` est injecté côté page (depuis le hook V4 ou la liste affichée).
 */
export function Masthead({ total = 0, liveDate, subtitle, countLabel }) {
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

  const renderedSubtitle = subtitle || MASTHEAD_COPY.subtitle;
  // Fallback compteur : suffixe pluralisé « N items » (cohérent Référentiel
  // historique). Si la page veut un libellé contextuel (« 5 actions
  // prioritaires », « 38 événements 7j »), elle passe `countLabel`.
  const renderedCount =
    countLabel != null ? countLabel : total > 0 ? MASTHEAD_COPY.itemsSuffix(total) : null;

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
        <span className="font-semibold not-italic">{MASTHEAD_COPY.title}</span> · {renderedSubtitle}
        {renderedCount && (
          <>
            {' · '}
            <span className="not-italic" style={{ color: 'var(--sol-ink-500)' }}>
              {renderedCount}
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
