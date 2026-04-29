/**
 * SolKickerWithSwitch — kicker mono uppercase avec switch route Briefing↔Synthèse.
 *
 * Phase 1.2 du sprint refonte cockpit dual sol2 (29/04/2026). Matérialise
 * la mécanique réciproque op↔exé doctrine §11.3 : l'utilisateur navigue
 * fluidement entre Briefing du jour (energy manager 30s) et Synthèse
 * stratégique (DG/CFO 3min) sans tabs séparées ni doublon nav.
 *
 * Cibles maquettes :
 *   - `docs/maquettes/cockpit-sol2/cockpit-pilotage-briefing-jour.html`
 *     lignes 219-225 (kicker + switch active "Briefing du jour")
 *   - `docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html`
 *     même section avec switch active "Synthèse stratégique"
 *
 * Anti-patterns évités (doctrine §6.3) :
 *   - Pas de tabs séparées au-dessus du H1 (doublon nav)
 *   - Pas de "Switch éditorial" en flottant (intégré au kicker)
 *
 * Composant pur display (doctrine §8.1 zero business logic frontend) :
 * props-driven, zero fetch. Le caller (page Cockpit) fournit `scope` +
 * `currentRoute`.
 *
 * Props :
 *   - scope : string — kicker prefix ex: "Cockpit · groupe HELIOS — 5 sites"
 *   - currentRoute : 'jour' | 'strategique' — détermine l'élément actif
 *   - className : string — classes additionnelles
 */
import { Link } from 'react-router-dom';

const ROUTES = Object.freeze({
  jour: { path: '/cockpit/jour', label: 'Briefing du jour' },
  strategique: { path: '/cockpit/strategique', label: 'Synthèse stratégique' },
});

export default function SolKickerWithSwitch({ scope = '', currentRoute = 'jour', className = '' }) {
  const linkClass = (isActive) =>
    `px-2 py-0.5 rounded transition-colors ${
      isActive
        ? 'bg-[var(--sol-bg-canvas,#f7f5ef)] text-[var(--sol-ink-900)]'
        : 'text-[var(--sol-ink-400)] hover:text-[var(--sol-ink-700)]'
    }`;

  return (
    <div
      data-testid="sol-kicker-with-switch"
      className={`sol-page-kicker flex items-center gap-2 flex-wrap ${className}`}
    >
      {scope && (
        <>
          <span>{scope}</span>
          <span aria-hidden="true">·</span>
        </>
      )}
      <span role="tablist" aria-label="Vue Cockpit" className="inline-flex items-center gap-1">
        <Link
          to={ROUTES.jour.path}
          role="tab"
          aria-selected={currentRoute === 'jour'}
          data-testid="sol-kicker-switch-jour"
          className={linkClass(currentRoute === 'jour')}
        >
          {ROUTES.jour.label}
        </Link>
        <span aria-hidden="true" className="text-[var(--sol-ink-300)]">
          ·
        </span>
        <Link
          to={ROUTES.strategique.path}
          role="tab"
          aria-selected={currentRoute === 'strategique'}
          data-testid="sol-kicker-switch-strategique"
          className={linkClass(currentRoute === 'strategique')}
        >
          {ROUTES.strategique.label}
        </Link>
      </span>
    </div>
  );
}
