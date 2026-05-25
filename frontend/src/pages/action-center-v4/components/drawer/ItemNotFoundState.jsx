/**
 * Action Center V4 P0 fix (2026-05-25) — fallback FR rendu dans le drawer
 * quand l'item est introuvable, supprimé, cross-org interdit, payload null
 * ou en erreur réseau. Avant ce composant le drawer affichait un panneau
 * blanc silencieux (audit deep §3.3 P0-2).
 *
 * Utilisé par ItemDetailDrawer (état) et DrawerErrorBoundary (catch
 * d'erreurs runtime React). Aucun nouveau menu, fallback unique vers le
 * hub canonique /centre-action (route V4).
 */
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';

import { DRAWER_COPY } from '../../constants/drawer';

export function ItemNotFoundState({ variant = 'not_found', onClose, onRetry }) {
  const { title, text } = _resolveCopy(variant);
  return (
    <div
      className="flex flex-col items-center justify-center text-center px-6 py-10"
      data-testid="drawer-item-not-found"
      data-variant={variant}
      role="alert"
    >
      <div
        className="mb-3 flex items-center justify-center w-12 h-12 rounded-full bg-amber-50 text-amber-600"
        aria-hidden="true"
      >
        <AlertCircle size={24} />
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 max-w-md mb-5">{text}</p>
      <div className="flex items-center gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            data-testid="drawer-item-not-found-retry"
          >
            <RefreshCw size={14} aria-hidden="true" />
            {DRAWER_COPY.retryCta}
          </button>
        )}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            data-testid="drawer-item-not-found-cta"
          >
            <ArrowLeft size={14} aria-hidden="true" />
            {DRAWER_COPY.returnToHubCta}
          </button>
        )}
      </div>
    </div>
  );
}

function _resolveCopy(variant) {
  switch (variant) {
    case 'network_error':
      return {
        title: DRAWER_COPY.networkErrorTitle,
        text: DRAWER_COPY.networkErrorText,
      };
    case 'unexpected':
      return {
        title: DRAWER_COPY.unexpectedErrorTitle,
        text: DRAWER_COPY.unexpectedErrorText,
      };
    case 'not_found':
    default:
      return {
        title: DRAWER_COPY.notFoundTitle,
        text: DRAWER_COPY.notFoundText,
      };
  }
}
