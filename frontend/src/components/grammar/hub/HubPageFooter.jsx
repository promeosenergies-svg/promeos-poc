/**
 * grammar/hub/HubPageFooter — Alias SolPageFooter pour les pages Hub L11.
 *
 * Re-export direct de ui/sol/SolPageFooter.
 * Aucune logique propre — coherence nommage dans le namespace hub/.
 *
 * Doctrine §12 Loi L11.5 : chaque Hub Page se termine par un footer
 * Source · Confiance · Mis a jour (grammaire SolPageFooter L6).
 *
 * Usage :
 *   import HubPageFooter from 'components/grammar/hub/HubPageFooter';
 *   <HubPageFooter source="EMS PROMEOS" confidence="high" updatedAt={new Date().toISOString()} />
 *
 * Props passes en pass-through a SolPageFooter :
 * @param {string} [props.source]
 * @param {'high'|'medium'|'low'} [props.confidence='medium']
 * @param {string} [props.updatedAt]
 * @param {string} [props.methodologyUrl]
 * @param {string} [props.className='']
 */
export { default } from '../../../ui/sol/SolPageFooter';
