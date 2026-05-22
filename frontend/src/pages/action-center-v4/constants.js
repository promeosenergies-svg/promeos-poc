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
  // M2-5.11.H : reformulé pour lever l'ambiguïté CS (« page courante »
  // pouvait laisser croire à un filtre org-wide). Audit polish +0.15.
  filterScopeNote:
    "Ces filtres portent uniquement sur les 20 items de cette page — d'autres pages peuvent contenir des résultats.",
  columnTitle: 'Titre',
  columnPriority: 'Priorité',
  columnState: 'État',
  columnType: 'Type',
  columnDomain: 'Domaine',
  columnUpdated: 'Mis à jour',
  // M2-6.B.frontend — colonne € « Impact estimé » (Q16=B audit Amine).
  // Remplace l'ancien « À risque 12m » (impact_payload.at_risk.value_eur) par
  // l'agrégat CFO simple `estimated_impact_euros` (champ scalaire seedé
  // M2-6.B.backend). Sémantique CFO MV3 : montant indicatif unique vs
  // drill-down 4 quadrants (reporté drawer ImpactSection M3+).
  // PAS de suffixe « €/an » tant que `impact_period`/`impact_basis` absent
  // de l'API (M3-IMPACT-PERIOD-BASIS tracé backlog).
  columnAmount: 'Impact estimé',
  amountTooltip: 'Montant indicatif issu du backend, hors éléments non estimés.',
  amountTooltipMissing:
    "Impact non encore estimé pour cet item — apparaîtra dès qu'une source documentée sera disponible.",
  // M2-5.11.E — colonne Pilote. Compact ; le tooltip qualifie l'absence.
  columnOwner: 'Pilote',
  ownerUnassignedLabel: 'Non assigné',
  ownerUnassignedTooltip:
    "Aucun pilote assigné — cliquer sur l'item pour ouvrir le drawer et assigner.",
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
//
// M2-5.10.B.bis — `primaryLabel` n'est plus statique : doctrine v0.3 §7.3
// prescrit un verbe dynamique selon `lifecycle_state` (audit UX Marie P0-1 +
// CS P0-1 — « Transitionner » est du jargon IT). Voir
// `LIFECYCLE_PRIMARY_ACTION_LABEL` ci-dessous. `menuItemHistory` supprimé
// (constante morte, audit code-reviewer P1-4).
export const DRAWER_ACTIONS_COPY = {
  primaryHint: 'Action principale',
  // M2-5.11.E — label dynamique : « Assigner » si aucun pilote, « Réassigner »
  // si déjà un pilote. Le tooltip dynamique nomme le pilote actuel.
  secondaryLabel: 'Assigner',
  secondaryReassignLabel: 'Réassigner',
  secondaryTooltipUnassigned: 'Assigner un pilote à cet item',
  secondaryTooltipAssigned: (name) => `Pilote actuel : ${name}. Cliquer pour réassigner.`,
  moreLabel: 'Plus',
  moreAriaLabel: "Plus d'actions",
  menuItemBlock: 'Signaler un blocage',
  menuItemEvidence: 'Ajouter une preuve',
  menuItemClose: 'Clôturer',
  // Élément disabled toujours visible (cardinal doctrine — pas de silence).
  menuItemMerge: 'Fusionner',
  menuItemMergeReason: 'aucun doublon',
};

// M2-5.11.E — copy de la modal AssignOwner (drawer secondary button).
export const ASSIGN_OWNER_COPY = {
  modalTitle: 'Assigner un pilote',
  fieldDisplayName: 'Pilote',
  fieldDisplayNameHint: 'Nom court — apparaîtra dans la colonne et la carte.',
  fieldOwnerId: 'Identifiant pilote (UUID)',
  fieldOwnerIdHint: 'Identifiant utilisateur, copié depuis la liste des comptes.',
  unassignButton: 'Désassigner',
  unassignConfirmHint: "L'item ne sera plus rattaché à un pilote nommé.",
  submitButton: 'Assigner',
  submitLoading: 'Assignation en cours…',
  submitReassignButton: 'Réassigner',
  cancelButton: 'Annuler',
  successAssignedToast: 'Pilote assigné',
  successUnassignedToast: 'Pilote retiré',
  errorTitle: "Impossible d'assigner le pilote",
  validationDisplayNameRequired: 'Le nom du pilote est requis quand un identifiant est saisi.',
  validationOwnerIdInvalid:
    'Identifiant invalide — UUID attendu (ex. 12345678-1234-1234-1234-123456789012).',
};

