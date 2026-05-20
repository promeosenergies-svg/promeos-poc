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
  columnPriority: 'Priorité',
  columnState: 'État',
  columnType: 'Type',
  columnDomain: 'Domaine',
  columnUpdated: 'Mis à jour',
  emptyTitle: 'Aucune action à afficher',
  emptyText: 'Les actions de votre organisation apparaîtront ici dès leur création.',
  // M2-5.10.A.bis — copy reformulée : sans cette précision, un audit CS a
  // démontré que l'utilisateur conclut « il n'y a aucune action » alors que
  // d'autres pages contiennent des items du filtre.
  emptyFilteredTitle: 'Aucun résultat sur cette page',
  emptyFilteredText:
    "D'autres actions correspondant à ce filtre peuvent exister sur les pages suivantes. " +
    'Navigue vers la page suivante ou clique « Réinitialiser » pour étendre la vue.',
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
  created: 'Créé',
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

// ── M2-5.5 — Upload + verify evidence ──────────────────────────

export const UPLOAD_COPY = {
  buttonAddEvidence: 'Ajouter une preuve',
  modalTitle: 'Ajouter une preuve',
  fieldFile: 'Fichier',
  fieldFileHint: 'PDF, JPG ou PNG · 10 Mo maximum',
  fieldDescription: 'Description (optionnel)',
  submitButton: 'Ajouter la preuve',
  submitLoading: 'Upload en cours…',
  cancelButton: 'Annuler',
  successToast: 'Preuve ajoutée',
};

export const VERIFY_COPY = {
  buttonVerify: 'Vérifier',
  dialogTitle: 'Vérifier cette preuve',
  dialogMessage: "Confirmer la vérification de cette preuve ? L'expiration sera fixée à 90 jours.",
  confirmButton: 'Vérifier',
  confirmLoading: 'Vérification…',
  cancelButton: 'Annuler',
  successToast: 'Preuve vérifiée',
};

// ── M2-5.6 — Ajout + résolution de blocage ─────────────────────

export const BLOCKER_ADD_COPY = {
  buttonAddBlocker: 'Ajouter un blocage',
  modalTitle: 'Signaler un blocage',
  fieldType: 'Type de blocage',
  fieldTypePlaceholder: 'Sélectionner un type…',
  fieldJustification: 'Justification',
  fieldJustificationHint: 'Motif du blocage — 3 caractères minimum.',
  submitButton: 'Signaler',
  submitLoading: 'Signalement…',
  cancelButton: 'Annuler',
  successToast: 'Blocage signalé',
};

export const BLOCKER_RESOLVE_COPY = {
  buttonResolve: 'Résoudre',
  modalTitle: 'Résoudre ce blocage',
  fieldNote: 'Note de résolution (optionnel)',
  fieldNoteHint: "Pour l'audit trail. Facultatif.",
  submitButton: 'Résoudre',
  submitLoading: 'Résolution…',
  cancelButton: 'Annuler',
  successToast: 'Blocage résolu',
};

// ── M2-5.8.B — Priorité + libellés kind FR + accessibilité ─────

// priority_bracket → label FR (4 brackets PriorityBracket, doctrine V4).
export const PRIORITY_LABELS = {
  P0: 'Critique',
  P1: 'Élevée',
  P2: 'Standard',
  P3: 'Faible',
};

// priority_bracket → status Badge (palette severity src/ui/Badge.jsx).
export const PRIORITY_BADGE_VARIANTS = {
  P0: 'crit', // rouge — à traiter aujourd'hui
  P1: 'warn', // orange — cette semaine
  P2: 'info', // bleu — ce mois
  P3: 'neutral', // gris — backlog
};

// Ordre canonique, du plus prioritaire au moins.
export const PRIORITY_ORDER = ['P0', 'P1', 'P2', 'P3'];

// kind backend → label FR (7 valeurs Kind, cf. enums/kind.py).
export const KIND_LABELS = {
  anomaly: 'Anomalie',
  action: 'Action',
  decision: 'Décision',
  signal: 'Signal',
  evidence_request: 'Demande de preuve',
  deadline: 'Échéance',
  recommendation: 'Recommandation',
};

// domain backend → label FR (7 valeurs Domain, cf. enums/domain.py).
export const DOMAIN_LABELS = {
  conformite: 'Conformité',
  facturation: 'Facturation',
  maintenance: 'Maintenance',
  optimisation: 'Optimisation énergétique',
  purchase: "Achat d'énergie",
  flexibilite: 'Flexibilité',
  data_quality: 'Qualité des données',
};

// Copy accessibilité (P0-4 a11y clavier · M2-5.9.bis libellés inconnus).
export const A11Y_COPY = {
  rowAriaLabel: (title) => `Ouvrir l'action : ${title}`,
  unknownKindLabel: 'Type inconnu',
  unknownDomainLabel: 'Domaine inconnu',
};

