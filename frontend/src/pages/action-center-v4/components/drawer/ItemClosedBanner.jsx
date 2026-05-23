import { Lock } from 'lucide-react';

import { CLOSED_BANNER_COPY } from '../../constants';
import { formatDateTimeFR } from '../../utils/date';

/**
 * M2-5.10.B.bis — Bandeau persistant pour les items en état `closed` (audit
 * UX Marie P0-3 + CS P0-2 : sans message explicite, l'utilisateur conclut à
 * un bug et appelle le support).
 *
 * Posé en tête du body drawer (au-dessus d'ItemHeader). Couleur Sol succès
 * (l'action est terminée — émotionnellement positif), pas un avertissement.
 * Le `closed_at` est lu depuis `item.closed_at` si exposé, sinon
 * `updated_at` (heuristique : la dernière MAJ d'un closed = la clôture).
 */
export function ItemClosedBanner({ item }) {
  if (!item || item.lifecycle_state !== 'closed') return null;

  // Le BE V4 n'expose pas (encore) un champ `closed_at` dédié — on tombe
  // sur `updated_at` qui correspond pour un item closed (dette M3+).
  const closedAt = item.closed_at || item.updated_at;

  return (
    <div
      role="status"
      className="mb-4 flex items-center gap-3 rounded-[6px] border-l-[3px] border px-4 py-2.5"
      style={{
        background: 'var(--sol-succes-bg)',
        borderColor: 'var(--sol-succes-line)',
        borderLeftColor: 'var(--sol-succes-fg)',
      }}
    >
      <Lock
        size={14}
        aria-label={CLOSED_BANNER_COPY.iconAriaLabel}
        style={{ color: 'var(--sol-succes-fg)', flexShrink: 0 }}
      />
      <div className="flex-1 text-[12.5px] leading-[1.4]" style={{ color: 'var(--sol-ink-700)' }}>
        <span
          className="mr-2 font-mono text-[10px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--sol-succes-fg)' }}
        >
          {CLOSED_BANNER_COPY.title}
        </span>
        <span>
          {CLOSED_BANNER_COPY.textPrefix}{' '}
          <b style={{ color: 'var(--sol-ink-900)', fontWeight: 600 }}>
            {formatDateTimeFR(closedAt)}
          </b>{' '}
          {CLOSED_BANNER_COPY.textSuffix}
        </span>
      </div>
    </div>
  );
}
