/**
 * M2-5.3.A — Formatage de dates FR pour le Centre d'Action V4.
 *
 * Extrait de ItemsTable (M2-5.2) pour réutilisation par EventItem.
 */

/**
 * Date relative courte : « aujourd'hui » / « hier » / « il y a 3 jours »
 * / « 12/05 » au-delà d'une semaine. « — » si date absente ou invalide.
 */
export function formatRelativeDate(isoDate) {
  if (!isoDate) return '—';
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return '—';
  const diffDays = Math.floor((new Date() - date) / (1000 * 60 * 60 * 24));

  if (diffDays <= 0) return "aujourd'hui";
  if (diffDays === 1) return 'hier';
  if (diffDays < 7) return `il y a ${diffDays} jours`;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
}

/**
 * Date + heure complète FR (utilisée en tooltip). « — » si absente/invalide.
 */
export function formatDateTimeFR(isoDate) {
  if (!isoDate) return '—';
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
