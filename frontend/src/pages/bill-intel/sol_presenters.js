/**
 * PROMEOS — Bill Intelligence Sol presenters (Phase 4.2)
 *
 * Helpers purs pour BillIntelSol — transformation des réponses APIs
 * billing vers props de composants Sol.
 *
 * APIs consommées :
 *   getBillingSummary()            → total_eur, total_invoices, total_insights,
 *                                    total_estimated_loss_eur, coverage_months
 *   getBillingInsights({limit})    → [{id, site_id, type, severity, message,
 *                                       estimated_loss_eur, insight_status, ...}]
 *   getBillingCompareMonthly({months:12}) → {current_year, previous_year,
 *                                             months: [{label, current_eur, previous_eur, ...}]}
 *
 * Zéro fetch ici. Fonctions pures déterministes.
 */
import { NBSP, formatFR, formatFREur, computeDelta, freshness } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildBillKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `Facturation · patrimoine ${orgName}${sitesSuffix}`;
}

export function buildBillNarrative({ summary, anomaliesCount, recoveredYtd } = {}) {
  const totalEur = summary?.total_eur;
  const totalInvoices = summary?.total_invoices ?? 0;
  const potentialLoss = summary?.total_estimated_loss_eur ?? 0;

  if (!totalEur && totalInvoices === 0) {
    return "Importez vos premières factures pour déclencher l'analyse shadow billing et détecter les anomalies.";
  }

  if (anomaliesCount > 0 && potentialLoss > 0) {
    return `${anomaliesCount}${NBSP}anomalie${anomaliesCount > 1 ? 's' : ''} détectée${anomaliesCount > 1 ? 's' : ''} sur ${totalInvoices}${NBSP}facture${totalInvoices > 1 ? 's' : ''} analysée${totalInvoices > 1 ? 's' : ''}. Récupération potentielle : ${formatFREur(potentialLoss, 0)}.`;
  }

  if (anomaliesCount > 0) {
    return `${anomaliesCount}${NBSP}anomalie${anomaliesCount > 1 ? 's' : ''} détectée${anomaliesCount > 1 ? 's' : ''} sur ${totalInvoices}${NBSP}facture${totalInvoices > 1 ? 's' : ''} analysée${totalInvoices > 1 ? 's' : ''}.`;
  }

  return `${totalInvoices}${NBSP}facture${totalInvoices > 1 ? 's' : ''} analysée${totalInvoices > 1 ? 's' : ''}, aucune anomalie détectée. Votre facturation est conforme aux barèmes réglementaires.`;
}

