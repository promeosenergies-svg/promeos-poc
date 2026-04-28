/**
 * SolFlexTeaser — Card minimaliste teaser vers Flex Intelligence.
 *
 * Phase 0.4 du sprint refonte cockpit dual sol2 (28/04/2026). Remplace
 * le bandeau « Pilotage des usages » 4 sub-cards (RadarPrixNegatifs +
 * RoiFlexReady + PortefeuilleScoring + NebcoSimulation) qui violait
 * l'anti-pattern doctrine §6.3 « bandeau Pilotage usages avec 4 sub-cards
 * en Vue Exécutive ».
 *
 * Cible maquette : `docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html`
 * section « TEASER FLEX INTELLIGENCE » — 1 card info bar + lien /flex.
 *
 * Composant pur display (doctrine §8.1 zero business logic frontend) :
 * lit `flex_potential` depuis `/api/cockpit/_facts.flex_potential`. Si
 * pas de gisement détecté, retourne null (pas d'empty state pleine
 * largeur, anti-pattern §6.1).
 *
 * Props :
 *   - flexPotential : { gisement_eur_an: number, sites_count: number,
 *                       archetypes: string[] } | null
 *   - onNavigate : function (route) — handler navigation /flex
 */
import { useNavigate } from 'react-router-dom';
import SolAcronym from './SolAcronym';

function fmtEurCompact(v) {
  if (!v || v <= 0) return '— €';
  if (v >= 1_000_000)
    return `${(v / 1_000_000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} M€`;
  if (v >= 1_000) return `${Math.round(v / 1_000).toLocaleString('fr-FR')} k€`;
  return `${Math.round(v).toLocaleString('fr-FR')} €`;
}

export default function SolFlexTeaser({ flexPotential, className = '' }) {
  const navigate = useNavigate();

  // Doctrine §6.1 : pas d'empty state pleine largeur — si pas de gisement,
  // on ne rend rien (le caller décide si la section reste visible ou non).
  if (!flexPotential || !flexPotential.gisement_eur_an || flexPotential.gisement_eur_an <= 0) {
    return null;
  }

  const { gisement_eur_an, sites_count = 0, archetypes = [] } = flexPotential;
  const archetypesLabel = archetypes.length > 0 ? archetypes.slice(0, 3).join(' · ') : null;

  return (
    <div
      data-testid="sol-flex-teaser"
      className={`flex items-center gap-3 flex-wrap rounded-md px-4 py-3 ${className}`}
      style={{
        background: 'var(--sol-bg-canvas, #f7f5ef)',
        border: '0.5px solid var(--sol-line, rgba(26,24,21,.12))',
      }}
    >
      <div className="flex-1 min-w-[200px] text-sm leading-relaxed text-[var(--sol-ink-700)]">
        <strong className="font-medium text-[var(--sol-calme-fg)]">
          Gisement Flex portefeuille — {fmtEurCompact(gisement_eur_an)}/an
        </strong>{' '}
        identifié sur {sites_count} site{sites_count > 1 ? 's' : ''}
        {archetypesLabel && ` (${archetypesLabel})`}. Activation possible via partenaire
        d'agrégation <SolAcronym code="NEBCO" />/<SolAcronym code="AOFD" />.
      </div>
      <button
        type="button"
        onClick={() => navigate('/flex')}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-[var(--sol-line,rgba(26,24,21,.22))] bg-white text-[var(--sol-ink-900)] hover:bg-[var(--sol-bg-canvas,#f7f5ef)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
        aria-label="Voir Flex Intelligence — détail radar prix négatifs, ROI Flex Ready, classement portefeuille"
      >
        Voir Flex Intelligence →
      </button>
    </div>
  );
}
