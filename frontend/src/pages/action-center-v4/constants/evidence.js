/**
 * M2-6.C.3 (commit 2/4) — Constantes Centre d'Action V4 / evidence.
 *
 * Les 3 types d'attachments d'un item : preuves (uploadées + vérifiées),
 * blocages (signalés + résolus), liens (vers d'autres modules).
 * Couvre les statuts dérivés, libellés FR, copy modals add/verify/resolve.
 */

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
