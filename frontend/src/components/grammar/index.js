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
 * Usage :
 *   import { SolPageFooter, Term, DecisionEvidenceCard } from 'components/grammar';
 */
export { default as SolPageFooter } from '../../ui/sol/SolPageFooter';
export { default as Term } from './Term';
export { default as DecisionEvidenceCard } from './DecisionEvidenceCard';