// ── M2-5.10.B — Sol drawer copy + métadonnées ────────────────────
//
// Restyle pixel-perfect du drawer détail (maquette `centre_action_v4_detail_
// drawer_v02.html` §7.3 + §8.4). Périmètre : éléments backend déjà exposés.
// Hors scope (BACKLOG_M3) : priority explain R1-R6, impact 4 quadrants,
// compliance card, scenarios, next action narrative, SLA, owner, audit mode,
// breadcrumb dynamique.

// 3 boutons header maquette lignes 689-732. Plus ▾ déploie un menu vers les
// modals existants (Bloquer / Ajouter preuve / Clôturer).
export const DRAWER_ACTIONS_COPY = {
  primaryLabel: 'Transitionner',
  primaryHint: 'Action principale',
  secondaryLabel: 'Réassigner',
  // Réassigner = dette M3+ (endpoint PATCH /items/{id}/assign manquant).
  secondaryDisabledHint: 'Disponible M3 — endpoint owner manquant',
  moreLabel: 'Plus',
  moreAriaLabel: "Plus d'actions",
  menuItemBlock: 'Signaler un blocage',
  menuItemEvidence: 'Ajouter une preuve',
  menuItemClose: 'Clôturer',
  menuItemHistory: 'Historique complet',
  // Élément disabled toujours visible (cardinal doctrine — pas de silence).
  menuItemMerge: 'Fusionner',
  menuItemMergeReason: 'aucun doublon',
};

// Layout audit-list maquette §8.4 lignes 614-637. Mapping acteur backend → UI :
// `actor_role` peut valoir `system` (auto), `user` (humain), `null` (legacy).
export const TIMELINE_ACTOR_COPY = {
  systemLabel: 'PROMEOS',
  fallbackActor: 'Système',
};

// Maquette §8.4 lignes 992-1011 — link-row 3 colonnes (label / value / action).
// Le `target_id` UUID est masqué côté UI (cohérent doctrine §13.5 anti-bruit).
export const LINKS_COPY = {
  linkActionOpen: 'Ouvrir ↗',
  noneFallback: 'aucun · créé par triage',
};

// Maquette §8.4 lignes 472-478 — blockers depuis « X jours ». Le compteur est
// dérivé client-side de `added_at`. Singulier/pluriel + escalade > 7j.
export const BLOCKERS_SINCE_COPY = {
  prefix: 'depuis le',
  sinceDaysSingular: (n) => `${n} jour`,
  sinceDaysPlural: (n) => `${n} jours`,
  escalationWarning: 'escalade automatique au manager si > 7 jours',
};

// Footer drawer maquette ligne 1124-1133.
export const DRAWER_FOOTER_COPY = {
  createdPrefix: 'Créé',
  updatedPrefix: 'Mise à jour',
  activityLabel: 'Activité',
};

// Placeholders « Disponible M3 » — affichés à la place des sections backend
// manquantes pour expliciter la dette doctrinale sans masquer la vision.
export const SECTION_M3_COPY = {
  priorityExplainLabel: 'Pourquoi cette priorité',
  impactLabel: 'Impact financier',
  complianceLabel: 'Lien réglementaire',
  scenariosLabel: 'Scénarios disponibles',
  m3HintShort: 'Disponible M3+',
  m3HintLong:
    'Endpoint backend en cours de spécification (cf. BACKLOG_M3). ' +
    "La section apparaîtra ici dès qu'il sera exposé.",
};

// ── M2-5.10.A — Fidélité doctrine Sol v0.2 (maquette referentiel) ──
//
// Restyle pixel-perfect des éléments déjà supportés backend. Hors-scope
// (owner/deadline/impact/bulk/search/sort serveur, narrative bar, view-switch
// Kanban) → dette tracée dans BACKLOG_M3.md.

// Masthead italique + sous-titre + date « MAJ live » au-dessus des filtres.
//
// M2-5.10.A.bis — `subtitle` ne contient plus que le label statique ; le
// nombre d'items « N items » est injecté dynamiquement par `Masthead.jsx`
// depuis `total` du hook V4 (fidélité maquette §8.3 ligne 705).
export const MASTHEAD_COPY = {
  // Titre court (le sous-titre détaille). « Référentiel » = onglet maquette
  // §8.3 actif (Pilotage est M2-5.10.D).
  title: "Centre d'action",
  subtitle: 'Référentiel complet',
  dateLive: 'MAJ live',
  itemsSuffix: (n) => (n === 1 ? '1 item' : `${n} items`),
};

// Label MONO uppercase utilisé dans la cellule Classement (chip + table).
// Dérivation explicite : on garde `KIND_LABELS` (FR mixed-case) pour la
// lecture et on UPPER-case à l'affichage. « Reco » dans la maquette est une
// abréviation tolérée pour `recommendation`.
export const KIND_LABELS_UPPER = {
  anomaly: 'ANOMALIE',
  action: 'ACTION',
  decision: 'DÉCISION',
  signal: 'SIGNAL',
  evidence_request: 'PREUVE',
  deadline: 'ÉCHÉANCE',
  recommendation: 'RECO',
};

