/**
 * PROMEOS — Focus ring utility partagée pour composants Sol
 *
 * Avant : 3 duplications identiques dans SolPanel, SolRail, AperSol Reset.
 * Après : constante unique importée. Si la palette Sol ajoute un token
 * `--sol-focus-ring` un jour, seul ce fichier change.
 */
export const FOCUS_RING_SOL =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1';