// Validation UUID v4-ish (laxe : on accepte tous les UUID syntaxiquement
// valides, pas seulement v4 — la doctrine V4 utilise uuid4 par défaut mais
// rien n'empêche un opérateur de coller un v1/v5). Le BE valide stricte
// Pydantic UUID.
export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Verbes dynamiques par lifecycle_state (doctrine v0.3 §7.3) — portés par
// `DrawerActions` sur le bouton primary. `closed` désactive le bouton (la
// réouverture est réservée aux admins, dette M3+).
export const LIFECYCLE_PRIMARY_ACTION_LABEL = {
  new: 'Qualifier',
  triaged: 'Planifier',
  planned: 'Démarrer',
  in_progress: 'Marquer comme fait',
  closed: 'Rouvrir',
};

// Bandeau persistant en tête du body drawer quand l'item est terminal (audit
// UX Marie P0-3 + CS P0-2 — item closed silencieux = appel support).
export const CLOSED_BANNER_COPY = {
  title: 'Action clôturée',
  textPrefix: 'Clôturée le',
  textSuffix: '· lecture seule. Pour rouvrir, contactez votre administrateur.',
  iconAriaLabel: 'Action clôturée',
};

// Breadcrumb header drawer (maquette ligne 679-687) — statique MV3 (file
// prioritaire = M2-5.10.D, pas encore livrée).
export const BREADCRUMB_DRAWER_COPY = {
  app: 'PROMEOS',
  section: "Centre d'action",
  page: 'Référentiel',
  current: 'Détail',
};

// CTA inline dans les empty states des onglets (audit CS P1-3 — actions
// d'ajout enfouies dans Plus ▾). Pour l'utilisateur lambda, mieux vaut un
// bouton contextuel visible que de devoir chercher le menu Plus.
export const EMPTY_STATE_CTA_COPY = {
  addEvidence: 'Ajouter la première preuve',
  addBlocker: 'Signaler le premier blocage',
};

// ── M2-5.10.C — Impact financier 4 quadrants (doctrine §8.5) ──────
//
// Section intégrée dans le drawer détail item, sous ItemHeader, au-dessus
// des onglets. 4 cards Sol côte à côte (Estimé / À risque / Sécurisable /
// Réalisé) avec valeur €, qualifier, source, formule.
//
// Cardinal doctrine v0.3 §8.5 : un chiffre € sans source/formule est un
// chiffre menteur. Quand `value_eur === null`, la card affiche « — » (pas
// « 0 € »).

export const IMPACT_COPY = {
  sectionTitle: 'Impact financier · 12 mois',
  sectionPeriodBadge: '€ HT · 12 mois',
  emptyTitle: 'Impact non encore calculé pour cet item',
  emptyText:
    "L'évaluation économique est en cours de spécification (BACKLOG_M3). " +
    "Les 4 dimensions apparaîtront ici dès qu'elles seront exposées.",
  errorTitle: "Impossible de charger l'impact financier",
  noValueDash: '—',
};

// Mapping dimension → libellé FR + couleur Sol + tooltip définition.
// Source maquette `centre_action_v4_detail_drawer_v02.html` lignes 428-454
// et `centre_action_v4_impact_drawer.html` lignes 240-292.
export const IMPACT_DIMENSIONS = {
  estimated: {
    label: 'Estimé',
    accentColor: 'var(--sol-attention-fg)',
    tooltip:
      "Gain attendu si l'action est exécutée selon le scénario recommandé. " +
      'Source backend (modèle V4 ou formule explicite).',
  },
  at_risk: {
    label: 'À risque',
    accentColor: 'var(--sol-refuse-fg)',
    tooltip:
      'Montant non sécurisé par une action démarrée ou une preuve validée. ' +
      "Pénalité réglementaire ou perte potentielle si l'item n'est pas traité.",
  },
  secured: {
    label: 'Sécurisable',
    accentColor: 'var(--sol-calme-fg)',
    tooltip:
      'Activable immédiatement : action ready-to-start, preuves disponibles. ' +
      "Aucun montant sécurisé tant que le scénario n'est pas démarré.",
  },
  realized: {
    label: 'Réalisé',
    accentColor: 'var(--sol-succes-fg)',
    tooltip:
      "Gain constaté après clôture de l'action avec preuves vérifiées. " +
      "Aucun montant tant que l'action n'est pas clôturée.",
  },
};

