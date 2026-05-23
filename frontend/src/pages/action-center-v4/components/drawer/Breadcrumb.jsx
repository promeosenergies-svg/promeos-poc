import { BREADCRUMB_DRAWER_COPY } from '../../constants';

/**
 * M2-5.10.B.bis — Breadcrumb MONO Sol pour le header drawer (maquette §8.4
 * lignes 678-682). PROMEOS › Centre d'action › Référentiel › **Détail**.
 *
 * Statique MV3 — le segment « File prioritaire » sera dynamique quand
 * M2-5.10.D Pilotage sera livré (route /action-center-v4/pilotage). Les
 * segments « actifs » (b) sont en `--sol-ink-900`, les liens en
 * `--sol-ink-500`, les séparateurs en `--sol-ink-300`.
 */
export function Breadcrumb({ items = null }) {
  // Permet à un parent de personnaliser (sinon défaut MV3).
  const segments = items || [
    { label: BREADCRUMB_DRAWER_COPY.app, strong: true },
    { label: BREADCRUMB_DRAWER_COPY.section },
    { label: BREADCRUMB_DRAWER_COPY.page },
    { label: BREADCRUMB_DRAWER_COPY.current, strong: true },
  ];

  return (
    <nav
      aria-label="Fil d'Ariane"
      className="font-mono text-[10px] font-medium uppercase tracking-[0.14em]"
      style={{ color: 'var(--sol-ink-500)' }}
    >
      {segments.map((seg, i) => (
        <span key={`${seg.label}-${i}`}>
          {seg.strong ? (
            <b className="font-semibold" style={{ color: 'var(--sol-ink-900)' }}>
              {seg.label}
            </b>
          ) : (
            seg.label
          )}
          {i < segments.length - 1 && (
            <span aria-hidden="true" className="mx-1.5" style={{ color: 'var(--sol-ink-300)' }}>
              ›
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
