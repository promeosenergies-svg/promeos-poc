/**
 * M2-6.C.3 (commit 2/4) — Constantes Centre d'Action V4 / classification.
 *
 * Les 3 axes orthogonaux de classement d'un action_center_item :
 * - priority_bracket : urgence dérivée (P0-P3, règles R1-R6 backend)
 * - kind             : nature intrinsèque (7 valeurs anomaly/action/…)
 * - domain           : pilier métier (7 valeurs conformite/optimisation/…)
 *
 * Chaque axe : libellés FR + variantes Sol (palette doctrine §3.2) +
 * mappings Badge (palette severity).
 */

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
