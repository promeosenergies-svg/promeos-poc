/**
 * grammar/hub/states/HubSkeleton — Skeleton générique L11 (loading state).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.3 — extraction de CockpitJourSkeleton
 * inline depuis pages/CockpitJour.jsx vers le namespace canonique states/.
 *
 * 4 variants, dimensions calees sur les primitifs reels (eviter shift de
 * layout au mount) :
 *   - 'hero'      → 180px (SolHeroPremiumNight)
 *   - 'kpi'       → 128px (HubKpiCard min-height)
 *   - 'chart'     → 220px (ChartFrame + chart svg 120px + meta)
 *   - 'highlight' → 70px  (HubHighlight row)
 *
 * Animation : utilise la classe Tailwind `animate-pulse` qui respecte deja
 * `prefers-reduced-motion: reduce` (cf media query @media dans tokens.css).
 * Aucun keyframe custom necessaire.
 *
 * Source-guards : `data-component="HubSkeleton"` + `data-skeleton-variant`.
 * Display-only — zero calcul metier.
 *
 * @typedef {'hero'|'kpi'|'chart'|'highlight'} HubSkeletonVariant
 *
 * @typedef {Object} HubSkeletonProps
 * @property {HubSkeletonVariant} variant
 * @property {number} [count=1]      - Nombre d'instances rendues (DRY pour
 *                                     triptyques KPI / paires charts).
 * @property {string|number} [width] - Override CSS width (rare, debug).
 * @property {string|number} [height]- Override CSS height en px (rare, debug).
 * @property {string} [className='']
 *
 * @param {HubSkeletonProps} props
 */

const VARIANT_HEIGHT = Object.freeze({
  hero: 180,
  kpi: 128,
  chart: 220,
  highlight: 70,
});

const VARIANT_LABEL = Object.freeze({
  hero: 'Chargement du briefing',
  kpi: 'Chargement KPI',
  chart: 'Chargement chart',
  highlight: 'Chargement priorite',
});

export default function HubSkeleton({ variant, count = 1, width, height, className = '' }) {
  if (!variant || !VARIANT_HEIGHT[variant]) {
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.error(
        `[HubSkeleton] variant "${variant}" invalide. Valeurs : hero|kpi|chart|highlight.`
      );
    }
    return null;
  }

  const safeCount = Math.max(1, Math.floor(count));
  const h = height ?? VARIANT_HEIGHT[variant];

  const items = Array.from({ length: safeCount }, (_, i) => (
    <div
      key={`skeleton-${variant}-${i}`}
      data-component="HubSkeleton"
      data-skeleton-variant={variant}
      data-skeleton-index={i}
      role="status"
      aria-busy="true"
      aria-label={VARIANT_LABEL[variant]}
      className={`rounded-xl animate-pulse ${className}`}
      style={{
        background: 'var(--sol-ink-100)',
        height: `${h}px`,
        width: width ?? '100%',
      }}
    />
  ));

  if (safeCount === 1) return items[0];

  // Plusieurs items — grille fluide alignee sur les slots L11 (KpiTriptych
  // gap-3.5, ChartPair gap-3.5, Highlights space-y-2). On laisse le parent
  // (HubPage.KpiTriptych / ChartPair / Highlights) gerer la grille reelle ;
  // ici on retourne un fragment pour fluidite de composition.
  return <>{items}</>;
}
