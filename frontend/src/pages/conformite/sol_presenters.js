/**
 * PROMEOS — Conformité Sol presenters (Phase 4.1)
 *
 * Helpers purs pour ConformiteSol — transformation des réponses API
 * compliance vers props de composants Sol.
 *
 * APIs consommées :
 *   getComplianceSummary    → total_sites, sites_ok/nok/unknown, compliance_score,
 *                             findings_by_regulation.{bacs,decret_tertiaire_operat,aper}
 *   getComplianceScoreTrend → trend[] pour SolTrajectoryChart
 *   getComplianceTimeline   → events[] (upcoming/passed/future) pour week-cards
 *   getComplianceFindings   → findings détectés (drift + validations)
 *   getAuditSmeAssessment   → scope audit énergétique (option, 404 si absent)
 *
 * Zéro fetch ici. Fonctions pures déterministes.
 */
import { NBSP, formatFR, formatFREur, computeDelta, freshness } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

// Re-export pour ConformiteSol.jsx
export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

/**
 * "Votre conformité — décret tertiaire, BACS, APER — 5 sites"
 * (utilisé comme titre éditorial SolPageHeader)
 */
export function buildConformiteKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `Conformité · patrimoine ${orgName}${sitesSuffix}`;
}

/**
 * Narrative principale : résume le score global + sites en attention.
 */
export function buildConformiteNarrative({ summary, upcomingCount } = {}) {
  const score = summary?.compliance_score;
  const sitesAttention = summary?.sites_nok ?? 0;
  const totalSites = summary?.total_sites ?? 0;
  const deadlineHint = upcomingCount
    ? ` ${upcomingCount} échéance${upcomingCount > 1 ? 's' : ''} vous attende${upcomingCount > 1 ? 'nt' : ''} cette fenêtre.`
    : '';

  if (score == null) {
    return "Votre score de conformité est en cours de calcul. Revenez dans quelques minutes.";
  }
  if (score >= 75) {
    return `Conformité solide (${formatScore(score)}/100). Votre patrimoine est en bonne trajectoire.${deadlineHint}`;
  }
  if (score >= 60) {
    return `Conformité en vigilance (${formatScore(score)}/100). ${sitesAttention} site${sitesAttention > 1 ? 's' : ''} sur ${totalSites} nécessite${sitesAttention > 1 ? 'nt' : ''} votre attention.${deadlineHint}`;
  }
  return `Zone critique (${formatScore(score)}/100). Plusieurs sites exigent un plan d'action rapide pour tenir la trajectoire 2030.${deadlineHint}`;
}

export function buildConformiteSubNarrative({ summary } = {}) {
  const total = summary?.total_sites ?? 0;
  const ok = summary?.sites_ok ?? 0;
  const nok = summary?.sites_nok ?? 0;
  const unknown = summary?.sites_unknown ?? 0;
  if (total === 0) {
    return "Aucun site évalué pour le moment. Importez votre patrimoine depuis SIREN ou ajoutez un site manuellement.";
  }
  return `${ok}${NBSP}site${ok > 1 ? 's' : ''} conforme${ok > 1 ? 's' : ''} · ${nok}${NBSP}à risque · ${unknown}${NBSP}à évaluer. Sources : RegOps canonique + OPERAT + inspections BACS.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations (headlines humaines)
// ─────────────────────────────────────────────────────────────────────────────

function formatScore(n) {
  if (n == null) return '—';
  return Number(n).toFixed(1).replace('.', ',');
}

export function interpretScoreDT({ score, sitesOk, sitesTotal, deadline }) {
  if (score == null) return 'Score en cours de calcul.';
  const pct = sitesTotal ? `${sitesOk ?? 0}/${sitesTotal} sites conformes` : '';
  if (score >= 75) return `Trajectoire tenue. ${pct}.`.trim();
  if (score >= 60) return `Zone de vigilance. ${pct}${deadline ? `, échéance ${deadline}` : ''}.`;
  return `En zone à risque — plan d'action requis. ${pct}.`.trim();
}

