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

// ── M2-5.3.A — Drawer détail item ──────────────────────────────

export const TAB_IDS = {
  timeline: 'timeline',
  evidences: 'evidences',
  blockers: 'blockers',
  links: 'links',
};

export const TAB_LABELS = {
  [TAB_IDS.timeline]: 'Historique',
  [TAB_IDS.evidences]: 'Preuves',
  [TAB_IDS.blockers]: 'Blocages',
  [TAB_IDS.links]: 'Liens',
};

// Mapping event_type backend → label FR. Clés alignées sur les valeurs
// réellement émises par routes/v4/action_center.py (audit Phase 1).
export const EVENT_TYPE_LABELS = {
  state_changed: "Transition d'état",
  evidence_added: 'Preuve ajoutée',
  evidence_verified: 'Preuve vérifiée',
  blocker_added: 'Blocage signalé',
  blocker_removed: 'Blocage levé',
};

// Copy spécifique au drawer détail.
export const DRAWER_COPY = {
  drawerTitle: "Détail de l'action",
  domainLabel: 'Domaine',
  kindLabel: 'Type',
  createdAtLabel: 'Créée',
  updatedAtLabel: 'Mise à jour',
  headerError: "Impossible de charger l'action.",
  timelineEmptyTitle: 'Aucun événement',
  timelineEmptyText: "L'historique sera alimenté au fil des actions.",
  timelineErrorTitle: "Impossible de charger l'historique",
  tabPlaceholderTitle: 'Disponible prochainement',
  tabPlaceholderText: 'Cet onglet sera activé au sprint suivant.',
};

// ── M2-5.3.B — Onglets Preuves / Blocages / Liens ──────────────

// Evidence : status dérivé de verified_at + expires_at (pas d'enum
// verification_status backend — doctrine ADR-029).
export const EVIDENCE_STATUS_LABELS = {
  pending: 'En attente',
  verified: 'Vérifiée',
  expired: 'Expirée',
};

export const EVIDENCE_STATUS_BADGE_VARIANTS = {
  pending: 'warn',
  verified: 'ok',
  expired: 'crit',
};

// Blocker : status dérivé de resolved_at.
export const BLOCKER_STATUS_LABELS = {
  active: 'Actif',
  resolved: 'Résolu',
};

export const BLOCKER_STATUS_BADGE_VARIANTS = {
  active: 'warn',
  resolved: 'ok',
};

// blocker_type → label FR. Clés = enum BlockerType réel (7 valeurs `waiting_*`,
// audit Phase 1.2) ; labels canoniques doctrine v0.3 §7.1.
export const BLOCKER_TYPE_LABELS = {
  waiting_evidence: 'Preuve attendue',
  waiting_budget: 'Budget attendu',
  waiting_third_party: 'Tiers attendu',
  waiting_data: 'Donnée attendue',
  waiting_supplier: 'Fournisseur attendu',
  waiting_manager_validation: 'Validation manager attendue',
  waiting_regulatory_confirmation: 'Confirmation réglementaire attendue',
};

// target_module → label FR (7 valeurs TargetModule, doctrine M2-4.4).
export const TARGET_MODULE_LABELS = {
  action_center_item: 'Action',
  site: 'Site',
  building: 'Bâtiment',
  meter: 'Compteur',
  invoice: 'Facture',
  contract: 'Contrat',
  regulatory_obligation: 'Obligation réglementaire',
};

// Seul action_center_item est traité côté UI ; les 6 autres = disabled + tooltip.
export const TARGET_MODULE_UI_AVAILABLE = ['action_center_item'];

export const TARGET_MODULE_DISABLED_TOOLTIP = 'Module pas encore intégré côté UI';

// Copy des onglets M2-5.3.B.
export const TAB_COPY = {
  evidencesEmptyTitle: 'Aucune preuve',
  evidencesEmptyText: "Les preuves d'exécution seront listées ici dès leur ajout.",
  evidencesErrorTitle: 'Impossible de charger les preuves',

  blockersEmptyTitle: 'Aucun blocage',
  blockersEmptyText: 'Les blocages signalés apparaîtront ici.',
  blockersErrorTitle: 'Impossible de charger les blocages',

  linksEmptyTitle: 'Aucun lien',
  linksEmptyText: "Les liens vers d'autres éléments apparaîtront ici.",
  linksErrorTitle: 'Impossible de charger les liens',

  expiresAtLabel: 'Expire le',
  verifiedAtLabel: 'Vérifiée le',
  resolvedAtLabel: 'Résolu le',
  reportedAtLabel: 'Signalé le',
  uploadedAtLabel: 'Ajoutée le',
};

// ── M2-5.4 — Modal transition lifecycle ────────────────────────

// 3 closure_reasons user-facing (cf. lifecycleTransitions.USER_FACING_CLOSURE_REASONS).
export const CLOSURE_REASON_LABELS = {
  resolved: 'Résolu',
  dismissed: 'Rejeté',
  not_applicable: 'Non applicable',
};

export const TRANSITION_COPY = {
  buttonTransition: 'Transitionner',
  buttonTerminal: 'État terminal — aucune transition possible',
  modalTitle: "Transitionner l'action",
  fieldNewState: 'Nouvel état',
  fieldClosureReason: 'Raison de clôture',
  fieldComment: 'Commentaire (optionnel)',
  selectPlaceholder: 'Sélectionner un état…',
  closurePlaceholder: 'Sélectionner une raison…',
  submitButton: 'Transitionner',
  submitLoading: 'Transition en cours…',
  cancelButton: 'Annuler',
  successToast: 'Transition effectuée',
  noTransitionsAvailable: 'Aucune transition possible depuis cet état.',
};
