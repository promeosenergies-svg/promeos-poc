/**
 * AcronymTooltip — Wrapper inline qui rend un acronyme avec tooltip glossaire
 * (refonte WOW Étape 2.bis · 29/04/2026).
 *
 * Convergence audits Marie + Sophie + /frontend-design : tous les acronymes
 * énergie/réglementaires (BACS, TURPE, ARENH, VNU, CBAM, CEE, DT, OPERAT,
 * EPEX, NEBCO, AOFD, GTB, CDC, EMS, DJU) doivent être glossés inline pour
 * un dirigeant non-sachant 3 min en CODIR.
 *
 * Pattern : style border-bottom dotted + cursor help + tooltip natif HTML.
 * V2 (post-sprint) : remplaçable par un Popover Sol avec citation +
 * lien méthodologie sur tap mobile.
 *
 * Doctrine §6.4 (acronyme → récit) appliquée au site d'affichage.
 *
 * Props :
 *   - acronym : string — ex. "BACS", "TURPE 7", "ARENH"
 *   - children : ReactNode (optionnel) — texte custom si différent du sigle
 *   - className : string
 */
import { acronymTooltip, isKnownAcronym } from '../../utils/acronyms';

export default function AcronymTooltip({ acronym, children, className = '' }) {
  // Si l'acronyme contient un suffixe (ex. "TURPE 7" → utiliser "TURPE")
  const key = acronym?.split(/\s+/)[0]?.toUpperCase();
  const tooltip = isKnownAcronym(key) ? acronymTooltip(key) : null;
  if (!tooltip) {
    return <span className={className}>{children || acronym}</span>;
  }
  return (
    <span
      tabIndex={0}
      role="button"
      aria-label={tooltip}
      title={tooltip}
      className={`cursor-help ${className}`}
      style={{
        borderBottom: '1px dotted var(--sol-ink-400)',
        textDecoration: 'none',
      }}
    >
      {children || acronym}
    </span>
  );
}