export function buildBillSubNarrative({ summary } = {}) {
  const months = summary?.coverage_months ?? 0;
  const engine = summary?.engine_version || 'shadow v4.2';
  if (months === 0) return 'Couverture analytique en cours de constitution.';
  return `${months}${NBSP}mois couverts · moteur ${engine} compare chaque ligne aux barèmes TURPE 7, ATRD, accises, CTA et TVA en vigueur.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretTotalFactures({
  summary,
  currentMonthEur,
  previousMonthEur,
  topAnomalySites,
} = {}) {
  if (currentMonthEur == null) {
    return 'Montant du mois en cours en cours de calcul.';
  }
  const prev = previousMonthEur;
  const pctChange = prev ? Math.abs((currentMonthEur - prev) / prev) * 100 : null;
  const drivers = (topAnomalySites || []).slice(0, 2);

  if (pctChange == null) {
    return `${summary?.total_invoices ?? 0} factures agrégées ce mois.`;
  }
  if (pctChange < 3) return 'Facture stable vs mois précédent.';
  if (currentMonthEur > prev) {
    if (drivers.length >= 2) {
      return `Hausse tirée par ${drivers[0]} et ${drivers[1]}.`;
    }
    return 'Hausse significative vs mois précédent.';
  }
  return 'Baisse vs mois précédent — effet saison + arbitrage contractuel.';
}

export function interpretAnomalies({ anomaliesCount, potentialRecovery, contestableCount } = {}) {
  if (!anomaliesCount) return 'Aucune anomalie détectée ce mois.';
  const recovery = potentialRecovery
    ? ` · récupération potentielle ${formatFREur(potentialRecovery, 0)}`
    : '';
  const contestable =
    contestableCount != null
      ? ` dont ${contestableCount}${NBSP}contestable${contestableCount > 1 ? 's' : ''} automatiquement`
      : '';
  return `${contestable}${recovery}`.trim() || `${anomaliesCount} anomalies à investiguer.`;
}

export function interpretRecovery({ recoveredYtd, contestationsValidated, avgDelayDays } = {}) {
  if (!recoveredYtd || recoveredYtd === 0) {
    return 'Aucune contestation validée depuis le 1ᵉʳ janvier.';
  }
  const count = contestationsValidated
    ? `sur ${contestationsValidated}${NBSP}contestation${contestationsValidated > 1 ? 's' : ''} validée${contestationsValidated > 1 ? 's' : ''}`
    : '';
  const delay = avgDelayDays ? ` · délai moyen ${avgDelayDays}${NBSP}jours` : '';
  return `${count}${delay}`.trim() || `${formatFREur(recoveredYtd, 0)} récupérés cette année.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Data adapters — API → composants
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit getBillingCompareMonthly().months → SolBarChart.data
 * @returns [{ month: 'Janv', current: number, previous: number|null }]
 */
export function adaptCompareToBarChart(compare) {
  if (!compare || !Array.isArray(compare.months)) return [];
  return compare.months.map((m) => ({
    month: m.label || String(m.month),
    current: m.current_eur != null ? Number(m.current_eur) : null,
    previous: m.previous_eur != null ? Number(m.previous_eur) : null,
  }));
}

/**
 * Extrait le total du mois en cours (dernier non-null current_eur) + precedent.
 */
export function extractCurrentMonthTotals(compare) {
  if (!compare || !Array.isArray(compare.months)) {
    return { currentEur: null, previousMonthEur: null };
  }
  const withCurrent = compare.months.filter((m) => m.current_eur != null);
  if (withCurrent.length === 0) {
    return { currentEur: null, previousMonthEur: null };
  }
  const lastMonth = withCurrent[withCurrent.length - 1];
  const prevMonth = withCurrent[withCurrent.length - 2];
  return {
    currentEur: Number(lastMonth.current_eur),
    previousMonthEur: prevMonth ? Number(prevMonth.current_eur) : null,
  };
}

/**
 * Estime la récupération YTD depuis les anomalies avec insight_status = resolved.
 * Backend pourrait exposer un endpoint dédié — pour l'instant on infère depuis
 * getBillingInsights() filtered.
 */
export function estimateRecoveredYtd(insights) {
  if (!Array.isArray(insights)) return 0;
  return insights
    .filter((i) => i?.insight_status === 'resolved')
    .reduce((sum, i) => sum + (Number(i.estimated_loss_eur) || 0), 0);
}

/**
 * Count contestable automatically (confidence >= 85 % → heuristique frontend).
 */
export function countContestableAnomalies(insights) {
  if (!Array.isArray(insights)) return 0;
  // Heuristique : les types shadow_gap / reseau_mismatch / taxes_mismatch
  // avec severity 'high' ou 'critical' sont contestables automatiquement.
  const CONTESTABLE_TYPES = new Set([
    'shadow_gap',
    'reseau_mismatch',
    'taxes_mismatch',
    'accise_mismatch',
    'cta_mismatch',
  ]);
  return insights.filter(
    (i) => CONTESTABLE_TYPES.has(i?.type) && ['high', 'critical'].includes(i?.severity)
  ).length;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards billing
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Construit 3 week-cards billing avec fallbacks businessErrors.
 *   Card 1 "À regarder"  : top anomalie non-résolue par impact €
 *   Card 2 "À faire"     : contestation en cours ou à lancer
 *   Card 3 "Bonne nouvelle" : dernière récupération validée
 */
export function buildBillWeekCards({ insights = [], onOpenInsight } = {}) {
  const cards = [];

  const openInsights = insights
    .filter((i) => i?.insight_status === 'open')
    .sort((a, b) => (Number(b.estimated_loss_eur) || 0) - (Number(a.estimated_loss_eur) || 0));

  const topAnomalie =
    openInsights.find((i) => ['high', 'critical'].includes(i?.severity)) || openInsights[0];
  if (topAnomalie) {
    const impact = Number(topAnomalie.estimated_loss_eur) || 0;
    cards.push({
      id: `anomaly-${topAnomalie.id}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: `${labelType(topAnomalie.type)}${topAnomalie.supplier ? ' · ' + topAnomalie.supplier : ''}`,
      body: topAnomalie.message || `Anomalie détectée par le shadow billing.`,
      footerLeft: impact ? `impact ${formatFREur(impact, 0)}` : '',
      footerRight: '⌘K',
      onClick: () => onOpenInsight?.(topAnomalie),
    });
  } else {
    cards.push(businessErrorFallback('billing.no_anomalies_detected', cards.length));
  }

  // Card 2 À faire : contestation en cours (in_review) ou à engager si anomalie présente
  const inReview = insights.find((i) => i?.insight_status === 'in_review');
  const pendingContestation = insights.find(
    (i) => i?.action_id != null && i?.insight_status === 'open'
  );
  const topForAction = inReview || pendingContestation;
  if (topForAction) {
    const impact = Number(topForAction.estimated_loss_eur) || 0;
    cards.push({
      id: `action-${topForAction.id}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: inReview
        ? `Contestation en cours · ${topForAction.supplier || labelType(topForAction.type)}`
        : `Contester ${topForAction.supplier || labelType(topForAction.type)}`,
      body: topForAction.message,
      footerLeft: impact ? `récupération ${formatFREur(impact, 0)}` : '',
      footerRight: 'Automatisable',
      onClick: () => onOpenInsight?.(topForAction),
    });
  } else {
    cards.push(businessErrorFallback('billing.recovery_in_progress'));
  }

  // Card 3 Bonne nouvelle : dernière résolution
  const resolved = insights
    .filter((i) => i?.insight_status === 'resolved')
    .sort((a, b) => (Number(b.estimated_loss_eur) || 0) - (Number(a.estimated_loss_eur) || 0))[0];
  if (resolved) {
    const impact = Number(resolved.estimated_loss_eur) || 0;
    cards.push({
      id: `resolved-${resolved.id}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `Récupéré · ${resolved.supplier || labelType(resolved.type)}`,
      body: `Contestation validée, avoir correctif reçu.`,
      footerLeft: impact ? `+${formatFREur(impact, 0)} récupérés` : 'récupération validée',
      footerRight: '✓ Clean',
      onClick: () => onOpenInsight?.(resolved),
    });
  } else {
    cards.push(businessErrorFallback('billing.no_anomalies_detected', cards.length));
  }

  return cards.slice(0, 3);
}

const TYPE_LABELS = {
  shadow_gap: 'Écart shadow billing',
  reseau_mismatch: 'Coût réseau (TURPE)',
  taxes_mismatch: 'Taxes & accises',
  unit_price_high: 'Prix unitaire anormal',
  contract_expiry_soon: 'Contrat expirant',
  accise_mismatch: 'Taux accise incorrect',
  cta_mismatch: 'CTA incorrecte',
  tva_mismatch: 'Taux TVA incorrect',
};

function labelType(type) {
  return TYPE_LABELS[type] || 'Anomalie facturation';
}

// Re-exports utiles pour BillIntelSol
export { formatFR, formatFREur, computeDelta, freshness };
