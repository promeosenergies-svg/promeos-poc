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
export { default as HubKpiCard } from './HubKpiCard';

// Synthèse Stratégique v1.0 (Phase 3.5 Vague D) — primitifs polymorphiques.
export { default as StrategicModeBanner } from './StrategicModeBanner';
export { default as CadreApplicable } from './CadreApplicable';
export { default as VerdictFinal } from './VerdictFinal';
export { default as DossierP1 } from './DossierP1';
export { default as QueueP2P3 } from './QueueP2P3';
export { default as ChartFrameTrajectoryLine } from './charts/ChartFrameTrajectoryLine';
export { default as ChartFrameBenchSites } from './charts/ChartFrameBenchSites';
// Phase 3.6 Vague CC — charts pour Procurement + Opportunity
export { default as ChartFrameForwardCurve } from './charts/ChartFrameForwardCurve';
export { default as ChartFrameOpportunityMap } from './charts/ChartFrameOpportunityMap';
