/**
 * M2-5.3.A — Formatage de dates FR pour le Centre d'Action V4.
 *
 * Extrait de ItemsTable (M2-5.2) pour réutilisation par EventItem.
 */

/**
 * Date relative courte : « aujourd'hui » / « hier » / « il y a 3 jours »
 * / « 12/05 » au-delà d'une semaine. « — » si date absente ou invalide.
 *
 * M2-5.10.bis clôture (audit code-reviewer P1-3) : `now` injectable
 * pour tests déterministes (cohérent avec `daysSince` qui suit le même
 * pattern).
 */
export function formatRelativeDate(isoDate, now = new Date()) {
  if (!isoDate) return '—';
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return '—';
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

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

/**
 * M2-5.10.B.bis — Nombre de jours écoulés depuis `isoDate`. SoT unique pour
 * « depuis X jours » (BlockerItem, etc.). `now` injectable pour les tests
 * (audit code-reviewer P1-3 — dépendance Date.now() non testable corrigée).
 *
 * Retourne `null` si la date est absente ou invalide ; sinon un entier ≥ 0.
 */
export function daysSince(isoDate, now = new Date()) {
  if (!isoDate) return null;
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return null;
  const diffMs = now.getTime() - date.getTime();
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
}
