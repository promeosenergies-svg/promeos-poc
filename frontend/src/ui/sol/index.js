/**
 * PROMEOS — Sol V1 UI components (refonte Phase 1, 21 composants).
 *
 * Composants de présentation pure. Zéro logique métier, zéro fetch, zéro
 * calcul. Tout ce qu'ils affichent vient de props déjà formatés par
 * l'appelant — sauf SolRail et SolPanel qui lisent le NavRegistry
 * (structure statique, pas de données dynamiques).
 *
 * Source de vérité visuelle : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 * Insight UX-1 : "journal en terrasse" — slate pro + accents warm.
 */

// Header / voice éditoriale
export { default as SolPageHeader } from './SolPageHeader';
export { default as SolHeadline } from './SolHeadline';
export { default as SolSubline } from './SolSubline';

// Data display signature
export { default as SolKpiRow } from './SolKpiRow';
export { default as SolKpiCard } from './SolKpiCard';
export { default as SolSourceChip } from './SolSourceChip';
export { default as SolStatusPill } from './SolStatusPill';
export { default as SolSectionHead } from './SolSectionHead';

// Hero agentique + cartouche
export { default as SolHero } from './SolHero';
export { default as SolCartouche } from './SolCartouche';
export { default as SolPendingBanner } from './SolPendingBanner';

// Week grid (À regarder / À faire / Bonne nouvelle)
export { default as SolWeekGrid } from './SolWeekGrid';
export { default as SolWeekCard } from './SolWeekCard';

// Courbe + timerail
export { default as SolLoadCurve } from './SolLoadCurve';
export { default as SolTimerail } from './SolTimerail';

// Modes d'affichage
export { default as SolLayerToggle } from './SolLayerToggle';
export { default as SolInspectDoc } from './SolInspectDoc';
export { default as SolExpertGrid } from './SolExpertGrid';
export { default as SolJournal } from './SolJournal';

// Shell + navigation
export { default as SolRail } from './SolRail';
export { default as SolPanel } from './SolPanel';
export { default as SolAppShell } from './SolAppShell';

// Overlays
export { default as SolDrawer } from './SolDrawer';

// Primitives
export { default as SolButton } from './SolButton';
