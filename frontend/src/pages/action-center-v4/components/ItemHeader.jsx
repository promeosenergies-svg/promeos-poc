import { DRAWER_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { LifecycleBadge } from './LifecycleBadge';

/**
 * M2-5.3.A — En-tête du drawer : titre + badge d'état + métadonnées.
 *
 * Aucune action (la transition lifecycle arrive en M2-5.4). Gère les états
 * loading (skeleton) et error / item absent.
 */
export function ItemHeader({ item, loading, error }) {
  if (loading) {
    return (
      <header>
        <div className="mb-2 h-7 w-2/3 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-gray-200" />
      </header>
    );
  }

  if (error || !item) {
    return (
      <header>
        <p className="text-sm text-red-700">{DRAWER_COPY.headerError}</p>
      </header>
    );
  }

  return (
    <header>
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xl font-semibold text-gray-900">{item.title}</h2>
        <LifecycleBadge state={item.lifecycle_state} />
      </div>

      {item.description && <p className="mt-2 text-sm text-gray-600">{item.description}</p>}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
        <dt>{DRAWER_COPY.domainLabel}</dt>
        <dd className="text-gray-700">{item.domain || '—'}</dd>

        <dt>{DRAWER_COPY.kindLabel}</dt>
        <dd className="text-gray-700">{item.kind || '—'}</dd>

        <dt>{DRAWER_COPY.createdAtLabel}</dt>
        <dd className="text-gray-700">{formatDateTimeFR(item.created_at)}</dd>

        <dt>{DRAWER_COPY.updatedAtLabel}</dt>
        <dd className="text-gray-700">{formatDateTimeFR(item.updated_at)}</dd>
      </dl>
    </header>
  );
}
