/**
 * grammar/SolHero — Wrapper standardise grammaire Sol §5.
 *
 * Contrat clair du primitif HERO : kicker + titre + narrative + cta optionnel.
 * Delegue vers SolNarrative (qui inclut deja le pattern kicker/titre/narrative
 * complet) pour les cas riches, et vers SolPageHeader pour les en-tetes pures.
 *
 * Choix d'implementation : SolNarrative est le composant le plus proche du
 * contrat HERO doctrine (kicker + h1 + narrative + KPIs max 3). SolPageHeader
 * couvre le cas header seul (kicker + titre + rightSlot).
 *
 * Ce wrapper unifie les deux sous un seul contrat grammaire, en masquant
 * les details d'implementation internes.
 *
 * Display-only — zero calcul metier (regle d'or §8.1).
 *
 * @param {Object} props
 * @param {string} [props.kicker] - Kicker mono uppercase (ex. "GROUPE HELIOS · 5 SITES")
 * @param {string} props.titre - Titre principal (Fraunces display)
 * @param {string} [props.italicHook] - Italic hook subordonee au titre
 * @param {string} [props.narrative] - Texte narratif 2-3 lignes sourcee
 * @param {Array<{label:string,value:string|number,unit?:string,tooltip?:string,source?:string}>} [props.kpis=[]] - Max 3 KPIs
 * @param {{label:string,href:string}} [props.cta] - CTA optionnel
 * @param {string} [props.className=''] - Classes CSS supplementaires
 */
import SolNarrative from '../../ui/sol/SolNarrative';

export default function SolHero({
  kicker,
  titre,
  italicHook,
  narrative,
  kpis = [],
  cta,
  className = '',
}) {
  return (
    <div data-testid="sol-hero" className={className}>
      <SolNarrative
        kicker={kicker}
        title={titre}
        italicHook={italicHook}
        narrative={narrative}
        kpis={kpis}
      />
      {cta && (
        <div className="mt-4">
          <a
            href={cta.href}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--sol-calme-fg)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded px-1 py-0.5"
          >
            {cta.label}
          </a>
        </div>
      )}
    </div>
  );
}
