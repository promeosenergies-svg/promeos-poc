/**
 * PROMEOS — ActionsSol presenters (Sprint REFONTE-P6 S1 — pilot wrapper)
 *
 * Fonctions pures pour ActionsSol wrapper. ActionsPage reste propriétaire
 * de la data + 3 vues (Table/Kanban/Week) + ActionDetailDrawer 1327 LOC.
 */

import { NBSP, formatFREur } from '../cockpit/sol_presenters';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narrative
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Build kicker "PILOTAGE · ACTIONS · 17 EN COURS · 7 URGENTES"
 */
export function buildActionsKicker({ stats } = {}) {
  const s = stats || {};
  const segments = ['PILOTAGE', 'ACTIONS'];
  if (s.in_progress) segments.push(`${s.in_progress} EN COURS`);
  if (s.overdue) segments.push(`${s.overdue} EN RETARD`);
  return segments.join(` ${NBSP}·${NBSP} `);
}

/**
 * Build narrative 2 lines :
 *   "X actions suivies · Y urgentes · Z € impact cumulé.
 *    Sources : RegOps + BillIntel + Diagnostic conso + Contract radar."
 */
export function buildActionsNarrative({ stats, total } = {}) {
  const s = stats || {};
  const parts = [];
  const totalCount = total || s.total || 0;
  parts.push(`${totalCount} action${totalCount > 1 ? 's' : ''} suivie${totalCount > 1 ? 's' : ''}`);
  if (s.overdue) parts.push(`${s.overdue} en retard`);
  if (s.in_progress) parts.push(`${s.in_progress} en cours`);
  if (s.total_impact) parts.push(`${formatFREur(s.total_impact)} impact cumulé`);

  const intro = parts.join(` ${NBSP}·${NBSP} `) + '.';
  const sources = 'Sources : RegOps + BillIntel + Diagnostic conso + Contract radar. Management by exception — priorisation par impact business.';

  return `${intro} ${sources}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week cards
// ─────────────────────────────────────────────────────────────────────────────

/**
 * interpretWeek — 3 cards sémantiques À regarder / Dérive / Bonne nouvelle.
 */
export function interpretWeek({ actions = [] } = {}) {
  const overdue = actions.filter((a) => isOverdue(a));
  const urgent = actions.filter(
    (a) =>
      !isOverdue(a) &&
      a.due_date &&
      dayDelta(a.due_date) <= 7 &&
      a.statut !== 'done',
  );
  const done = actions.filter((a) => a.statut === 'done');

  // À regarder : action overdue la + impactante
  const topOverdue = overdue
    .slice()
    .sort((a, b) => (b.impact_eur || 0) - (a.impact_eur || 0))[0];

  // Dérive : action urgente cette semaine (impact max)
  const topUrgent = urgent
    .slice()
    .sort((a, b) => (b.impact_eur || 0) - (a.impact_eur || 0))[0];

  const aRegarder = topOverdue
    ? {
        tagKind: 'refuse',
        tagLabel: 'En retard',
        title: topOverdue.titre || 'Action en retard',
        body: topOverdue.site_nom
          ? `${topOverdue.site_nom} — échéance ${formatDate(topOverdue.due_date)}`
          : `Échéance ${formatDate(topOverdue.due_date)}`,
        footerLeft: topOverdue.impact_eur
          ? `Impact ${formatFREur(topOverdue.impact_eur)}`
          : '',
        footerRight: `J+${Math.abs(dayDelta(topOverdue.due_date))}`,
      }
    : {
        tagKind: 'calme',
        tagLabel: 'En retard',
        title: 'Aucune action en retard',
        body: 'Vous êtes dans les temps sur l\'ensemble du portefeuille.',
      };

  const deriveDetectee = topUrgent
    ? {
        tagKind: 'afaire',
        tagLabel: 'Urgent cette semaine',
        title: topUrgent.titre || 'Action urgente',
        body: topUrgent.site_nom
          ? `${topUrgent.site_nom} — échéance ${formatDate(topUrgent.due_date)}`
          : `Échéance ${formatDate(topUrgent.due_date)}`,
        footerLeft: topUrgent.impact_eur
          ? `Impact ${formatFREur(topUrgent.impact_eur)}`
          : '',
        footerRight: `J-${dayDelta(topUrgent.due_date)}`,
      }
    : {
        tagKind: 'calme',
        tagLabel: 'Urgent cette semaine',
        title: 'Aucune action urgente',
        body: 'Pas d\'échéance sous 7 jours à traiter.',
      };

  const bonneNouvelle = {
    tagKind: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: `${done.length} action${done.length > 1 ? 's' : ''} terminée${done.length > 1 ? 's' : ''}`,
    body:
      done.length > 0
        ? 'Continuité des actions clôturées sur la période récente.'
        : 'En attente de clôture sur les actions en cours.',
    footerLeft: urgent.length > 0 ? `${urgent.length} à traiter cette semaine` : '',
  };

  return { aRegarder, deriveDetectee, bonneNouvelle };
}

// ─────────────────────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────────────────────

export function isOverdue(action) {
  if (!action || !action.due_date || action.statut === 'done') return false;
  return dayDelta(action.due_date) < 0;
}

export function dayDelta(isoDate) {
  if (!isoDate) return 0;
  try {
    const d = new Date(isoDate);
    const now = new Date();
    return Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  } catch (_) {
    return 0;
  }
}

function formatDate(isoDate) {
  if (!isoDate) return '—';
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
  } catch (_) {
    return '—';
  }
}