// 7 variantes Sol pour la cellule Classement (kind-icon + kind-label).
// Source : maquette §8.3 lignes 435-454 (palette « journal en terrasse »).
// `borderStyle` : 'dashed' pour signal, 'dotted' pour recommendation
// (signature visuelle distinctive de chaque kind, cf. README maquettes).
export const KIND_SOL_VARIANTS = {
  anomaly: {
    bg: 'var(--sol-refuse-bg)',
    border: 'var(--sol-refuse-line)',
    color: 'var(--sol-refuse-fg)',
    borderStyle: 'solid',
  },
  action: {
    bg: 'var(--sol-bg-paper)',
    border: 'var(--sol-ink-300)',
    color: 'var(--sol-ink-700)',
    borderStyle: 'solid',
  },
  decision: {
    bg: 'var(--sol-hch-bg)',
    border: 'var(--sol-hch-fg)',
    color: 'var(--sol-hch-fg)',
    borderStyle: 'solid',
  },
  signal: {
    bg: 'var(--sol-bg-panel)',
    border: 'var(--sol-ink-300)',
    color: 'var(--sol-ink-500)',
    borderStyle: 'dashed',
  },
  evidence_request: {
    bg: 'var(--sol-attention-bg)',
    border: 'var(--sol-attention-line)',
    color: 'var(--sol-attention-fg)',
    borderStyle: 'solid',
  },
  deadline: {
    bg: 'var(--sol-afaire-bg)',
    border: 'var(--sol-afaire-line)',
    color: 'var(--sol-afaire-fg)',
    borderStyle: 'solid',
  },
  recommendation: {
    bg: 'var(--sol-calme-bg)',
    border: 'var(--sol-calme-fg)',
    color: 'var(--sol-calme-fg)',
    borderStyle: 'dotted',
  },
};

// Lifecycle pill Sol (maquette §8.3 lignes 501-505) — couleurs émotionnelles.
// `closed` (succès) ≠ `in_progress` (attention) ≠ `triaged` (hch). Le dot
// pulse uniquement sur in_progress (pas implémenté ici — cosmétique pure).
export const LIFECYCLE_SOL_VARIANTS = {
  new: {
    bg: 'var(--sol-bg-paper)',
    border: 'var(--sol-ink-700)',
    color: 'var(--sol-ink-700)',
  },
  triaged: {
    bg: 'var(--sol-hch-bg)',
    border: 'var(--sol-hch-fg)',
    color: 'var(--sol-hch-fg)',
  },
  planned: {
    bg: 'var(--sol-calme-bg)',
    border: 'var(--sol-calme-fg)',
    color: 'var(--sol-calme-fg)',
  },
  in_progress: {
    bg: 'var(--sol-attention-bg)',
    border: 'var(--sol-attention-fg)',
    color: 'var(--sol-attention-fg)',
  },
  closed: {
    bg: 'var(--sol-succes-bg)',
    border: 'var(--sol-succes-fg)',
    color: 'var(--sol-succes-fg)',
  },
};

// 7 domaines BE → variantes Sol. La maquette ne couvre que 6 chip-style
// (« conformite/facturation/achat/consommation/patrimoine/data ») ; on
// dérive les 7 vraies clés BE (Domain enum) en mappant sur les tons les plus
// proches sémantiquement. Doctrine §5 : MONO uppercase, fond clair.
export const DOMAIN_SOL_VARIANTS = {
  conformite: { bg: 'var(--sol-calme-bg)', color: 'var(--sol-calme-fg)' },
  facturation: { bg: 'var(--sol-attention-bg)', color: 'var(--sol-attention-fg)' },
  maintenance: { bg: 'var(--sol-afaire-bg)', color: 'var(--sol-afaire-fg)' },
  optimisation: { bg: 'var(--sol-succes-bg)', color: 'var(--sol-succes-fg)' },
  purchase: { bg: 'var(--sol-hch-bg)', color: 'var(--sol-hch-fg)' },
  flexibilite: { bg: 'var(--sol-ink-100)', color: 'var(--sol-ink-700)' },
  data_quality: { bg: 'var(--sol-bg-panel)', color: 'var(--sol-ink-500)' },
};

// Priorité Sol — tag plein (texte clair sur fond coloré) + strip vertical
// 3px à gauche de chaque ligne (maquette §8.3 lignes 388-391 et 533-536).
// Même palette : la strip et le tag partagent la couleur, signature de la
// modulation R1-R6 (cf. doctrine §5.2).
export const PRIORITY_SOL_BG = {
  P0: 'var(--sol-refuse-fg)',
  P1: 'var(--sol-attention-fg)',
  P2: 'var(--sol-calme-fg)',
  P3: 'var(--sol-ink-400)',
};

// Copy spécifique au restyle Sol — filtres Row 1 (Classement) + Row 2.
export const SOL_COPY = {
  filterLabelClassement: 'Classement',
  filterLabelPriorisation: 'Priorisation',
  filterAllKinds: 'Tous les types',
  filterReset: 'Réinitialiser',
  // ARIA — chip clickable kind ouvre/ferme le filtre.
  kindChipAria: (label) => `Filtrer par ${label}`,
  resetAria: 'Réinitialiser les filtres',
};
