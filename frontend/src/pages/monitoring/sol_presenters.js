/**
 * PROMEOS — Monitoring Performance Sol presenters (Lot 1.3)
 *
 * Helpers purs pour MonitoringSol — transformation des alertes monitoring
 * + historique consommation vers props Sol.
 *
 * APIs consommées :
 *   getMonitoringAlerts(siteId=null, status=null, limit)
 *     → shape : [{id, alert_type, severity, site_id, explanation,
 *                 recommended_action, estimated_impact_eur, status, ...}]
 *     ⚠ Appel org-level : utiliser `?org_id=${orgId}` via l'override.
 *   getBillingCompareMonthly({months:12}) → pour courbe consommation kWh
 *   getSites({org_id}) → nb sites + conso_kwh_an pour baseline
 *
 * Zéro endpoint dédié monitoring-summary, calculs agrégés côté frontend.
 */
import {
  NBSP,
  formatFR,
  formatFREur,
  computeDelta,
  freshness,
} from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildMonitoringKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `Monitoring performance · ${orgName}${sitesSuffix}`;
}

export function buildMonitoringNarrative({ alertsCount, totalImpact, activeSites, totalSites } = {}) {
  if (activeSites == null && alertsCount == null) {
    return "Le monitoring s'active dès qu'un site reçoit 12 mois de télérelève. Sol calibre la baseline de référence automatiquement.";
  }

  if (alertsCount === 0) {
    return `Tous vos sites respectent leur baseline DJU. Aucune dérive active${activeSites ? ` sur ${activeSites}${NBSP}site${activeSites > 1 ? 's' : ''} surveillés` : ''}.`;
  }

  const impactClause = totalImpact > 0
    ? ` · impact annualisé estimé ${formatFREur(totalImpact, 0)}/an`
    : '';
  return `${alertsCount}${NBSP}dérive${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''} détectée${alertsCount > 1 ? 's' : ''}${impactClause}. Sol identifie les causes probables et propose des plans d'action.`;
}

