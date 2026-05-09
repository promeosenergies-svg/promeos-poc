/**
 * grammar/SolPageFooter — Alias canonique grammaire Sol §5.
 *
 * Re-exporte `ui/sol/SolPageFooter` sans modification.
 * Ce module est le point d'entrée contractuel du namespace grammar/
 * pour le primitif FOOTER (doctrine §5 : SOURCE · CONFIANCE · MIS A JOUR).
 *
 * Props (contrat inchangé) :
 *   @param {string} [props.source] - Source des donnees
 *   @param {'high'|'medium'|'low'} [props.confidence='medium'] - Niveau de confiance
 *   @param {string} [props.updatedAt] - ISO datetime de derniere mise a jour
 *   @param {string} [props.methodologyUrl] - URL ou route interne de methodologie
 *   @param {string} [props.className=''] - Classes CSS supplementaires
 *
 * Usage :
 *   import { SolPageFooter } from 'components/grammar';
 *   <SolPageFooter source="RegOps" confidence="high" updatedAt={ts} />
 */
export { default } from '../../ui/sol/SolPageFooter';
