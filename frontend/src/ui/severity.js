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

/** Classes utilitaires par sévérité.
 *
 * Audit CX 26/04 (sol2 Phase 1) : avant cette version, les classes étaient
 * `bg-red-50 / text-red-900` (Tailwind brut) qui ne fonctionnaient qu'à
 * travers les overrides `!important` de `index.css`. Si un dev ajoutait
 * un composant qui consommait directement les vars Sol via `var(--sol-*)`,
 * l'incohérence apparaissait. Cette version utilise des classes éditoriales
 * `sol-{severity}-{role}` qui pointent directement sur les vars Sol côté
 * `tokens.css` — composants robustes hors override Tailwind.
 *
 * Convention :
 *   bg        : fond saturé léger (badge, banner)
 *   border    : bordure neutre légèrement teintée
 *   accentBar : barre latérale 4px (left accent)
 *   title     : couleur titre fort
 *   impact    : couleur valeur secondaire
 *   deadline  : couleur metadata claire
 *   cta       : button primary fill
 *   pill      : pill compact (chip)
 */
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

/** Style inline avec tokens Sol natifs — bypass overrides Tailwind.
 *
 * Utiliser quand le composant doit garantir l'identité Sol même sans le
 * `index.css` global (ex. tests Storybook isolés, exports PDF).
 *
 * @example
 *   const styles = getSeverityInlineStyles('critical');
 *   <div style={styles.bg}>...</div>
 */
export function getSeverityInlineStyles(severity) {
  const key = normalizeSeverity(severity);
  const map = {
    [SEVERITY.CRITICAL]: {
      bg: { backgroundColor: 'var(--sol-refuse-bg)' },
      border: { borderColor: 'var(--sol-refuse-fg)' },
      title: { color: 'var(--sol-refuse-fg)' },
      cta: { backgroundColor: 'var(--sol-refuse-fg)', color: 'white' },
    },
    [SEVERITY.WARN]: {
      bg: { backgroundColor: 'var(--sol-attention-bg)' },
      border: { borderColor: 'var(--sol-attention-fg)' },
      title: { color: 'var(--sol-attention-fg)' },
      cta: { backgroundColor: 'var(--sol-attention-fg)', color: 'white' },
    },
    [SEVERITY.INFO]: {
      bg: { backgroundColor: 'var(--sol-calme-bg)' },
      border: { borderColor: 'var(--sol-calme-fg)' },
      title: { color: 'var(--sol-calme-fg)' },
      cta: { backgroundColor: 'var(--sol-calme-fg)', color: 'white' },
    },
    [SEVERITY.OK]: {
      bg: { backgroundColor: 'var(--sol-succes-bg)' },
      border: { borderColor: 'var(--sol-succes-fg)' },
      title: { color: 'var(--sol-succes-fg)' },
      cta: { backgroundColor: 'var(--sol-succes-fg)', color: 'white' },
    },
  };
  return map[key] ?? map[SEVERITY.INFO];
}

export function getSeverityClasses(severity) {
  const key = normalizeSeverity(severity);
  return SEVERITY_CLASSES[key] ?? SEVERITY_CLASSES[SEVERITY.INFO];
}