export function interpretScoreBACS({ findingsByReg, notApplicable } = {}) {
  if (notApplicable) {
    return "Aucun bâtiment de votre portefeuille n'est assujetti au décret BACS (puissance CVC\u00a0<\u00a070\u00a0kW).";
  }
  const bacs = findingsByReg?.bacs;
  if (!bacs) return 'Aucune installation BACS recensée.';
  const total = (bacs.ok || 0) + (bacs.nok || 0);
  if (total === 0) return 'Aucun bâtiment assujetti BACS identifié.';
  const pctOk = total > 0 ? Math.round(((bacs.ok || 0) / total) * 100) : 0;
  if (pctOk >= 75) return `${bacs.ok}/${total} installations GTB homologuées.`;
  if (pctOk >= 40) return `${bacs.nok}${NBSP}installation${bacs.nok > 1 ? 's' : ''} à mettre en conformité.`;
  return `GTB/GTC manquante sur ${bacs.nok}${NBSP}bâtiment${bacs.nok > 1 ? 's' : ''} > 290${NBSP}kW.`;
}

export function interpretScoreAPER({ findingsByReg, notApplicable } = {}) {
  if (notApplicable) {
    return "Aucun site de votre portefeuille n'est assujetti à l'obligation APER (toit\u00a0<\u00a0500\u00a0m², parking\u00a0<\u00a01\u00a0500\u00a0m²).";
  }
  const aper = findingsByReg?.aper;
  if (!aper) return 'Cartographie APER en cours.';
  const total = (aper.ok || 0) + (aper.nok || 0) + (aper.unknown || 0);
  if (total === 0) return "Aucun bien assujetti loi APER détecté.";
  if (aper.unknown > 0) return `${aper.unknown}${NBSP}site${aper.unknown > 1 ? 's' : ''} à cartographier (parkings + toitures).`;
  return `${aper.ok}/${total} projets ENR engagés.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI score derivation (API → { score, delta })
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Dérive un score sous-famille (bacs/aper/dt) depuis findings_by_regulation.
 *
 * Règle de calcul :
 *   - `out_of_scope` = sites non-assujettis (ex : APER pas applicable car
 *     toit < 500 m² ET parking < 1 500 m²). Exclu du dénominateur.
 *   - `unknown` = sites assujettis mais non encore évalués (en attente).
 *     Exclu du dénominateur : on ne pénalise pas tant qu'on n'a pas évalué.
 *   - Dénominateur : (ok + nok) = sites réellement évalués.
 *
 * Retour :
 *   - number 0-100 : pourcentage d'évalués conformes (1 décimale)
 *   - 'not_applicable' : aucun site assujetti (tous out_of_scope)
 *   - null : en attente d'évaluation (unknown > 0, ok+nok = 0) ou données absentes
 */
export function deriveScoreFromFindings(findings) {
  if (!findings) return null;
  const ok = findings.ok || 0;
  const nok = findings.nok || 0;
  const unknown = findings.unknown || 0;
  const outOfScope = findings.out_of_scope || 0;

  // Aucun site en scope (tous out_of_scope) → réglementation non applicable
  const inScope = ok + nok + unknown;
  if (inScope === 0) {
    return outOfScope > 0 ? 'not_applicable' : null;
  }

  // Sites en scope mais aucun encore évalué → en attente (null, pas 0)
  const evaluated = ok + nok;
  if (evaluated === 0) return null;

  // Score = pourcentage d'évalués conformes, 1 décimale
  return Math.round((ok / evaluated) * 1000) / 10;
}

/**
 * Calcule le delta d'un score vs 6 mois précédents depuis le trend array.
 */
export function computeScoreDelta(trendArr, context = `sur${NBSP}6${NBSP}mois`) {
  if (!Array.isArray(trendArr) || trendArr.length < 2) return null;
  const first = trendArr[0];
  const last = trendArr[trendArr.length - 1];
  if (first?.score == null || last?.score == null) return null;
  return computeDelta({
    current: last.score,
    previous: first.score,
    unit: 'pts',
    context,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards — 3 cards conformité avec footers chiffrés + EvidenceDrawer deeplinks
// ─────────────────────────────────────────────────────────────────────────────

function formatDateFR(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  const diffMs = d.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Construit 3 week-cards conformité avec fallbacks businessErrors.
 *
 * @param {object} inputs
 * @param {Array}  inputs.findings            — findings drift/anomalies
 * @param {Array}  inputs.timelineUpcoming    — events timeline status 'upcoming'
 * @param {Array}  inputs.timelineValidated   — events timeline status 'passed'
 * @param {Function} inputs.onOpenEvidence    — callback click (passe finding.id)
 * @returns {Array<SolWeekCardProps>} exactement 3 cards
 */
export function buildConformiteWeekCards({
  findings = [],
  timelineUpcoming = [],
  timelineValidated = [],
  onOpenEvidence,
} = {}) {
  const cards = [];

  // Card 1 — "À regarder" : top finding drift, fallback si aucune dérive
  const topDrift = findings.find((f) => f?.severity === 'critical' || f?.severity === 'high')
    || findings[0];
  if (topDrift) {
    const deltaScore = topDrift.score_delta ?? topDrift.deltaScore;
    const deltaLabel = deltaScore != null ? `écart ${deltaScore > 0 ? '+' : ''}${deltaScore}${NBSP}pts` : '';
    cards.push({
      id: `drift-${topDrift.id || topDrift.rule_id || 0}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: topDrift.title || topDrift.action || topDrift.label || 'Dérive détectée',
      body: topDrift.message || topDrift.description || topDrift.summary,
      footerLeft: deltaLabel || topDrift.regulation?.toUpperCase() || '',
      footerRight: '⌘K',
      onClick: () => onOpenEvidence?.(topDrift),
    });
  } else {
    cards.push(businessErrorFallback('conformite.no_drift'));
  }

  // Card 2 — "À faire" : prochaine échéance upcoming
  const topUpcoming = [...timelineUpcoming].sort(
    (a, b) => new Date(a.deadline) - new Date(b.deadline)
  )[0];
  if (topUpcoming) {
    const dl = topUpcoming.deadline;
    const daysLeft = daysUntil(dl);
    const penalty = topUpcoming.penalty_eur;
    const sitesCount = topUpcoming.sites_concerned;
    const footerParts = [];
    if (daysLeft != null) footerParts.push(`${daysLeft > 0 ? `${daysLeft}${NBSP}j restants` : 'échéance passée'}`);
    if (penalty) footerParts.push(`pénalité ${formatFREur(penalty, 0)}`);
    cards.push({
      id: `upcoming-${topUpcoming.id || 0}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: topUpcoming.label || topUpcoming.title || 'Échéance à préparer',
      body:
        (topUpcoming.description || topUpcoming.summary || '') +
        (sitesCount ? ` ${sitesCount} site${sitesCount > 1 ? 's' : ''} concerné${sitesCount > 1 ? 's' : ''}.` : ''),
      footerLeft: footerParts.join(' · '),
      footerRight: dl ? formatDateFR(dl) : 'Automatisable',
      onClick: () => onOpenEvidence?.(topUpcoming),
    });
  } else {
    cards.push(businessErrorFallback('conformite.no_upcoming'));
  }

  // Card 3 — "Bonne nouvelle" : dernière validation (timeline passed)
  const lastValidated = [...timelineValidated].sort(
    (a, b) => new Date(b.deadline) - new Date(a.deadline)
  )[0];
  if (lastValidated) {
    cards.push({
      id: `validated-${lastValidated.id || 0}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: lastValidated.label || lastValidated.title,
      body:
        (lastValidated.description || '') +
        (lastValidated.sites_concerned
          ? ` ${lastValidated.sites_concerned} site${lastValidated.sites_concerned > 1 ? 's' : ''} validé${lastValidated.sites_concerned > 1 ? 's' : ''}.`
          : ''),
      footerLeft: 'conforme · pièce au dossier',
      footerRight: '✓ Clean',
      onClick: () => onOpenEvidence?.(lastValidated),
    });
  } else {
    cards.push(businessErrorFallback('conformite.no_recent_validation'));
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Re-exports utiles
// ─────────────────────────────────────────────────────────────────────────────

export { formatFR, formatFREur, computeDelta, freshness };
