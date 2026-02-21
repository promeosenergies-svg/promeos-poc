/**
 * PROMEOS — Labels centralisés conformité (FR)
 *
 * Source de vérité unique pour tous les libellés, statuts, et textes métier
 * affichés dans le cockpit conformité et le plan d'actions.
 *
 * Convention : aucun anglais visible en mode normal.
 * Les codes internes (rule_id, engine_version) ne sont affichés qu'en Mode expert.
 */

// ─── Réglementations ────────────────────────────────────────────────────

export const REG_LABELS = {
  decret_tertiaire_operat: 'Décret Tertiaire',
  bacs: 'BACS (GTB/GTC)',
  aper: 'Loi APER (ENR)',
};

export const REG_DESCRIPTIONS = {
  decret_tertiaire_operat: 'Réduire la consommation énergétique des bâtiments tertiaires > 1 000 m²',
  bacs: 'Systèmes d\'automatisation et de contrôle des bâtiments (GTB/GTC)',
  aper: 'Installation d\'énergies renouvelables sur parkings > 1 500 m²',
};

// ─── Statuts conformité ─────────────────────────────────────────────────

export const STATUT_LABELS = {
  conforme:      'Conforme',
  non_conforme:  'Non conforme',
  a_risque:      'À risque',
  a_qualifier:   'À qualifier',
  derogation:    'Dérogation',
  hors_perimetre:'Hors périmètre',
};

/** Mapping des codes backend (OK/NOK/UNKNOWN/OUT_OF_SCOPE) → clé interne */
export const BACKEND_STATUS_MAP = {
  OK:           'conforme',
  NOK:          'non_conforme',
  UNKNOWN:      'a_qualifier',
  OUT_OF_SCOPE: 'hors_perimetre',
};

// ─── Workflow (findings) ────────────────────────────────────────────────

export const WORKFLOW_LABELS = {
  open:           'À traiter',
  ack:            'En cours',
  resolved:       'Résolu',
  false_positive: 'Faux positif',
};

// ─── Workflow (actions) ─────────────────────────────────────────────────

export const ACTION_STATUS_LABELS = {
  backlog:     'À planifier',
  planned:     'Planifiée',
  in_progress: 'En cours',
  done:        'Terminée',
};

// ─── Sévérité ───────────────────────────────────────────────────────────

export const SEVERITY_LABELS = {
  critical: 'Critique',
  high:     'Élevée',
  medium:   'Moyenne',
  low:      'Faible',
};

export const SEVERITY_BADGE_MAP = {
  critical: 'crit',
  high:     'warn',
  medium:   'info',
  low:      'neutral',
};

// ─── Confiance ──────────────────────────────────────────────────────────

export const CONFIDENCE_LABELS = {
  high:   'Élevée',
  medium: 'Moyenne',
  low:    'Faible',
};

// ─── Types d'action ─────────────────────────────────────────────────────

export const ACTION_TYPE_LABELS = {
  conformite:  'Conformité',
  conso:       'Consommation',
  facture:     'Facturation',
  maintenance: 'Maintenance',
};

// ─── Onglets cockpit ────────────────────────────────────────────────────

export const COCKPIT_TABS = [
  { id: 'obligations', label: 'Obligations' },
  { id: 'donnees',     label: 'Données & Qualité' },
  { id: 'execution',   label: 'Plan d\'exécution' },
  { id: 'preuves',     label: 'Preuves & Rapports' },
];

// ─── États vides ────────────────────────────────────────────────────────

export const EMPTY_REASONS = {
  NO_SITES:       { title: 'Aucun site dans le périmètre',   text: 'Ajoutez des sites via le patrimoine pour démarrer.',       ctaLabel: 'Aller au patrimoine', ctaPath: '/patrimoine' },
  NO_EVALUATION:  { title: 'Évaluation non lancée',          text: 'Cliquez « Réévaluer » pour lancer la première analyse.' },
  ALL_COMPLIANT:  { title: 'Tout est conforme',              text: 'Aucune non-conformité détectée. Félicitations !' },
  DATA_BLOCKED:   { title: 'Données indisponibles',          text: 'Erreur d\'accès aux données de conformité. Réessayez.' },
};

