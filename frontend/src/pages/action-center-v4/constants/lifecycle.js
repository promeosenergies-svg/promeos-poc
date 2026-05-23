/**
 * M2-6.C.3 (commit 2/4) — Constantes Centre d'Action V4 / lifecycle.
 *
 * Cycle de vie complet d'un action_center_item : 5 états canoniques V4,
 * transitions disponibles, libellés FR + variantes Sol émotionnelles,
 * verbes dynamiques par état, bandeau d'item clôturé.
 *
 * Extrait de l'ancien constants.js monolithique (865 lignes) — voir
 * constants/index.js pour re-exports compat layer.
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
