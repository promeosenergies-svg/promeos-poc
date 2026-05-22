import { useEffect, useState } from 'react';

import { MASTHEAD_COPY } from '../constants';

/**
 * M2-5.10.A → M2-5.12 — Masthead Sol éditorial (maquette Sophie Marin
 * 2026-05-22, mise à jour majeure du masthead §8.3 historique).
 *
 * Bandeau italique au-dessus des filtres : titre + persona (M2-5.12) +
 * sous-titre contextuel + compteur explicite. À droite : date + heure live
 * (M2-5.12) + tag MAJ LIVE. Posé via la prop `editorialHeader` de
 * `PageShell` pour court-circuiter le H1 sans-serif Tailwind par défaut
 * (anti-pattern doctrine Sol §6.1 « triptyque typographique brisé »).
 *
 * Props :
 *  - `total` (number) : compteur d'items (fallback suffixe « N items »)
 *  - `subtitle` (string) : sous-titre contextuel (défaut « Référentiel complet »)
 *  - `countLabel` (string) : libellé compteur contextuel (override `total`)
 *  - `persona` (string) : « Sophie Marin · Resp. Énergie HELIOS » (M2-5.12)
 *  - `liveDate` (string) : override date (sinon dérivée locale FR)
 *  - `withLiveTime` (bool) : affiche HH:mm live avec setInterval 60s (M2-5.12)
 *
 * Le compteur historique (« N actions prioritaires », « N items ») reste
 * en suffixe du sous-titre quand `countLabel` est passé.
 */
export function Masthead({
  total = 0,
  liveDate,
  subtitle,
  countLabel,
  persona,
  withLiveTime = false,
}) {
  // M2-5.12 — heure live (HH:mm). useState + setInterval 60s pour éviter le
  // re-render de toute la page chaque seconde ; l'écran change à la minute.
  // Si `withLiveTime=false`, le state reste à null et le render est skip.
  const [liveTime, setLiveTime] = useState(() =>
    withLiveTime ? formatLiveTime(new Date()) : null
  );
  useEffect(() => {
    if (!withLiveTime) return undefined;
    const tick = () => setLiveTime(formatLiveTime(new Date()));
    tick(); // sync immédiatement au montage
    const interval = setInterval(tick, 60_000);
    return () => clearInterval(interval);
  }, [withLiveTime]);

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
        <span className="font-semibold not-italic">{MASTHEAD_COPY.title}</span>
        {/* M2-5.12 — Persona inséré entre titre et subtitle : « Sophie Marin ·
            Resp. Énergie HELIOS » (maquette). Italique Fraunces hérité du
            parent. Le séparateur reste « · » canonique grammaire Sol §5. */}
        {persona && <> · {persona}</>}
        {' · '}
        {renderedSubtitle}
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
        // a11y : ne pas annoncer la minute live à chaque tick (anti-bruit
        // lecteurs d'écran). `aria-live=off` explicite — seul le tag final
        // "MAJ LIVE" est sémantique.
        aria-live="off"
      >
        {date}
        {liveTime && (
          <>
            {' · '}
            <span style={{ color: 'var(--sol-ink-700)' }}>{liveTime}</span>
          </>
        )}
        {' · '}
        {MASTHEAD_COPY.dateLive}
      </div>
    </div>
  );
}

/**
 * Formate l'heure live au format HH:mm en locale FR. Extrait pour
 * testabilité (le composant lui-même est testé via Vitest jsdom, ce helper
 * pur n'a besoin que d'un test unit simple).
 */
function formatLiveTime(date) {
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
