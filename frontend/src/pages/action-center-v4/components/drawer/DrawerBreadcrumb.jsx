import { Fragment } from 'react';

/**
 * M2-6.C.3 (commit 4/4) — Breadcrumb patrimonial du drawer item.
 *
 * Affiche le chemin patrimoine de l'item :
 *   organisation › site › bâtiment › compteur
 *
 * Sémantique cardinale (différente du `Breadcrumb` existant qui porte le
 * fil d'Ariane navigation `PROMEOS › Centre d'action › Référentiel › KIND
 * › DOMAIN › Détail` — purement applicatif). Ce composant ajoute le contexte
 * PATRIMONIAL nécessaire à l'utilisateur pour situer l'item dans son parc :
 * « cette action concerne quel site / quel bâtiment ? ».
 *
 * Mode MV3 (cardinal) :
 * - Le backend `ActionCenterItemResponse` n'expose actuellement que
 *   `organisation_id` (Integer) — pas de `*_name`.
 * - Le composant lit les champs s'ils existent, sinon retourne `null`
 *   (silencieux, conforme doctrine §6.6 « pas de chiffre menteur »).
 * - Activable dès que le BE expose les noms snapshots (M3 backend dette
 *   tracée : `M3-DRAWER-BREADCRUMB-PATRIMOINE-BE`).
 *
 * Pattern « MV3-ready » : composant complet côté frontend, attend le BE.
 * Aucun changement payload requis pour livrer ce commit (garde-fou Amine).
 */
export function DrawerBreadcrumb({ item }) {
  if (!item) return null;

  // Champs lus défensivement — si BE expose un jour ces snapshots ils
  // s'affichent. Ordre canonique du plus large au plus précis.
  const segments = [
    item.organisation_name,
    item.site_name,
    item.building_name,
    item.meter_id,
  ].filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <nav
      aria-label="Chemin patrimoine"
      className="flex items-center gap-1 font-mono text-[11px] tracking-[0.02em]"
      style={{ color: 'var(--sol-ink-500)' }}
      data-testid="drawer-breadcrumb"
    >
      {segments.map((segment, index) => (
        <Fragment key={index}>
          {index > 0 && (
            <span aria-hidden="true" style={{ color: 'var(--sol-ink-300)' }} className="mx-0.5">
              →
            </span>
          )}
          <span
            className={index === segments.length - 1 ? 'font-semibold' : ''}
            style={{
              color: index === segments.length - 1 ? 'var(--sol-ink-900)' : 'var(--sol-ink-500)',
            }}
            data-testid="drawer-breadcrumb-segment"
          >
            {segment}
          </span>
        </Fragment>
      ))}
    </nav>
  );
}
