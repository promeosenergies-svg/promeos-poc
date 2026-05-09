/**
 * grammar/ — Namespace des 6 primitifs grammaire Sol v1.1.
 *
 * Exports canoniques (doctrine §5 grammaire editoriale) :
 *
 *   SolPageFooter  — re-export DIRECT de ui/sol/SolPageFooter (la canonique)
 *                    Audit Phase 1.7 P2 : ancien alias grammar/SolPageFooter.jsx
 *                    retiré (zéro consommateur intermédiaire, bruit architectural).
 *   SolHero        — wrapper SolNarrative (kicker + titre + narrative + cta optionnel)
 *   KPISol         — wrapper KpiCard variant confidence + contrat KpiResult backend
 *   Term           — NOUVEAU acronyme + tooltip narratif (doctrine §6.4)
 *   WeekCard       — wrapper SolWeekCards single carte typee (4 variantes)
 *   DecisionEvidenceCard — NOUVEAU carte decision rang/evidence 4-8 cellules (doctrine §5.6)
 *
 * Usage :
 *   import { SolPageFooter, SolHero, KPISol, Term, WeekCard, DecisionEvidenceCard } from 'components/grammar';
 */
export { default as SolPageFooter } from '../../ui/sol/SolPageFooter';
export { default as SolHero } from './SolHero';
export { default as KPISol } from './KPISol';
export { default as Term } from './Term';
export { default as WeekCard } from './WeekCard';
export { default as DecisionEvidenceCard } from './DecisionEvidenceCard';
