/**
 * PROMEOS Design System — Conventions V1
 * B2B, sobre, ultra clair. Labels 100% FR.
 *
 * Ce fichier sert de reference executable pour les conventions UI.
 * Utiliser ces constantes dans les pages pour garantir la coherence.
 */

// ── Spacing standards (classes Tailwind) ────────────────────────────
export const LAYOUT = {
  page: 'px-6 py-6',
  sectionGap: 'space-y-6',
  cardGrid3: 'grid grid-cols-1 md:grid-cols-3 gap-6',
  cardGrid4: 'grid grid-cols-2 md:grid-cols-4 gap-3',
};

// ── Typography scale ────────────────────────────────────────────────
export const TYPO = {
  pageTitle: 'text-xl font-bold text-gray-900',
  pageSubtitle: 'text-sm text-gray-500',
  sectionTitle: 'text-lg font-bold text-gray-900',
  kpiLabel: 'text-xs text-gray-500 font-medium uppercase tracking-wider',
  kpiValue: 'text-2xl font-bold text-gray-900',
  caption: 'text-xs text-gray-400',
};

// ── Labels FR — etats communs ───────────────────────────────────────
export const LABELS_FR = {
  loading: 'Chargement...',
  noData: 'Aucune donnee',
  error: 'Erreur de chargement',
  retry: 'Reessayer',
  noResults: 'Aucun resultat',
  import: 'Importer',
  export: 'Exporter',
  sites: 'Sites',
  total: 'Total',
  active: 'Actif',
  inactive: 'Inactif',
};