export function buildMonitoringSubNarrative({ totalSites, coverage } = {}) {
  const parts = [];
  if (coverage != null) parts.push(`${coverage}${NBSP}% de couverture monitoring`);
  if (totalSites > 0) parts.push(`baseline DJU normalisée Météo-France`);
  if (parts.length === 0) return "Sources : EMS télérelève + Météo-France + règles métier services/monitoring_rules.py.";
  return `${parts.join(' · ')}. Sources : EMS télérelève + Météo-France + règles métier.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretMonitoringSites({ activeSites, totalSites } = {}) {
  if (!totalSites) return "Aucun site dans votre portefeuille.";
  if (activeSites === totalSites) return `Couverture complète · baseline ajustée DJU sur ${totalSites}${NBSP}site${totalSites > 1 ? 's' : ''}.`;
  return `${activeSites}/${totalSites} sites instrumentés · ${totalSites - activeSites} à calibrer.`;
}

export function interpretMonitoringAlerts({ alertsCount, bySeverity, topAlert } = {}) {
  if (!alertsCount) return "Aucune dérive active sur les 30 derniers jours.";
  const parts = [];
  if (bySeverity?.critical > 0) parts.push(`${bySeverity.critical}${NBSP}critique${bySeverity.critical > 1 ? 's' : ''}`);
  if (bySeverity?.high > 0) parts.push(`${bySeverity.high}${NBSP}haute${bySeverity.high > 1 ? 's' : ''}`);
  if (bySeverity?.warning > 0) parts.push(`${bySeverity.warning}${NBSP}vigilance`);
  const severities = parts.join(' · ');
  if (topAlert?.explanation) {
    const short = topAlert.explanation.length > 80
      ? topAlert.explanation.slice(0, 80) + '…'
      : topAlert.explanation;
    return `${severities}. Plus récente : ${short}`;
  }
  return severities || `${alertsCount} dérives à traiter.`;
}

export function interpretMonitoringDrift({ totalImpact, topContributors } = {}) {
  if (!totalImpact) return "Aucun impact financier matérialisé.";
  const drivers = (topContributors || []).slice(0, 2).map((c) => c.site_nom || `site ${c.site_id}`);
  if (drivers.length === 2) {
    return `${formatFREur(totalImpact, 0)}/an en jeu · top contributeurs : ${drivers[0]} et ${drivers[1]}.`;
  }
  if (drivers.length === 1) {
    return `${formatFREur(totalImpact, 0)}/an en jeu · contributeur principal : ${drivers[0]}.`;
  }
  return `Impact cumulé estimé ${formatFREur(totalImpact, 0)}/an si non-traité.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Computations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Agrège les alertes par severity + trie par impact décroissant pour top.
 */
export function summarizeAlerts(alerts) {
  if (!Array.isArray(alerts)) {
    return { total: 0, bySeverity: {}, topImpact: [], totalImpact: 0, topAlert: null };
  }
  const bySeverity = alerts.reduce((acc, a) => {
    const sev = a?.severity || 'info';
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {});
  const totalImpact = alerts.reduce((sum, a) => sum + (Number(a?.estimated_impact_eur) || 0), 0);
  const topImpact = [...alerts]
    .filter((a) => (Number(a?.estimated_impact_eur) || 0) > 0)
    .sort((a, b) => (Number(b.estimated_impact_eur) || 0) - (Number(a.estimated_impact_eur) || 0));
  return {
    total: alerts.length,
    bySeverity,
    topImpact,
    totalImpact: Math.round(totalImpact),
    topAlert: alerts.find((a) => a?.severity === 'critical') || alerts[0] || null,
  };
}

/**
 * Enrichit les alertes avec site_nom depuis la liste sites.
 */
export function enrichAlertsWithSites(alerts, sites) {
  if (!Array.isArray(alerts)) return [];
  const siteMap = new Map((sites || []).map((s) => [s.id, s.nom || s.name]));
  return alerts.map((a) => ({
    ...a,
    site_nom: siteMap.get(a.site_id) || `site ${a.site_id}`,
  }));
}

/**
 * Convertit getBillingCompareMonthly().months → data SolTrajectoryChart.
 * Retourne [{month, value}] en kWh du current_year (fallback previous si manquant).
 */
export function adaptCompareToTrajectory(compare) {
  if (!compare || !Array.isArray(compare.months)) return [];
  const MONTH_KEYS = {
    Janv: '2026-01', Fév: '2026-02', Mars: '2026-03', Avr: '2026-04',
    Mai: '2026-05', Juin: '2026-06', Juil: '2026-07', Août: '2026-08',
    Sept: '2026-09', Oct: '2026-10', Nov: '2026-11', Déc: '2026-12',
  };
  return compare.months
    .map((m) => {
      const kwh = m.current_kwh ?? m.previous_kwh;
      if (kwh == null) return null;
      return {
        month: MONTH_KEYS[m.label] || m.label,
        value: Math.round((Number(kwh) || 0) / 1000), // kWh → MWh
      };
    })
    .filter(Boolean);
}

/**
 * Calcule la baseline comme moyenne des 12 mois courants.
 */
export function computeBaseline(trajectoryData) {
  if (!Array.isArray(trajectoryData) || trajectoryData.length === 0) return null;
  const sum = trajectoryData.reduce((s, p) => s + (Number(p.value) || 0), 0);
  return Math.round(sum / trajectoryData.length);
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards Monitoring
// ─────────────────────────────────────────────────────────────────────────────

export function buildMonitoringWeekCards({ alerts = [], onNavigateSite = null } = {}) {
  const cards = [];

  const sorted = [...alerts].sort(
    (a, b) => (Number(b.estimated_impact_eur) || 0) - (Number(a.estimated_impact_eur) || 0)
  );
  const open = sorted.filter((a) => a?.status === 'open' || a?.status === 'active' || !a?.status);
  const resolved = sorted.filter((a) => a?.status === 'resolved' || a?.status === 'closed');

  // Card 1 À regarder : alerte avec impact max
  const urgent = open[0];
  if (urgent) {
    const impact = Number(urgent.estimated_impact_eur) || 0;
    cards.push({
      id: `alert-${urgent.id}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: `${labelAlertType(urgent.alert_type)} · ${urgent.site_nom || 'site ' + urgent.site_id}`,
      body: urgent.explanation || 'Dérive détectée sur la consommation.',
      footerLeft: impact > 0 ? `impact ${formatFREur(impact, 0)}/an` : '',
      footerRight: urgent.severity === 'critical' ? 'Critique' : urgent.severity === 'high' ? 'Haute' : '⌘K',
      onClick: onNavigateSite ? () => onNavigateSite(urgent.site_id) : undefined,
    });
  } else {
    cards.push(businessErrorFallback('monitoring.no_drift', cards.length));
  }

  // Card 2 À faire : 2ème alerte persistante
  const next = open[1];
  if (next) {
    const impact = Number(next.estimated_impact_eur) || 0;
    cards.push({
      id: `next-${next.id}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: `${labelAlertType(next.alert_type)} · ${next.site_nom || 'site ' + next.site_id}`,
      body: next.recommended_action || next.explanation || '',
      footerLeft: impact > 0 ? `récupération ${formatFREur(impact, 0)}/an` : '',
      footerRight: 'Plan requis',
      onClick: onNavigateSite ? () => onNavigateSite(next.site_id) : undefined,
    });
  } else {
    cards.push(businessErrorFallback('monitoring.no_drift', cards.length));
  }

  // Card 3 Bonne nouvelle : alerte résolue récente
  const lastResolved = resolved[0];
  if (lastResolved) {
    const impact = Number(lastResolved.estimated_impact_eur) || 0;
    cards.push({
      id: `resolved-${lastResolved.id}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `Dérive résolue · ${lastResolved.site_nom || 'site ' + lastResolved.site_id}`,
      body: `${labelAlertType(lastResolved.alert_type)} traitée.`,
      footerLeft: impact > 0 ? `${formatFREur(impact, 0)}/an économisés` : 'cas clos',
      footerRight: '✓ Clean',
      onClick: onNavigateSite ? () => onNavigateSite(lastResolved.site_id) : undefined,
    });
  } else {
    cards.push(businessErrorFallback('monitoring.no_drift', cards.length));
  }

  return cards.slice(0, 3);
}

const ALERT_TYPE_LABELS = {
  low_load_factor: 'Facteur de charge faible',
  high_load_factor: 'Facteur de charge élevé',
  baseline_drift: 'Dérive baseline',
  night_baseline: 'Talon nocturne anormal',
  weekend_consumption: 'Consommation week-end',
  peak_exceeded: 'Dépassement puissance souscrite',
  off_hours: 'Consommation hors horaires',
  unusual_spike: 'Pic anormal',
};

function labelAlertType(type) {
  return ALERT_TYPE_LABELS[type] || 'Dérive détectée';
}

// Re-exports
export { formatFR, formatFREur, computeDelta, freshness };