// ─── Termes techniques → FR ─────────────────────────────────────────────

export const TECH_TERMS_FR = {
  deadline:   'Échéance',
  tier:       'Niveau',
  scope:      'Périmètre',
  bundle:     'Synthèse',
  intake:     'Collecte des informations',
  upload:     'Téléversement',
  audit:      'Détails',
  owner:      'Responsable',
  finding:    'Constat',
  evidence:   'Preuve',
  readiness:  'Maturité',
};

// ─── Labels rule_id → FR (plan d'exécution humanisé) ────────────────────

export const RULE_LABELS = {
  // Décret Tertiaire
  DT_SCOPE:            { title_fr: 'Périmètre Décret Tertiaire',       why_fr: 'Vérifier si le site est soumis au Décret Tertiaire (surface tertiaire ≥ 1 000 m²).' },
  DT_OPERAT:           { title_fr: 'Déclaration OPERAT',               why_fr: 'Déclarer les consommations énergétiques sur la plateforme OPERAT.' },
  DT_TRAJECTORY_2030:  { title_fr: 'Trajectoire 2030 (-40 %)',         why_fr: 'Atteindre l\'objectif de réduction de 40 % par rapport à la consommation de référence.' },
  DT_TRAJECTORY_2040:  { title_fr: 'Trajectoire 2040 (-50 %)',         why_fr: 'Atteindre l\'objectif de réduction de 50 % par rapport à la consommation de référence.' },
  DT_ENERGY_DATA:      { title_fr: 'Données énergétiques',             why_fr: 'Renseigner les données de consommation annuelle du site.' },

  // BACS
  BACS_POWER:          { title_fr: 'Puissance CVC',                    why_fr: 'Vérifier si la puissance CVC du bâtiment dépasse le seuil (> 70 kW).' },
  BACS_HIGH_DEADLINE:  { title_fr: 'BACS — Échéance haute puissance',  why_fr: 'CVC > 290 kW : obligation GTB/GTC avec échéance au 1er janvier 2025.' },
  BACS_LOW_DEADLINE:   { title_fr: 'BACS — Échéance basse puissance',  why_fr: 'CVC entre 70 et 290 kW : obligation GTB/GTC avec échéance au 1er janvier 2027.' },
  BACS_ATTESTATION:    { title_fr: 'Attestation GTB/GTC',              why_fr: 'Fournir l\'attestation de conformité du système GTB/GTC (classe B minimum).' },
  BACS_DEROGATION:     { title_fr: 'Dérogation BACS',                  why_fr: 'Demander une dérogation si le TRI dépasse 6 ans.' },

  // APER
  APER_PARKING:        { title_fr: 'Parking — Loi APER',               why_fr: 'Vérifier si la surface de parking extérieur dépasse 1 500 m².' },
  APER_TOITURE:        { title_fr: 'Toiture — Loi APER',               why_fr: 'Vérifier si la surface de toiture dépasse 500 m².' },
  APER_PARKING_TYPE:   { title_fr: 'Type de parking',                  why_fr: 'Vérifier que le parking est de type extérieur (non couvert).' },
};

