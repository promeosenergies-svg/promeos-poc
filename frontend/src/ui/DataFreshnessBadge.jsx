/**
 * DataFreshnessBadge — badge compact "Données · il y a Xh" (header dashboard).
 *
 * Distinct de `FreshnessIndicator` qui est dimensionné pour le détail site
 * (last_reading + last_invoice + recommendations). Ici on affiche juste la
 * fraîcheur globale du compute backend pour le header.
 *
 * Props :
 *   computedAt  : ISO string (ex. compliance_computed_at)
 *   sourceLabel : 'EMS' | 'Facture' | 'Estimé' (optionnel)
 */
import { Clock } from 'lucide-react';

function formatRelative(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffH = Math.round(diffMs / (1000 * 60 * 60));
    if (diffH < 1) return "à l'instant";
    if (diffH < 24) return `il y a ${diffH}h`;
    const diffD = Math.round(diffH / 24);
    if (diffD < 7) return `il y a ${diffD}j`;
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
  } catch {
    return null;
  }
}

function formatAbsolute(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return null;
  }
}

export default function DataFreshnessBadge({ computedAt, sourceLabel }) {
  const relative = formatRelative(computedAt);
  const absolute = formatAbsolute(computedAt);
  if (!relative) return null;

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-50 text-gray-600 text-[11px] font-medium border border-gray-200"
      title={
        absolute
          ? `Dernière mise à jour : ${absolute}${sourceLabel ? ` · Source : ${sourceLabel}` : ''}`
          : ''
      }
      data-testid="data-freshness-badge"
    >
      <Clock size={10} aria-hidden="true" />
      Données · {relative}
      {sourceLabel && <span className="text-gray-400">· {sourceLabel}</span>}
    </span>
  );
}
