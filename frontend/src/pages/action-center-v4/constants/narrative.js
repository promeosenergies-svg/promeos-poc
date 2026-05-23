/**
 * M2-6.C.3 (commit 2/4) — Constantes Centre d'Action V4 / narrative.
 *
 * Surfaces haut-niveau : pages Pilotage + Référentiel + Journal,
 * Masthead Sol, NarrativeBar 5 compteurs CFO, bloc éditorial Sophie Marin,
 * SOL_COPY filtres, COPY tableau, A11Y_COPY clavier.
 */

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
