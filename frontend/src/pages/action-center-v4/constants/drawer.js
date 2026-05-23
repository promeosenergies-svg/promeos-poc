/**
 * M2-6.C.3 (commit 2/4) — Constantes Centre d'Action V4 / drawer.
 *
 * Drawer détail item : onglets (Historique/Preuves/Blocages/Liens),
 * actions principales (verbe dynamique + Plus ▾), section impact financier
 * 4 quadrants, timeline acteur, breadcrumb, footer audit, placeholders M3+.
 */

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

// Layout audit-list maquette §8.4 lignes 614-637. Mapping acteur backend → UI :
// `actor_type` (enum 'system' | 'user') détermine la pill ; `actor_name` est
// snapshoté côté write. Si absent → `fallbackActor` (générique). M2-6.C audit
// RGPD : `actor_role` n'est plus utilisé comme fallback d'affichage (anti-
// déduction §6.3 — un rôle organisationnel peut identifier une personne).
export const TIMELINE_ACTOR_COPY = {
  systemLabel: 'PROMEOS',
  fallbackActor: 'Système',
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