// Ordre de rendu (maquette §8.5) : risque + estimé prioritaires (haut),
// sécurisable + réalisé en bas (état futur ou passé).
export const IMPACT_DIMENSION_ORDER = ['estimated', 'at_risk', 'secured', 'realized'];

// ── M2-5.10.D — Pilotage / File prioritaire (doctrine §8.1) ───────
//
// Page `/action-center-v4/pilotage` — vue Resp. Énergie « ce matin » :
// la file prioritaire (5 items P0/P1 triés priority_score DESC) avec
// renvoi vers le drawer détail au clic.
//
// MV3 livré : 1 section « File prioritaire » + 1 onglet (Décisions). Hors
// scope BACKLOG_M3 : narrative bar agrégée, escalation banner, quick
// filters serveur, sections Jalons / À surveiller / Clôturé récemment,
// view toggle Journal (= M2-5.10.E), SLA dates BE, vues Audit/Dense.

export const PILOTAGE_COPY = {
  pageTitle: 'Pilotage',
  pageSubtitle: 'File prioritaire — décisions du jour',
  // Masthead Sol (cohérent référentiel §8.3).
  mastheadTitle: "Centre d'action",
  mastheadSubtitle: 'Pilotage',
  // Section file prioritaire.
  fileSectionTitle: 'File prioritaire',
  fileSectionSub: "Risques, décisions et actions nécessitant une intervention humaine aujourd'hui.",
  fileLinkToReferentiel: 'Voir tout le référentiel ↗',
  // Empty state — pas de P0/P1 actif aujourd'hui.
  emptyTitle: "Aucune action prioritaire aujourd'hui",
  emptyText:
    'Aucun item P0/P1 actif sur le périmètre courant. Bonne nouvelle ! ' +
    'Consultez le référentiel pour les autres actions en cours.',
  errorTitle: 'Impossible de charger la file prioritaire',
  // Tabs internes Pilotage / Référentiel.
  tabPilotage: 'Pilotage',
  tabReferentiel: 'Référentiel',
  // M2-5.12 — bloc éditorial narratif (maquette Sophie Marin 2026-05-22).
  // Eyebrow status pill : dot vert + libellé MONO uppercase identifiant le
  // périmètre tour de contrôle. Posé au-dessus de la phrase narrative.
  eyebrowDot: '●',
  eyebrowLabel: 'TOUR DE CONTRÔLE ÉNERGÉTIQUE',
  eyebrowSeparator: '·',
  // Phrase éditoriale dynamique (Fraunces italique ~28px). Sources :
  // count_p0 + count_p1 pour "N décisions", count_at_risk pour "N blocages",
  // qualité données pour le tag final. Sans calcul métier — composition.
  editorialDecisionsSuffix: 'décisions à traiter',
  // M2-5.12 polish — singulier pour count ≤ 1 (français Académie : 0 et 1 prennent
  // le singulier). Convention alignée Masthead `sitesCount > 1 ? 'SITES' : 'SITE'`.
  editorialDecisionSuffixSingular: 'décision à traiter',
  editorialDecisionsTodaySuffix: " aujourd'hui",
  editorialBlockersSuffix: 'blocages',
  editorialBlockerSuffixSingular: 'blocage',
  editorialNoBlockers: 'aucun blocage en cours',
  editorialDataQualityOK: 'qualité données OK',
  editorialDataQualityDegraded: 'qualité données dégradée',
  // M2-6.B.frontend.bis — Indicateur complétude CFO Q19=C closeur. Format
  // « X actions sur Y portent un impact estimé : Z k€ » composé inline dans
  // EditorialNarrativeBlock.jsx avec singulier/pluriel grammatical FR
  // (Académie française : 0 et 1 → singulier ; ≥2 → pluriel). Les anciennes
  // constantes `editorialCompletudePrefix`/`Suffix` (M2-6.B.frontend) sont
  // retirées — incompatibles avec la phrase structurée.
  // 3 CTAs header — visibles en MV3 mais comportements M2-6+ (wizard de
  // triage par lot · drawer impact agrégé · export PDF). Tooltip explique
  // l'arrivée pour ne pas frustrer le user en attendant.
  ctaTriage: 'Lancer le triage',
  ctaTriageDisabledHint: 'Wizard bulk-action disponible en M2-6 (sprint dédié)',
  ctaImpact: "Voir l'impact",
  ctaImpactDisabledHint: 'Drawer impact agrégé disponible en M2-6 (somme € BE)',
  ctaExport: 'Exporter COMEX',
  // M2-6.B.pdf — ce hint reste utile si l'export devient indisponible (perm,
  // erreur backend) — affiché si `onExportComex` n'est pas fourni au composant.
  ctaExportDisabledHint: 'Export PDF/CSV disponible en M2-6 (service BE)',
  // M2-6.B.pdf — libellé pendant génération ReportLab (2-5s).
  ctaExportLoading: 'Génération…',
};

