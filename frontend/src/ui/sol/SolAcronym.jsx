/**
 * SolAcronym — affichage accessible d'un acronyme avec définition tooltip.
 *
 * Sprint 2 Vague E ét16 (audit Marie DAF P0 #2 28/04/2026) :
 * « BACS/APER/Décret Tertiaire sans gloss = je décroche dès la 3ᵉ ligne ».
 *
 * Doctrine §5 grammaire éditoriale + §13 a11y WCAG 2.2 :
 *   - `<abbr title="...">` natif HTML5 (lecteurs d'écran)
 *   - underline dotted Sol token (signal visuel "il y a quelque chose")
 *   - cursor help (signal de hover possible)
 *   - tooltip survol (titre HTML natif — pas de modale, lisible mobile)
 *
 * Usage :
 *   <SolAcronym code="BACS" /> → rend "BACS" + tooltip
 *   <SolAcronym code="Décret Tertiaire" />
 *   <SolAcronym code="BACS">décret BACS</SolAcronym> → texte custom + tooltip BACS
 *   <SolAcronym code="UNKNOWN">Whatever</SolAcronym> → fallback : pas de gloss
 *
 * Source de vérité : `frontend/src/domain/glossary.js` (GLOSSARY map).
 */
import { getDefinition, isGlossed } from '../../domain/glossary';

export default function SolAcronym({ code, children, className = '' }) {
  const definition = getDefinition(code);
  const display = children ?? code;

  // Si pas de définition glossée, on rend le texte brut (pas de friction visuelle)
  if (!isGlossed(code)) {
    return <span className={className}>{display}</span>;
  }

  return (
    <abbr
      title={definition}
      className={`underline decoration-dotted decoration-[var(--sol-ink-300)] underline-offset-2 cursor-help hover:decoration-[var(--sol-calme-fg)] ${className}`}
      // ARIA explicite pour lecteurs d'écran (compl. au title natif)
      aria-label={`${display} : ${definition}`}
    >
      {display}
    </abbr>
  );
}
