/**
 * grammar/ — Namespace des primitifs grammaire Sol v1.1 réellement consommés.
 *
 * Exports canoniques (doctrine §5 grammaire editoriale) :
 *
 *   SolPageFooter        — re-export ui/sol/SolPageFooter (Source · Confiance · Mis à jour, Loi L6)
 *   Term                 — acronyme + tooltip narratif (doctrine §6.4)
 *   DecisionEvidenceCard — carte décision rang/evidence 4-8 cellules (doctrine §5.6 Loi L9)
 *
 * Audit Phase 3.0 P2 (simplify 09/05) : SolHero / KPISol / WeekCard retirés
 * (zéro consommateur, ~430 LOC dette pure). Phase 1.2 les avait créés en
 * anticipation mais aucune des vues livrées Lego (CockpitPilotage,
 * ActionCenterSlideOver, ConformitePage) ne les utilisait. Patterns hero/KPI/
 * weekcards déjà incarnés par SolPageHeader, KpiCard, SolWeekCards canoniques.
 *
 * Sprint Grammaire v1.2 / Phase 3.4 — primitifs L11 Hub Page (doctrine §12) :
 *   HubPage              — wrapper compound component (slots KpiTriptych/ChartPair/Highlights)
 *   SolHeroPremiumNight  — hero bleu nuit + illustration filaire SVG
 *   ChartFrame           — question + reponse + chart slot + footer SCM
 *   HubHighlight         — ligne action-card compacte rang/severity/invitation
 *   HubPageFooter        — alias SolPageFooter (Source · Confiance · MAJ)
 *
 * Usage :
 *   import { SolPageFooter, Term, DecisionEvidenceCard } from 'components/grammar';
 *   import { HubPage, SolHeroPremiumNight, ChartFrame, HubHighlight, HubPageFooter }
 *     from 'components/grammar';
 */
export { default as SolPageFooter } from '../../ui/sol/SolPageFooter';
export { default as Term } from './Term';
export { default as DecisionEvidenceCard } from './DecisionEvidenceCard';

// Sprint Grammaire v1.2 / Phase 3.4 — primitifs L11 Hub Page
export { default as HubPage } from './hub/HubPage';
export { default as SolHeroPremiumNight } from './hub/SolHeroPremiumNight';
export { default as ChartFrame } from './hub/ChartFrame';
export { default as HubHighlight } from './hub/HubHighlight';
export { default as HubPageFooter } from './hub/HubPageFooter';
