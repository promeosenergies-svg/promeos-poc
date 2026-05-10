/**
 * grammar/hub/ — Exports des primitifs L11 Hub Page.
 *
 * Sprint Grammaire v1.2 / Phase 3.4 — Loi L11 Hub Page (doctrine §12).
 *
 * Composants :
 *   HubPage              — wrapper compound component (slots KpiTriptych/ChartPair/Highlights)
 *   SolHeroPremiumNight  — hero bleu nuit + illustration filaire SVG
 *   ChartFrame           — question + reponse + chart slot + footer SCM
 *   HubHighlight         — ligne action-card compacte (rang/severity/invitation)
 *   HubPageFooter        — alias SolPageFooter (Source · Confiance · MAJ)
 *
 * Usage :
 *   import { HubPage, SolHeroPremiumNight, ChartFrame, HubHighlight, HubPageFooter }
 *     from 'components/grammar/hub';
 */
export { default as HubPage } from './HubPage';
export { default as SolHeroPremiumNight } from './SolHeroPremiumNight';
export { default as ChartFrame } from './ChartFrame';
export { default as HubHighlight } from './HubHighlight';
export { default as HubPageFooter } from './HubPageFooter';
