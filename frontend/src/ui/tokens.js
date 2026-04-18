/**
 * PROMEOS Design Tokens
 * Shared spacing, typography, color constants.
 */

export const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
  },
  success: { 50: '#f0fdf4', 500: '#22c55e', 700: '#15803d' },
  warning: { 50: '#fffbeb', 500: '#f59e0b', 700: '#b45309' },
  danger: { 50: '#fef2f2', 500: '#ef4444', 700: '#b91c1c' },
  neutral: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
};

export const spacing = {
  page: 'px-6 py-6',
  section: 'mb-6',
  card: 'p-5',
  gap: 'gap-4',
};

export const radius = {
  sm: 'rounded',
  md: 'rounded-lg',
  full: 'rounded-full',
};

/**
 * Sol V1 design tokens — isolated namespace.
 *
 * Source de vérité UX : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 * Insight stratégique "journal en terrasse" — slate pro + accents warm
 * (DECISIONS_LOG.md UX-1).
 *
 * Usage : appliquer className="sol-surface" sur le wrapper de page Sol
 * pour activer ces tokens via CSS custom properties (cf index.css).
 * Les tokens PROMEOS existants (colors/spacing/radius) restent intacts.
 */
export const solTokens = {
  bg: {
    canvas: '#F8F9FA',   // slate très clair, off-white (vs Tailwind white)
    paper: '#FFFFFF',
    panel: '#F3F4F6',
  },
  ink: {
    900: '#0F172A',   // slate-900 tranchant
    700: '#334155',
    500: '#64748B',
    400: '#94A3B8',
    300: '#CBD5E1',
    200: '#E2E8F0',
    100: '#F1F5F9',
  },
  rule: '#E2E8F0',

  // Accents émotionnels warm hérités — "journal en terrasse"
  accent: {
    calmeFg: '#2F6B5E',      // bleu-vert doux (proposing, bonne nouvelle)
    calmeBg: '#E3F0ED',
    attentionFg: '#A06B1A',  // ambre chaleureux (à regarder)
    attentionBg: '#F6EAD2',
    afaireFg: '#B8552E',     // orange corail non punitif (à faire)
    afaireBg: '#F7E4D8',
    succesFg: '#2E6B4A',     // vert forêt (validé, conforme)
    succesBg: '#DFEDE3',
    refuseFg: '#8B3A3A',
    refuseBg: '#F3DDDB',
  },

  // Tariff colors (courbe de charge HP/HC)
  tariff: {
    hphFg: '#B84545', hphBg: '#FBE9E9',   // heures pleines (signal fort)
    hchFg: '#2E4A6B', hchBg: '#E6EDF5',   // heures creuses (calme, éco)
  },
};
