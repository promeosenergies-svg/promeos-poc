/**
 * Mirror JS des types SolEventCard backend (doctrine v1.1 §10).
 *
 * Source de vérité : `backend/services/event_bus/types.py` (Python frozen
 * dataclass). Ce fichier expose les const enums JS pour validation côté
 * frontend (autocomplete, tests source-guard).
 *
 * Sprint 2 Vague C ét11 — chantier α moteur événements MVP. Le frontend
 * consomme encore `NarrativeWeekCard` (transition via `to_narrative_week_cards`
 * backend). Vague C ét12+ ajoutera le composant `<SolEventCard>` natif qui
 * exposera `source.system`, `source.confidence`, `action.owner_role`.
 */

/** 9 event_types canoniques (doctrine §10). */
export const EVENT_TYPES = Object.freeze([
  'consumption_drift',
  'billing_anomaly',
  'compliance_deadline',
  'contract_renewal',
  'market_window',
  'data_quality_issue',
  'flex_opportunity',
  'asset_registry_issue',
  'action_overdue',
]);

/** 4 niveaux severity (doctrine §10). */
export const EVENT_SEVERITIES = Object.freeze(['info', 'watch', 'warning', 'critical']);

/** Unités impact (doctrine §10). */
export const EVENT_UNITS = Object.freeze(['€', 'kWh', 'MWh', 'kW', 'kVA', 'kgCO2e', 'days', '%']);

/** Périodes impact (doctrine §10). */
export const EVENT_PERIODS = Object.freeze([
  'day',
  'week',
  'month',
  'year',
  'contract',
  'deadline',
]);

/** Systèmes source (doctrine §10). */
export const EVENT_SOURCE_SYSTEMS = Object.freeze([
  'Enedis',
  'GRDF',
  'invoice',
  'GTB',
  'IoT',
  'RegOps',
  'EPEX',
  'manual',
  'benchmark',
]);

/** Niveaux confidence (doctrine §10 + §7.1 contrat data). */
export const EVENT_CONFIDENCES = Object.freeze(['high', 'medium', 'low']);

/**
 * Statuts fraîcheur data (doctrine §7.2 statuts obligatoires).
 * Frontend doit afficher un badge visuel pour chaque statut non-`fresh`
 * (« estimé » ambré, « incomplet » jaune, « stale » gris, « démo » bleu).
 *
 * SoT canonique : `backend/services/event_bus/types.py::EventFreshnessStatus`.
 */
export const EVENT_FRESHNESS_STATUSES = Object.freeze([
  'fresh',
  'stale',
  'estimated',
  'incomplete',
  'demo',
]);

/** Roles owner action (doctrine §10). */
export const EVENT_OWNER_ROLES = Object.freeze([
  'DAF',
  'Energy Manager',
  'Site Manager',
  'Admin',
  'Operator',
]);

/**
 * Mapping severity → tone visuel (cohérent avec SolWeekCards CARD_TYPE_CONFIG).
 * `critical`+`warning` → todo (urgent), `watch` → watch, `info` → good_news.
 *
 * SoT canonique : `backend/services/event_bus/types.py::SEVERITY_TO_CARD_TYPE`.
 * Toute évolution doit être faite côté backend en premier puis mirror ici.
 */
export const SEVERITY_TO_CARD_TYPE = Object.freeze({
  critical: 'todo',
  warning: 'todo',
  watch: 'watch',
  info: 'good_news',
});

/** Helper validation : True si event est conforme schéma §10. */
export function isValidEvent(event) {
  if (!event || typeof event !== 'object') return false;
  return (
    typeof event.id === 'string' &&
    EVENT_TYPES.includes(event.event_type) &&
    EVENT_SEVERITIES.includes(event.severity) &&
    typeof event.title === 'string' &&
    typeof event.narrative === 'string' &&
    event.impact &&
    EVENT_UNITS.includes(event.impact.unit) &&
    EVENT_PERIODS.includes(event.impact.period) &&
    event.source &&
    EVENT_SOURCE_SYSTEMS.includes(event.source.system) &&
    EVENT_CONFIDENCES.includes(event.source.confidence) &&
    EVENT_FRESHNESS_STATUSES.includes(event.source.freshness_status || 'fresh') &&
    event.action &&
    typeof event.action.label === 'string' &&
    typeof event.action.route === 'string' &&
    event.linked_assets &&
    typeof event.linked_assets.org_id === 'number'
  );
}
