/**
 * date.js — Helpers date FR partagés (refonte WOW Étape 2.bis · 29/04/2026).
 *
 * Centralise les utilitaires date utilisés à travers les pages Cockpit
 * (Pilotage + Décision + futures pages Sol). Évite la duplication signalée
 * par /simplify P1 audit fin Étape 2 (CockpitPilotage:96 ↔ CockpitDecision:42).
 *
 * Tous les formats sont en français (locale fr-FR).
 */

const MS_PER_DAY = 86_400_000;

/** Numéro de semaine ISO 8601 (lundi = début de semaine).
 *  Référence : ISO 8601 §3.2.1.4. */
export function getIsoWeek(d = new Date()) {
  const date = new Date(d);
  date.setHours(0, 0, 0, 0);
  // Décalage pour que le jeudi de la semaine en cours détermine l'année ISO.
  date.setDate(date.getDate() + 4 - (date.getDay() || 7));
  const yearStart = new Date(date.getFullYear(), 0, 1);
  return Math.ceil(((date - yearStart) / MS_PER_DAY + 1) / 7);
}

/** Temps relatif en français : "il y a 2 h", "il y a 3 j", "à l'instant". */
export function relativeTime(iso) {
  if (!iso) return '—';
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (diffMin < 1) return "à l'instant";
  if (diffMin < 60) return `il y a ${diffMin} min`;
  const h = Math.round(diffMin / 60);
  if (h < 24) return `il y a ${h} h`;
  const d = Math.round(h / 24);
  return `il y a ${d} j`;
}

/** Nombre de jours entre maintenant et une date ISO future (positif=futur). */
export function daysUntil(iso) {
  if (!iso) return null;
  return Math.ceil((new Date(iso) - new Date()) / MS_PER_DAY);
}

/** Date FR longue ex. "lundi 29 avril". */
const FR_LONG = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});
export const fmtDateLong = (d = new Date()) => FR_LONG.format(d);

/** Date FR courte ex. "29/04". */
const FR_SHORT = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: '2-digit',
});
export const fmtDateShort = (iso) => (iso ? FR_SHORT.format(new Date(iso)) : '—');
