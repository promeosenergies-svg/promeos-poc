/**
 * M2-5.2 — Constantes UI Centre d'Action V4 liste.
 *
 * Copy FR + mappings tokens. Doctrine PROMEOS : zéro anglais UI, zéro couleur
 * hardcodée (les couleurs viennent du composant Badge via le prop `status`).
 */

// Mapping lifecycle → label FR (cohérent doctrine V4 — 5 états).
export const LIFECYCLE_LABELS = {
  new: 'Nouveau',
  triaged: 'Trié',
  planned: 'Planifié',
  in_progress: 'En cours',
  closed: 'Clôturé',
};

// Ordre canonique d'affichage (du premier état au terminal).
export const LIFECYCLE_ORDER = ['new', 'triaged', 'planned', 'in_progress', 'closed'];

// Mapping lifecycle → prop `status` du composant Badge.
// Statuts réels supportés par Badge : ok / warn / crit / info / neutral
// (audit Phase 1.3 — src/ui/Badge.jsx).
export const LIFECYCLE_BADGE_VARIANTS = {
  new: 'neutral',
  triaged: 'info',
  planned: 'info',
  in_progress: 'warn',
  closed: 'ok',
};

// Page size fixe MV3 (pas de sélecteur).
export const PAGE_SIZE = 20;

// Copy FR.
export const COPY = {
  pageTitle: "Centre d'action",
  pageSubtitle: 'Nouveau (V4) — Pilote',
  filterByState: 'État',
  filterAllStates: 'Tous les états',
  // Filtre lifecycle client-side : il ne porte que sur la page courante
  // (le backend M2-4.2 GET /items n'accepte pas de paramètre ?state=).
  filterScopeNote: 'Filtre appliqué à la page courante',
  columnTitle: 'Titre',
  columnState: 'État',
  columnDomain: 'Domaine',
  columnUpdated: 'Mis à jour',
  emptyTitle: 'Aucune action à afficher',
  emptyText: 'Les actions de votre organisation apparaîtront ici dès leur création.',
  emptyFilteredTitle: 'Aucune action pour ce filtre sur cette page',
  emptyFilteredText: 'Essayez une autre page ou choisissez « Tous les états ».',
  errorTitle: 'Impossible de charger les actions',
};
