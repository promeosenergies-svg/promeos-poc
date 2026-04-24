/**
 * PROMEOS — NotificationsSol presenters (Sprint REFONTE-P6 S1 — pilot wrapper)
 *
 * Fonctions pures pour NotificationsSol wrapper.
 * NotificationsPage reste propriétaire de la data. Ces helpers produisent
 * uniquement le narratif SolPageHeader + les 3 SolWeekCard sémantiques.
 *
 * Shape events consommée (provient de NotificationsPage state `events`) :
 *   {
 *     id, title, message,
 *     source_type: 'compliance'|'billing'|'purchase'|'consumption'|'action_hub',
 *     severity: 'critical'|'warn'|'info',
 *     status: 'new'|'read'|'dismissed',
 *     estimated_impact_eur,
 *     due_date, deeplink_path
 *   }
 */

import { NBSP } from '../cockpit/sol_presenters';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narrative (SolPageHeader)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Build kicker "PILOTAGE · ALERTES · 5 CRITIQUES · 11 ATTENTION"
 */
export function buildNotificationsKicker({ liveSummary } = {}) {
  const byS = (liveSummary && liveSummary.by_severity) || {};
  const crit = byS.critical || 0;
  const warn = byS.warn || 0;
  const segments = ['PILOTAGE', 'ALERTES'];
  if (crit > 0) segments.push(`${crit} CRITIQUE${crit > 1 ? 'S' : ''}`);
  if (warn > 0) segments.push(`${warn} ATTENTION`);
  return segments.join(` ${NBSP}·${NBSP} `);
}

/**
 * Build narrative 2 lines :
 *   "X alertes actives · Y nouvelles · Z impact cumulé €.
 *    Sources 5 briques : Conformité · Facturation · Achats · Consommation · Actions.
 *    Dédup SHA-256 · dernière synchro il y a N min."
 */
export function buildNotificationsNarrative({ events = [], lastSync } = {}) {
  const total = events.length;
  const newCount = events.filter((e) => e.status === 'new').length;
  const impact = events.reduce((s, e) => s + (e.estimated_impact_eur || 0), 0);

  const parts = [];
  parts.push(`${total} alerte${total > 1 ? 's' : ''} active${total > 1 ? 's' : ''}`);
  if (newCount > 0) parts.push(`${newCount} nouvelle${newCount > 1 ? 's' : ''}`);
  if (impact > 0) parts.push(`impact cumulé ${formatFREurCompact(impact)}`);

  const intro = parts.join(` ${NBSP}·${NBSP} `) + '.';
  const sources = `Sources 5 briques : Conformité ${NBSP}·${NBSP} Facturation ${NBSP}·${NBSP} Achats ${NBSP}·${NBSP} Consommation ${NBSP}·${NBSP} Actions.`;
  const sync = lastSync ? `Dernière synchro à ${formatSyncTime(lastSync)}.` : 'Dédup SHA-256 actif.';

  return `${intro} ${sources} ${sync}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week cards (3 cards sémantiques)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * interpretWeek — construit les 3 SolWeekCard narratifs sémantiques.
 *
 * @returns {{ aRegarder, deriveDetectee, bonneNouvelle }}
 */
export function interpretWeek({ events = [] } = {}) {
  const criticals = events.filter((e) => e.severity === 'critical' && e.status !== 'dismissed');
  const warns = events.filter((e) => e.severity === 'warn' && e.status !== 'dismissed');
  const resolved = events.filter((e) => e.status === 'read' || e.status === 'dismissed');

  // À regarder = alerte critique avec le + gros impact €
  const topCritical = criticals
    .slice()
    .sort(
      (a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0),
    )[0];

  // Dérive détectée = anomalie conso/billing la + récente
  const topDrift = events
    .filter(
      (e) =>
        (e.source_type === 'consumption' || e.source_type === 'billing') &&
        e.status !== 'dismissed',
    )
    .slice()
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))[0];

  // Bonne nouvelle = alertes résolues ce mois
  const aRegarder = topCritical
    ? {
        tagKind: 'afaire',
        tagLabel: 'À regarder',
        title: topCritical.title || 'Alerte critique',
        body: topCritical.message
          ? truncate(topCritical.message, 120)
          : `Source : ${topCritical.source_type || 'n/a'}`,
        footerLeft: topCritical.estimated_impact_eur
          ? `Impact ${formatFREurCompact(topCritical.estimated_impact_eur)}`
          : '',
        footerRight: topCritical.deeplink_path ? 'ouvrir →' : '',
        onClick: topCritical.deeplink_path
          ? () => window.location.assign(topCritical.deeplink_path)
          : undefined,
      }
    : {
        tagKind: 'calme',
        tagLabel: 'À regarder',
        title: 'Aucune alerte critique',
        body: 'Votre portefeuille est sous contrôle sur les 7 derniers jours.',
        footerLeft: '',
        footerRight: '',
      };

  const deriveDetectee = topDrift
    ? {
        tagKind: 'attention',
        tagLabel: 'Dérive détectée',
        title: topDrift.title || 'Anomalie détectée',
        body: topDrift.message
          ? truncate(topDrift.message, 120)
          : `Source : ${topDrift.source_type}`,
        footerLeft: topDrift.estimated_impact_eur
          ? `Impact ${formatFREurCompact(topDrift.estimated_impact_eur)}`
          : '',
        footerRight: topDrift.deeplink_path ? 'ouvrir →' : '',
        onClick: topDrift.deeplink_path
          ? () => window.location.assign(topDrift.deeplink_path)
          : undefined,
      }
    : {
        tagKind: 'calme',
        tagLabel: 'Dérive détectée',
        title: 'Aucune dérive consommation ou facturation',
        body: 'Les moteurs shadow v4.2 et diagnostic conso ne détectent rien d\'anormal.',
        footerLeft: '',
        footerRight: '',
      };

  const bonneNouvelle = {
    tagKind: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: `${resolved.length} alerte${resolved.length > 1 ? 's' : ''} traitée${resolved.length > 1 ? 's' : ''}`,
    body:
      resolved.length > 0
        ? 'Historique à jour. Les sources 5 briques restent en veille.'
        : 'En attente de retours sur les alertes en cours.',
    footerLeft: warns.length > 0 ? `${warns.length} en attention` : '',
    footerRight: '',
  };

  return { aRegarder, deriveDetectee, bonneNouvelle };
}

// ─────────────────────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────────────────────

export function formatFREurCompact(value) {
  if (value == null || !Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(abs >= 10000 ? 0 : 1).replace('.', ',')}${NBSP}k€`;
  }
  return `${Math.round(value)}${NBSP}€`;
}

function formatSyncTime(date) {
  try {
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (_) {
    return '';
  }
}

function truncate(s, n) {
  if (!s) return '';
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