/** Prochaines étapes par rule_id (pour le plan d'exécution) */
export const RULE_NEXT_STEPS = {
  DT_SCOPE:            ['Vérifier la surface tertiaire dans le patrimoine'],
  DT_OPERAT:           ['Créer un compte OPERAT', 'Déclarer les consommations de l\'année de référence'],
  DT_TRAJECTORY_2030:  ['Identifier les gisements d\'économies', 'Planifier les travaux de rénovation énergétique'],
  DT_TRAJECTORY_2040:  ['Poursuivre le plan de réduction', 'Envisager des énergies renouvelables'],
  DT_ENERGY_DATA:      ['Collecter les factures d\'énergie', 'Renseigner les consommations annuelles'],
  BACS_POWER:          ['Vérifier la puissance CVC installée auprès du mainteneur'],
  BACS_HIGH_DEADLINE:  ['Lancer l\'appel d\'offres GTB/GTC', 'Installer le système avant l\'échéance'],
  BACS_LOW_DEADLINE:   ['Planifier l\'installation GTB/GTC avant le 1er janvier 2027'],
  BACS_ATTESTATION:    ['Demander l\'attestation de conformité au prestataire GTB/GTC'],
  BACS_DEROGATION:     ['Réaliser l\'étude de TRI', 'Constituer le dossier de dérogation'],
  APER_PARKING:        ['Mesurer la surface exacte du parking', 'Étudier la faisabilité d\'ombrières solaires'],
  APER_TOITURE:        ['Mesurer la surface de toiture exploitable', 'Étudier l\'installation photovoltaïque'],
  APER_PARKING_TYPE:   ['Vérifier le type de parking (extérieur / couvert)'],
};

/** Preuves attendues par rule_id */
export const RULE_EXPECTED_PROOFS = {
  DT_SCOPE:            ['Relevé de surface tertiaire'],
  DT_OPERAT:           ['Récépissé de déclaration OPERAT', 'Attestation annuelle'],
  DT_TRAJECTORY_2030:  ['Plan de réduction énergétique', 'Suivi annuel des consommations'],
  DT_TRAJECTORY_2040:  ['Plan de réduction énergétique', 'Suivi annuel des consommations'],
  DT_ENERGY_DATA:      ['Factures d\'énergie', 'Relevés de compteurs'],
  BACS_POWER:          ['Fiche technique CVC', 'Attestation du mainteneur'],
  BACS_HIGH_DEADLINE:  ['Attestation GTB/GTC conforme (classe B min.)', 'Rapport d\'inspection'],
  BACS_LOW_DEADLINE:   ['Attestation GTB/GTC conforme (classe B min.)', 'Rapport d\'inspection'],
  BACS_ATTESTATION:    ['Attestation GTB/GTC conforme'],
  BACS_DEROGATION:     ['Étude TRI', 'Dossier de dérogation'],
  APER_PARKING:        ['Plan cadastral', 'Étude de faisabilité ombrières'],
  APER_TOITURE:        ['Plan de toiture', 'Étude de faisabilité photovoltaïque'],
  APER_PARKING_TYPE:   ['Photographie aérienne', 'Plan de masse'],
};

// ─── Drawer / UI labels ─────────────────────────────────────────────────

export const DRAWER_LABELS = {
  finding_title:     'Constat réglementaire',
  loading:           'Chargement…',
  not_found:         'Constat introuvable',
  identity:          'Identité',
  inputs:            'Données utilisées',
  params:            'Paramètres / seuils',
  evidence_refs:     'Preuves / références',
  explanation:       'Explication',
  metadata:          'Métadonnées',
  technical_details: 'Détails techniques',
  regulation:        'Réglementation',
  status:            'Statut',
  severity:          'Sévérité',
  site:              'Site',
  deadline:          'Échéance',
  workflow:          'État du traitement',
  engine_version:    'Version moteur',
  computed_at:       'Calculé le',
  updated_at:        'Mis à jour le',
  rule_id:           'Identifiant règle',
  owner:             'Responsable',
  create_action:     'Créer une action',
  add_proof:         'Ajouter une preuve',
  complete_data:     'Compléter les données',
  view_details:      'Voir les détails',
  recompute:         'Réévaluer',
};

// ─── RegOps status → FR ─────────────────────────────────────────────────

export const REGOPS_STATUS_LABELS = {
  COMPLIANT:          'Conforme',
  AT_RISK:            'À risque',
  NON_COMPLIANT:      'Non conforme',
  UNKNOWN:            'À qualifier',
  OUT_OF_SCOPE:       'Hors périmètre',
  EXEMPTION_POSSIBLE: 'Dérogation possible',
};

export const REGOPS_SEVERITY_LABELS = {
  CRITICAL: 'Critique',
  HIGH:     'Élevée',
  MEDIUM:   'Moyenne',
  LOW:      'Faible',
};
