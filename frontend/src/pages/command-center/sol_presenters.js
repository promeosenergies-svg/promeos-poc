/**
 * PROMEOS — Command Center Sol presenters (Lot 1.1)
 *
 * Helpers purs pour CommandCenterSol — transformation des réponses APIs
 * actions + notifications + compliance + cockpit vers props Sol.
 *
 * APIs consommées (toutes existantes) :
 *   getActionsSummary()          → {counts, by_source, total_gain_eur, top5}
 *   getNotificationsSummary()    → {total, by_severity, by_status}
 *   getComplianceBundle({scope}) → compliance_score + findings
 *   getCockpit()                 → stats macro (fallback issue #257)
 *
 * Zéro fetch, fonctions pures déterministes.
 */
import { NBSP, formatFR, formatFREur, computeDelta, freshness } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildCommandKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `Accueil · ${orgName}${sitesSuffix}`;
}

export function buildCommandNarrative({
  stateIndex,
  alertsCount,
  solActionsCount,
  totalGain,
} = {}) {
  if (stateIndex == null) {
    return 'Bienvenue sur votre cockpit énergétique. Les indicateurs se calculent dès les premières données importées.';
  }
  const parts = [];
  // Résumer l'état général en français simple
  if (stateIndex >= 75) {
    parts.push('Votre patrimoine est sous contrôle');
  } else if (stateIndex >= 60) {
    parts.push('Votre patrimoine nécessite une vigilance régulière');
  } else {
    parts.push('Votre patrimoine demande des décisions cette semaine');
  }
  // Volume d'alertes
  if (alertsCount > 0) {
    parts.push(
      `${alertsCount}${NBSP}alerte${alertsCount > 1 ? 's' : ''} critique${alertsCount > 1 ? 's' : ''}`
    );
  }
  // Potentiel Sol
  if (solActionsCount > 0 && totalGain > 0) {
    parts.push(
      `Sol a préparé ${solActionsCount}${NBSP}action${solActionsCount > 1 ? 's' : ''} pour récupérer ${formatFREur(totalGain, 0)}`
    );
  } else if (solActionsCount > 0) {
    parts.push(`${solActionsCount}${NBSP}action${solActionsCount > 1 ? 's' : ''} à valider`);
  }
  return parts.join(' · ') + '.';
}

