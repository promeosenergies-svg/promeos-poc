/**
 * PROMEOS — DiagnosticConsoSol presenters (Lot 3 Phase 5, Pattern A hybride)
 *
 * Helpers purs pour DiagnosticConsoSol (/diagnostic-conso).
 *
 * API consommée (parent ConsumptionDiagPage.jsx legacy) :
 *   getConsumptionInsights(orgId) → {
 *     insights: [{
 *       id, site_id, site_nom, type, severity, message,
 *       estimated_loss_kwh, estimated_loss_eur, insight_status,
 *       period_start, period_end, metrics, recommended_actions, …
 *     }, …],
 *     summary: {
 *       total_insights, sites_with_insights, total_loss_eur,
 *       total_loss_kwh, …
 *     }
 *   }
 *
 * IMPORTANT : divergences spec user → API réelle
 *   - `annual_loss_eur` spec → `total_loss_eur` (cumul période, NON annualisé)
 *   - `drift_kwh` spec → `total_loss_kwh`
 *   - `flex_potential_kw` spec → absent côté summary (per-site via
 *     getFlexMini). KPI 3 remappé en « Sites concernés »
 *     (sites_with_insights).
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Type labels (cohérent avec `insight.type` enum backend)
// ─────────────────────────────────────────────────────────────────────────────

const INSIGHT_TYPE_LABEL = {
  hors_horaires: 'Hors horaires',
  base_load: 'Talon excessif',
  pointe: 'Pointe anormale',
  derive: 'Dérive tendance',
  data_gap: 'Données manquantes',
};

export function labelInsightType(type) {
  return INSIGHT_TYPE_LABEL[type] || (type ? String(type).replace(/_/g, ' ') : 'Anomalie');
}

const SEVERITY_TONE = {
  critical: 'refuse',
  high: 'attention',
  medium: 'afaire',
  low: 'calme',
};

export function toneFromSeverity(severity) {
  return SEVERITY_TONE[String(severity || '').toLowerCase()] || 'afaire';
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildDiagnosticKicker({ scope, selectedSite, periodDays } = {}) {
  const siteTag = selectedSite?.nom ? selectedSite.nom.toUpperCase() : 'PATRIMOINE TOUS LES SITES';
  const days = periodDays || 90;
  return `DIAGNOSTIC · CONSOMMATION · ${siteTag} · ${days}${NBSP}JOURS`;
}

export function buildDiagnosticNarrative({ summary, insights = [], scope, periodDays } = {}) {
  const totalInsights = summary?.total_insights ?? insights.length ?? 0;
  const totalLossEur = Number(summary?.total_loss_eur) || 0;
  const totalLossKwh = Number(summary?.total_loss_kwh) || 0;
  const sitesCount = summary?.sites_with_insights ?? 0;
  const days = periodDays || 90;

  if (totalInsights === 0) {
    return `Aucune anomalie détectée sur les ${days}${NBSP}derniers jours. Votre patrimoine est stable.`;
  }

  // Top insight par impact EUR
  const topByEur = [...insights]
    .filter((i) => Number(i?.estimated_loss_eur) > 0)
    .sort((a, b) => (Number(b.estimated_loss_eur) || 0) - (Number(a.estimated_loss_eur) || 0))[0];

  const parts = [];
  parts.push(
    `${totalInsights}${NBSP}anomalie${totalInsights > 1 ? 's' : ''} détectée${totalInsights > 1 ? 's' : ''} sur ${days}${NBSP}jours`
  );
  if (sitesCount > 0) {
    parts.push(
      `${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''} concerné${sitesCount > 1 ? 's' : ''}`
    );
  }
  if (totalLossEur > 0) {
    parts.push(`pertes cumulées ${formatFREur(totalLossEur, 0)}`);
  }
  if (totalLossKwh > 0) {
    parts.push(`excès énergétique ${formatFR(Math.round(totalLossKwh / 1000), 0)}${NBSP}MWh`);
  }
  if (topByEur) {
    const where = topByEur.site_nom || `site #${topByEur.site_id}`;
    parts.push(`action prioritaire : ${where} · ${labelInsightType(topByEur.type)}`);
  }
  return parts.join(' · ') + '.';
}

export function buildDiagnosticSubNarrative() {
  return 'Méthodologie : baseline DJU Météo-France normalisée · détection ML LOF sur profils horaires · seuils ADEME archétypes tertiaire.';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretTotalLoss({ summary, customPrice } = {}) {
  const totalEur = Number(summary?.total_loss_eur) || 0;
  if (totalEur <= 0) return 'Aucune perte financière identifiée sur la période.';
  if (customPrice) {
    return `Recalcul avec prix ${customPrice}${NBSP}€/kWh · basé sur dérives détectées.`;
  }
  return 'Basé sur prix moyen pondéré · estimation sur la période analysée.';
}

export function interpretDriftKwh({ summary } = {}) {
  const kwh = Number(summary?.total_loss_kwh) || 0;
  if (kwh <= 0) return 'Aucun excès énergétique détecté sur la période.';
  const mwh = Math.round(kwh / 1000);
  return `${formatFR(mwh, 0)}${NBSP}MWh cumulés au-dessus du profil archétype ADEME.`;
}

export function interpretSitesAffected({ summary } = {}) {
  const sites = Number(summary?.sites_with_insights) || 0;
  const total = Number(summary?.total_insights) || 0;
  if (sites <= 0) return "Aucun site ne présente d'anomalie active.";
  return `${sites}${NBSP}site${sites > 1 ? 's' : ''} avec ${total}${NBSP}anomalie${total > 1 ? 's' : ''} active${total > 1 ? 's' : ''} détectée${total > 1 ? 's' : ''}.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Adapt insights → SolBarChart (top sites par pertes €)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Agrège insights par site → data SolBarChart catégoriel.
 * Shape retournée : [{ site, current (EUR perdus), previous: 0 }]
 * (previous = 0 par convention car pas de valeur historique comparable)
 */