// M2-5.12 — Mapping role legacy → libellé FR persona (cohérent
// AppShell.jsx:51-62 + AdminUsersPage:9-21 + AdminAssignmentsPage:24-37).
// Dupliqué localement plutôt qu'importé pour éviter une dépendance cyclique
// vers layout/. Source de vérité : AppShell.jsx (audit code-reviewer M3+
// extraction utils/roleLabels.js si > 3 duplications).
export const ROLE_LABELS_V4 = {
  dg_owner: 'DG / Propriétaire',
  dsi_admin: 'DSI / Admin',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Resp. Énergie',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  prestataire: 'Prestataire',
  auditeur: 'Auditeur',
  pmo_acc: 'PMO / Acc.',
};

// ── M2-5.11.C — NarrativeBar Sol (5 compteurs CFO) ────────────────
//
// Bandeau horizontal posé sous le Masthead sur Référentiel + Pilotage,
// rendant lisible l'état du portefeuille en une coup d'œil (audit CFO
// 3.5/10 → cible 5.5/10). Chaque tuile combine une valeur (chiffre
// MONO) + un libellé court + une palette Sol émotionnelle.
//
// 5 dimensions canoniques cf. `ActionCenterSummaryResponse` (backend) :
// P0 / P1 / Sans owner / À risque / Sécurisé. Les couleurs réutilisent
// la palette dérive/attention/ink-500/refuse/succès (cohérence pillarsLifecycleBadge
// et KIND_SOL_VARIANTS).

export const NARRATIVE_BAR_COPY = {
  // M2-5.12 — Labels affichés sous chaque chiffre (FR, ≤ 18 char chacun
  // pour rester tenable en 5 colonnes desktop avec breakpoints lg+).
  // Tuile 1 combine P0+P1 en "Décisions P0/P1" (maquette Sophie Marin
  // 2026-05-22) — plus parlant CFO/Resp.Énergie que 2 tuiles séparées.
  decisionsLabel: 'Décisions P0/P1',
  // M2-5.12 : « Sans responsable » plutôt que « Sans pilote » (maquette).
  // Reflète mieux le langage organisationnel (rôle hiérarchique vs métaphore
  // aviation). Doctrine §5 grammaire éditoriale Sol — proche du terrain.
  withoutOwnerLabel: 'Sans responsable',
  // M2-5.11.G : libellé « Bloqués » pour lever l'ambiguïté avec
  // `ImpactSection.at_risk` (qui mesure un montant € à perdre — différent
  // d'un item bloqué par une dépendance non résolue).
  atRiskLabel: 'Bloqués',
  // M2-5.11.G : « Preuvés » plutôt que « Sécurisés ».
  securedLabel: 'Preuvés',
  // M2-5.12 : 5e tuile SLA en retard (maquette). MV3 placeholder désactivé
  // — exige que le seed populate `sla_due_date` + endpoint /summary étende
  // `count_sla_overdue`. Affichée avec badge "Bientôt" pour matcher visuel.
  slaOverdueLabel: 'SLA en retard',
  slaOverduePlaceholder: '—',
  // Tooltips contextuels (title=) — explicitent la définition exacte du
  // compteur, accessibles à la souris et aux lecteurs d'écran.
  decisionsTooltip: "Items P0 + P1 actifs (lifecycle ≠ clos) — décisions à arbitrer aujourd'hui.",
  withoutOwnerTooltip:
    'Items actifs sans responsable assigné. Cliquer sur un item dans le tableau pour assigner via le drawer.',
  atRiskTooltip:
    "Items actifs avec ≥ 1 blocage non résolu — une dépendance externe (preuve, budget, tiers) attend résolution. Distinct du montant « à risque » de l'impact financier.",
  securedTooltip:
    "Items actifs avec ≥ 1 preuve vérifiée — auditable à date. Ne confond pas avec « Sécurisable » de l'impact financier (qui mesure le potentiel activable).",
  slaOverdueTooltip:
    'Items actifs avec date limite SLA dépassée. Disponible M2-6 (champ sla_due_date à populer + endpoint /summary étendu).',
  // M2-6.B.frontend — Tooltip sur sum € (sous-ligne tuile Décisions P0/P1).
  // Cohérent ItemsTable colonne « Impact estimé » (même libellé Q16).
  sumImpactTooltip: 'Montant indicatif issu du backend, hors éléments non estimés.',
  // États non-data (loading / error / no-data).
  loadingLabel: 'Synthèse en cours…',
  errorTitle: 'Impossible de charger la synthèse',
  errorRetry: 'Réessayer',
};

