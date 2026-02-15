/**
 * PROMEOS — Color Tokens (Phase 6)
 * Semantic color mapping for KPI types, severity levels, and accents.
 * Rule: neutral-first + controlled accents. No full-color backgrounds.
 */

// ── KPI Accent Mapping ──
// Each KPI type gets ONE stable accent color.
export const KPI_ACCENTS = {
  conformite: {
    accent: 'primary',
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    border: 'border-blue-500',
    tintBg: 'bg-blue-50/60',
    tintText: 'text-blue-700',
    ringClass: 'ring-blue-500/20',
  },
  risque: {
    accent: 'amber',
    iconBg: 'bg-amber-50',
    iconText: 'text-amber-600',
    border: 'border-amber-500',
    tintBg: 'bg-amber-50/60',
    tintText: 'text-amber-700',
    ringClass: 'ring-amber-500/20',
  },
  alertes: {
    accent: 'indigo',
    iconBg: 'bg-indigo-50',
    iconText: 'text-indigo-600',
    border: 'border-indigo-500',
    tintBg: 'bg-indigo-50/60',
    tintText: 'text-indigo-700',
    ringClass: 'ring-indigo-500/20',
  },
  sites: {
    accent: 'primary',
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    border: 'border-blue-500',
    tintBg: 'bg-blue-50/60',
    tintText: 'text-blue-700',
    ringClass: 'ring-blue-500/20',
  },
  maturite: {
    accent: 'primary',
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    border: 'border-blue-400',
    tintBg: 'bg-blue-50/60',
    tintText: 'text-blue-700',
    ringClass: 'ring-blue-500/20',
  },
  neutral: {
    accent: 'gray',
    iconBg: 'bg-gray-100',
    iconText: 'text-gray-500',
    border: 'border-gray-300',
    tintBg: 'bg-gray-50',
    tintText: 'text-gray-600',
    ringClass: 'ring-gray-300/20',
  },
};

// ── Severity Tints ──
// Micro-signals only: StatusDot, small badges, tiny borders. Never big backgrounds.
export const SEVERITY_TINT = {
  critical: {
    dot: 'bg-red-500',
    chipBg: 'bg-red-50',
    chipText: 'text-red-700',
    chipBorder: 'border-red-200',
    label: 'Critique',
  },
  high: {
    dot: 'bg-amber-500',
    chipBg: 'bg-amber-50',
    chipText: 'text-amber-700',
    chipBorder: 'border-amber-200',
    label: 'Eleve',
  },
  warn: {
    dot: 'bg-amber-500',
    chipBg: 'bg-amber-50',
    chipText: 'text-amber-700',
    chipBorder: 'border-amber-200',
    label: 'Attention',
  },
  medium: {
    dot: 'bg-blue-400',
    chipBg: 'bg-blue-50',
    chipText: 'text-blue-700',
    chipBorder: 'border-blue-200',
    label: 'Moyen',
  },
  info: {
    dot: 'bg-blue-400',
    chipBg: 'bg-blue-50',
    chipText: 'text-blue-700',
    chipBorder: 'border-blue-200',
    label: 'Info',
  },
  low: {
    dot: 'bg-gray-400',
    chipBg: 'bg-gray-50',
    chipText: 'text-gray-600',
    chipBorder: 'border-gray-200',
    label: 'Faible',
  },
  neutral: {
    dot: 'bg-gray-300',
    chipBg: 'bg-gray-50',
    chipText: 'text-gray-600',
    chipBorder: 'border-gray-200',
    label: '-',
  },
};

// ── Accent Bar Colors ──
// For the left 3px bar on MetricCards.
export const ACCENT_BAR = {
  primary: 'bg-blue-500',
  amber: 'bg-amber-500',
  indigo: 'bg-indigo-500',
  gray: 'bg-gray-300',
};

// ── Hero band / premium card accents ──
export const HERO_ACCENTS = {
  priority: {
    bg: 'bg-amber-50/50',
    border: 'border-amber-200/60',
    ring: 'ring-1 ring-amber-200/40',
  },
  success: {
    bg: 'bg-emerald-50/50',
    border: 'border-emerald-200/60',
    ring: 'ring-1 ring-emerald-200/40',
  },
  executive: {
    bg: 'bg-indigo-50/40',
    border: 'border-indigo-200/50',
    ring: 'ring-1 ring-indigo-200/30',
  },
};