export function adaptInsightsToBarChart(insights = [], { limit = 8 } = {}) {
  if (!Array.isArray(insights) || insights.length === 0) return [];
  const bySite = new Map();
  for (const i of insights) {
    const siteName = i?.site_nom || `#${i?.site_id ?? '—'}`;
    const eur = Number(i?.estimated_loss_eur) || 0;
    if (eur <= 0) continue;
    bySite.set(siteName, (bySite.get(siteName) || 0) + eur);
  }
  return Array.from(bySite.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([site, eur]) => ({
      site: shortSite(site),
      current: Math.round(eur),
      previous: 0,
    }));
}

function shortSite(name) {
  if (!name) return 'Site';
  const clean = String(name)
    .replace(/HELIOS\s*/gi, '')
    .trim();
  return clean.length > 20 ? clean.slice(0, 18) + '…' : clean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards (variety guard D1 : 1 attention + 1 afaire + 1 succes)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards diagnostic avec variety imposée.
 *   Card 1 'attention' : top insight impact € (le plus cher non résolu)
 *   Card 2 'afaire'    : insight avec recommended_actions[] prêt OU data_gap
 *   Card 3 'succes'    : insight résolu récent OU "patrimoine stable"
 */
export function buildDiagnosticWeekCards({ insights = [], onOpenInsight } = {}) {
  const active = insights.filter((i) => i?.insight_status !== 'resolved');
  const resolved = insights.filter((i) => i?.insight_status === 'resolved');

  const cards = [];

  // Card 1 : top impact € (attention)
  const topEur = [...active]
    .filter((i) => Number(i?.estimated_loss_eur) > 0)
    .sort((a, b) => (Number(b.estimated_loss_eur) || 0) - (Number(a.estimated_loss_eur) || 0))[0];
  if (topEur) {
    const where = topEur.site_nom || `Site #${topEur.site_id}`;
    cards.push({
      id: `top-eur-${topEur.id || 'top'}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: `${where} · ${labelInsightType(topEur.type)}`,
      body: topEur.message || 'Impact financier le plus élevé sur la période.',
      footerLeft: formatFREur(Math.round(topEur.estimated_loss_eur || 0), 0),
      footerRight: '⌘K',
      onClick: () => onOpenInsight?.(topEur),
    });
  } else {
    cards.push(businessErrorFallback('diagnostic.no_insights', cards.length));
  }

  // Card 2 : insight avec recommended_actions (afaire)
  const withReco = active.find(
    (i) =>
      Array.isArray(i?.recommended_actions) &&
      i.recommended_actions.length > 0 &&
      i.id !== topEur?.id
  );
  if (withReco) {
    const where = withReco.site_nom || `Site #${withReco.site_id}`;
    cards.push({
      id: `reco-${withReco.id || 'mid'}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: `${where} · action prête`,
      body:
        withReco.recommended_actions[0]?.label ||
        withReco.message ||
        'Action recommandée identifiée.',
      footerLeft: labelInsightType(withReco.type),
      footerRight: 'Sol peut préparer',
      onClick: () => onOpenInsight?.(withReco),
    });
  } else {
    const fb = businessErrorFallback('diagnostic.seed_needed', cards.length);
    cards.push({ ...fb, tagKind: 'afaire', tagLabel: 'À faire' });
  }

  // Card 3 : insight résolu OU évaluation active (succes)
  if (resolved.length > 0) {
    const lastResolved = resolved[0];
    const where = lastResolved.site_nom || `Site #${lastResolved.site_id}`;
    cards.push({
      id: `resolved-${lastResolved.id || 'last'}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `${where} · anomalie résolue`,
      body: lastResolved.message || 'Anomalie traitée et confirmée résolue.',
      footerLeft: labelInsightType(lastResolved.type),
      footerRight: '✓ Clean',
      onClick: () => onOpenInsight?.(lastResolved),
    });
  } else {
    cards.push({
      id: 'monitoring-active',
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: 'Détection continue active',
      body: "Sol analyse les consommations chaque nuit et vous alertera dès qu'une anomalie nouvelle apparaît.",
      footerLeft: 'ML + baseline DJU',
      footerRight: '—',
    });
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalize
// ─────────────────────────────────────────────────────────────────────────────

export function normalizeDiagnosticSummary(raw) {
  if (!raw) {
    return {
      total_insights: 0,
      sites_with_insights: 0,
      total_loss_eur: 0,
      total_loss_kwh: 0,
    };
  }
  return {
    total_insights: Number(raw.total_insights) || 0,
    sites_with_insights: Number(raw.sites_with_insights) || 0,
    total_loss_eur: Number(raw.total_loss_eur) || 0,
    total_loss_kwh: Number(raw.total_loss_kwh) || 0,
  };
}