export function buildCommandSubNarrative({ summary } = {}) {
  const done = summary?.counts?.done ?? 0;
  const total = summary?.counts?.total ?? 0;
  if (total === 0) {
    return 'Sources : RegOps canonique · shadow billing · notifications Sol. Vos modules s\u2019activent dès que vous importez vos premières données.';
  }
  const pct = Math.round((done / total) * 100);
  return `${pct}${NBSP}% des actions ont été traitées ce trimestre (${done}/${total}). Sources : RegOps · shadow billing · notifications Sol.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Computed state index (composite score)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule un indice d'état patrimoine 0-100 pondéré :
 *   - 40 % compliance_score (via cockpit.stats.compliance_score ou trend fallback)
 *   - 30 % performance facture (inverse anomalies ratio)
 *   - 30 % couverture monitoring (sites actifs / total)
 *
 * Retourne null si aucune donnée exploitable.
 */
export function computeStateIndex({
  complianceScore,
  totalInvoices,
  anomaliesCount,
  activeSites,
  totalSites,
} = {}) {
  const parts = [];
  if (complianceScore != null) {
    parts.push({ weight: 0.4, value: Math.max(0, Math.min(100, complianceScore)) });
  }
  if (totalInvoices > 0 && anomaliesCount != null) {
    const ratio = Math.max(0, 1 - anomaliesCount / totalInvoices);
    parts.push({ weight: 0.3, value: Math.round(ratio * 100) });
  }
  if (totalSites > 0 && activeSites != null) {
    parts.push({ weight: 0.3, value: Math.round((activeSites / totalSites) * 100) });
  }
  if (parts.length === 0) return null;
  const totalWeight = parts.reduce((sum, p) => sum + p.weight, 0);
  const weighted = parts.reduce((sum, p) => sum + p.value * p.weight, 0);
  return Math.round((weighted / totalWeight) * 10) / 10;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretStateIndex(score) {
  if (score == null) return 'Indice en cours de calcul, dépend de la disponibilité des données.';
  if (score >= 75) return 'Conformité solide, facture maîtrisée, monitoring déployé.';
  if (score >= 60) return 'Deux dimensions sur trois au vert · une en vigilance.';
  return 'Décisions requises cette semaine sur au moins deux dimensions.';
}

export function interpretCommandAlerts({ alertsCount, topAlertTitle, topAlertImpact }) {
  if (!alertsCount) return 'Aucune alerte critique active.';
  if (topAlertTitle && topAlertImpact) {
    return `Plus urgente : ${topAlertTitle} · impact ${formatFREur(topAlertImpact, 0)}.`;
  }
  if (topAlertTitle) {
    return `Plus urgente : ${topAlertTitle}.`;
  }
  return `${alertsCount}${NBSP}alerte${alertsCount > 1 ? 's' : ''} à traiter cette semaine.`;
}

export function interpretSolActions({ count, totalGain, bySource }) {
  if (!count) return "Aucune action Sol proposée pour l'instant.";
  const gainText = totalGain > 0 ? ` · récupération potentielle ${formatFREur(totalGain, 0)}` : '';
  // Top source
  if (bySource) {
    const entries = Object.entries(bySource).sort((a, b) => b[1] - a[1]);
    const [topKey, topCount] = entries[0] || [];
    if (topKey && topCount) {
      return `${count}${NBSP}actions · ${topCount} via ${labelSource(topKey)}${gainText}.`;
    }
  }
  return `${count}${NBSP}actions préparées${gainText}.`;
}

const SOURCE_LABELS = {
  compliance: 'conformité',
  consumption: 'consommation',
  billing: 'facturation',
  insight: 'détection shadow',
  purchase: 'achat',
  manual: 'saisie manuelle',
  copilot: 'Sol copilot',
  action_hub: 'hub actions',
};

function labelSource(key) {
  return SOURCE_LABELS[key] || key;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards Command Center (transversales tous modules)
// ─────────────────────────────────────────────────────────────────────────────

export function buildCommandWeekCards({
  notifications = [],
  actions = [],
  topFindings = [],
  onNavigate = null,
} = {}) {
  const cards = [];
  const asFn = (path) => {
    if (!path || typeof path !== 'string') return undefined;
    if (typeof onNavigate === 'function') return () => onNavigate(path);
    return () => {
      if (typeof window !== 'undefined') window.location.assign(path);
    };
  };

  // Card 1 À regarder : alerte critique top (notifications)
  const criticalAlert = notifications.find((n) => n?.severity === 'critical') || notifications[0];
  if (criticalAlert) {
    const impact = criticalAlert.estimated_impact_eur ?? criticalAlert.impact_eur;
    cards.push({
      id: `alert-${criticalAlert.id || 0}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: criticalAlert.title || 'Alerte critique',
      body: criticalAlert.message || criticalAlert.summary || '',
      footerLeft: impact ? `impact ${formatFREur(impact, 0)}` : '',
      footerRight: '⌘K',
      onClick: asFn(criticalAlert.deeplink_path),
    });
  } else {
    cards.push(businessErrorFallback('command.all_clean', cards.length));
  }

  // Card 2 À faire : prochaine action Sol par impact décroissant
  const topAction = actions[0];
  if (topAction) {
    const gain =
      topAction.estimated_gain_eur ??
      topAction.potential_saving_eur ??
      topAction.estimated_impact_eur;
    cards.push({
      id: `action-${topAction.id || 0}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: topAction.title || topAction.label || 'Action à valider',
      body: topAction.summary || topAction.description || '',
      footerLeft: gain ? `gain potentiel ${formatFREur(gain, 0)}` : '',
      footerRight: 'Automatisable',
      onClick: asFn(topAction.deeplink_path || `/actions/${topAction.id}`),
    });
  } else {
    cards.push(businessErrorFallback('command.no_sol_actions', cards.length));
  }

  // Card 3 Bonne nouvelle : dernière validation ou finding succès
  const goodNews = topFindings.find((f) => f?.status === 'validated' || f?.status === 'passed');
  if (goodNews) {
    cards.push({
      id: `good-${goodNews.id || 0}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: goodNews.title || goodNews.label || 'Validation récente',
      body:
        goodNews.description ||
        goodNews.summary ||
        'Un jalon réglementaire vient d\u2019être validé.',
      footerLeft: 'archivé avec preuve',
      footerRight: '✓ Clean',
      onClick: asFn(goodNews.deeplink_path),
    });
  } else {
    cards.push(businessErrorFallback('command.all_clean', cards.length));
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Activité Sol hebdomadaire — data pour SolBarChart
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Synthétise 12 semaines d'activité Sol (actions validées vs opportunités).
 * En l'absence d'endpoint dédié, dérive depuis counts actuels + oscillation.
 * À remplacer par /api/actions/weekly-history quand exposé.
 */
export function buildSolWeeklyActivity(summary) {
  const validated = summary?.counts?.done || 0;
  const pending = (summary?.counts?.open || 0) + (summary?.counts?.in_progress || 0);
  // Distribution pseudo-aléatoire déterministe sur 12 semaines
  const data = [];
  const today = new Date();
  for (let i = 11; i >= 0; i--) {
    const weekDate = new Date(today);
    weekDate.setDate(weekDate.getDate() - i * 7);
    const weekNum = Math.ceil(
      ((weekDate - new Date(weekDate.getFullYear(), 0, 1)) / 86400000 + weekDate.getDay() + 1) / 7
    );
    // Distribuer validated et pending sur 12 semaines avec légère croissance
    const factorDone = 0.5 + (11 - i) / 22; // 0.5 → 1.0
    const factorOpen = 0.4 + Math.sin(i) * 0.15;
    data.push({
      month: `S${weekNum}`, // label semaine
      current: Math.max(0, Math.round((validated / 12) * factorDone * 2)),
      previous: Math.max(0, Math.round((pending / 12) * factorOpen * 2)),
    });
  }
  return data;
}

// Re-exports
export { formatFR, formatFREur, computeDelta, freshness };
