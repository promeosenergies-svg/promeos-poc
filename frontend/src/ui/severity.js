/**
 * Source de vérité pour les niveaux de sévérité — frontend.
 *
 * Audit /simplify 26/04/2026 : avant ce fichier, le lexique sévérité était
 * dispersé en 3 endroits (PriorityHero, AlertStack, TopContributors) avec
 * 3 mappings tailwind quasi-identiques + le backend qui retourne `crit/warn/ok`
 * (3e lexique). Cette source unique unifie : `critical/warn/info/ok` côté FE.
 *
 * Mapping backend ↔ frontend : la fonction `normalizeSeverity` accepte les
 * variantes (`crit` → `critical`) pour faciliter le pont API.
 */

export const SEVERITY = Object.freeze({
  CRITICAL: 'critical',
  WARN: 'warn',
  INFO: 'info',
  OK: 'ok',
});

/** Ordre de priorité (plus petit = plus prioritaire) pour tri AlertStack. */
export const SEVERITY_RANK = Object.freeze({
  [SEVERITY.CRITICAL]: 0,
  [SEVERITY.WARN]: 1,
  [SEVERITY.INFO]: 2,
  [SEVERITY.OK]: 3,
});

/** Pont backend → frontend (le backend retourne `crit`, certains modules `warning`). */
export function normalizeSeverity(raw) {
  if (!raw) return SEVERITY.INFO;
  const v = String(raw).toLowerCase();
  if (v === 'crit' || v === 'critical') return SEVERITY.CRITICAL;
  if (v === 'warn' || v === 'warning') return SEVERITY.WARN;
  if (v === 'ok' || v === 'success') return SEVERITY.OK;
  return SEVERITY.INFO;
}

/** Classes Tailwind par sévérité — utilisé par PriorityHero/AlertStack/banners. */
export const SEVERITY_CLASSES = Object.freeze({
  [SEVERITY.CRITICAL]: {
    bg: 'bg-red-50',
    border: 'border-red-300',
    accentBar: 'border-l-4 border-red-500',
    title: 'text-red-900',
    impact: 'text-red-700',
    deadline: 'text-red-600',
    cta: 'bg-red-600 hover:bg-red-700 text-white',
    pill: 'bg-red-50 text-red-700 ring-red-200',
  },
  [SEVERITY.WARN]: {
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    accentBar: 'border-l-4 border-amber-500',
    title: 'text-amber-900',
    impact: 'text-amber-700',
    deadline: 'text-amber-600',
    cta: 'bg-amber-600 hover:bg-amber-700 text-white',
    pill: 'bg-amber-50 text-amber-700 ring-amber-200',
  },
  [SEVERITY.INFO]: {
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    accentBar: 'border-l-4 border-blue-500',
    title: 'text-blue-900',
    impact: 'text-blue-700',
    deadline: 'text-blue-600',
    cta: 'bg-blue-600 hover:bg-blue-700 text-white',
    pill: 'bg-blue-50 text-blue-700 ring-blue-200',
  },
  [SEVERITY.OK]: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    accentBar: 'border-l-4 border-emerald-500',
    title: 'text-emerald-900',
    impact: 'text-emerald-700',
    deadline: 'text-emerald-600',
    cta: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    pill: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  },
});

export function getSeverityClasses(severity) {
  const key = normalizeSeverity(severity);
  return SEVERITY_CLASSES[key] ?? SEVERITY_CLASSES[SEVERITY.INFO];
}