// Palette Sol des 5 tuiles — `bg` mate, `accent` pour le chiffre.
// Sans pilote reste neutre ink-500 : ce n'est pas une dérive émotionnelle,
// juste une dette opérationnelle.
export const NARRATIVE_BAR_VARIANTS = {
  // M2-5.12 — `decisions` combine P0+P1 (refuse-bg conservé : c'est le
  // niveau d'urgence dominant). P0 + P1 séparés gardés pour compat tests
  // historiques M2-5.11.A→L (peuvent disparaître après cleanup M2-6).
  decisions: { bg: 'var(--sol-refuse-bg)', accent: 'var(--sol-refuse-fg)' },
  p0: { bg: 'var(--sol-refuse-bg)', accent: 'var(--sol-refuse-fg)' },
  p1: { bg: 'var(--sol-attention-bg)', accent: 'var(--sol-attention-fg)' },
  without_owner: { bg: 'var(--sol-bg-panel)', accent: 'var(--sol-ink-500)' },
  at_risk: { bg: 'var(--sol-refuse-bg)', accent: 'var(--sol-refuse-fg)' },
  secured: { bg: 'var(--sol-succes-bg)', accent: 'var(--sol-succes-fg)' },
  // M2-5.12 — SLA en retard : refuse-bg (urgence) mais accent ink-500
  // (désactivé MV3, pas de signal émotionnel tant que la donnée n'existe pas).
  sla_overdue: { bg: 'var(--sol-bg-panel)', accent: 'var(--sol-ink-400)' },
};

// ── M2-5.10.E — Pilotage / Journal org-wide (doctrine §8.2) ───────
//
// Page `/action-center-v4/pilotage/journal` — flux d'activité cross-items
// des 7 derniers jours (timeline avec day-groups). Accessible via le
// view toggle Décisions / Journal posé sur les pages Pilotage.
//
// MV3 livré : timeline 7j org-wide + day-groups Aujourd'hui/Hier/dates +
// item title joint + actor pill. Hors scope (BACKLOG_M3) : filtres
// event_type serveur, narrative bar agrégée 5 stats, export PDF,
// drill-down acteur, fenêtres glissantes paramétrables UI.

export const JOURNAL_COPY = {
  pageTitle: 'Journal',
  sectionTitle: "Flux d'activité",
  sectionSub:
    "Tous les événements de votre Centre d'action sur la fenêtre 7 jours, " +
    'triés du plus récent au plus ancien.',
  countSuffix: (n) => {
    if (n === 0) return 'aucun événement';
    if (n === 1) return '1 événement · 7 derniers jours';
    return `${n} événements · 7 derniers jours`;
  },
  emptyTitle: 'Aucun événement récent',
  emptyText:
    'Aucune activité sur les 7 derniers jours. Les transitions, ajouts de preuve, ' +
    "blocages et clôtures apparaîtront ici dès qu'ils auront lieu.",
  errorTitle: 'Impossible de charger le journal',
  viewToggleDecisions: 'Décisions',
  viewToggleJournal: 'Journal',
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
