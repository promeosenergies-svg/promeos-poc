/**
 * PROMEOS — Site360Sol presenters (Lot 3 Phase 2)
 *
 * Helpers purs pour Site360Sol (onglet « Résumé » en Pattern C).
 * Ne refactorise PAS les autres onglets : Site360.jsx legacy reste
 * responsable des 8 autres tabs (conso, analytics, factures, …).
 *
 * Sources utilisées :
 *   - site : entité scopedSites (déjà fetch côté Site360.jsx parent)
 *   - intensityData : { intensity, benchmark, intensityRatio, hasIntensity }
 *   - siteComplianceScore : A.2 backend (/api/compliance/sites/{id}/score)
 *   - unifiedAnomalies : /patrimoine/sites/{id}/anomalies-unified
 *   - topReco : recommandation top 1 (pushée par parent)
 *   - deliveryPoints : /patrimoine/sites/{id}/delivery-points (PDL/PRM)
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { getBenchmark } from '../../utils/benchmarks';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Compliance normalization
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Normalise la réponse /api/compliance/sites/{id}/score vers la shape
 * attendue par les presenters Site360Sol.
 *
 * Input  : { score: 62.4, breakdown: [{framework: 'tertiaire_operat', score: 58}, ...] }
 * Output : { overall: 62, breakdown: { dt: 58, bacs: 80, aper: null }, baseline }
 *
 * Retourne null si l'input est null/undefined.
 */
const FRAMEWORK_ALIAS = {
  tertiaire_operat: 'dt',
  decret_tertiaire: 'dt',
  dt: 'dt',
  bacs: 'bacs',
  aper: 'aper',
};

export function normalizeCompliance(raw) {
  if (!raw) return null;
  const overall = raw.score != null ? Math.round(raw.score) : (raw.overall ?? null);
  const breakdown = {};
  const list = Array.isArray(raw.breakdown) ? raw.breakdown : [];
  for (const b of list) {
    const key = FRAMEWORK_ALIAS[b?.framework];
    if (key && b.score != null) breakdown[key] = Math.round(b.score);
  }
  return {
    overall,
    breakdown,
    baseline: raw.baseline ?? null,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

const USAGE_LABEL_FR = {
  bureau: 'bureaux',
  bureaux: 'bureaux',
  entrepot: 'entrepôt',
  logistique: 'site logistique',
  enseignement: 'enseignement',
  commerce: 'commerce',
  magasin: 'magasin',
  hotel: 'hôtel',
  hotellerie: 'hôtellerie',
  sante: 'site santé',
  industrie: 'site industriel',
  usine: 'usine',
  autre: 'tertiaire',
};

export function labelUsage(usage) {
  if (!usage) return 'tertiaire';
  return USAGE_LABEL_FR[String(usage).toLowerCase()] || String(usage).toLowerCase();
}

export function buildSiteKicker(site) {
  if (!site) return 'SITE';
  const type = labelUsage(site.usage || site.type).toUpperCase();
  const city = site.ville || site.city || '';
  return city ? `SITE · ${type} · ${city.toUpperCase()}` : `SITE · ${type}`;
}

/**
 * Narrative synthèse (1 phrase) : comportement énergétique + anomalies + compliance.
 * Priorité éditoriale : écart EUI le plus surprenant d'abord, puis anomalies actives,
 * puis statut DT.
 */
export function buildSiteNarrative({ site, intensityData, anomalies = [], compliance }) {
  if (!site) return '';
  const nom = site.nom || 'Ce site';
  const usageLabel = labelUsage(site.usage || site.type);
  const anomCount = Array.isArray(anomalies)
    ? anomalies.filter((a) => a && !a.resolved_at).length
    : 0;

  const intensity = intensityData?.intensity;
  const benchmark = intensityData?.benchmark;
  const hasIntensity = intensityData?.hasIntensity && intensity > 0 && benchmark > 0;

  // Clause EUI (énergie)
  let clauseEui = '';
  if (hasIntensity) {
    const gapPct = Math.round(((intensity - benchmark) / benchmark) * 100);
    if (gapPct > 15) {
      clauseEui = `consomme ${gapPct}${NBSP}% au-dessus du benchmark ADEME ${usageLabel}`;
    } else if (gapPct < -10) {
      clauseEui = `consomme ${Math.abs(gapPct)}${NBSP}% mieux que la référence ADEME ${usageLabel}`;
    } else {
      clauseEui = `consomme au rythme attendu pour un ${usageLabel}`;
    }
  } else {
    clauseEui = `n'a pas encore assez de données pour situer sa performance énergétique`;
  }

  // Clause anomalies
  let clauseAnom = '';
  if (anomCount > 0) {
    clauseAnom = ` mais ${anomCount}${NBSP}anomalie${anomCount > 1 ? 's' : ''} de facturation mérite${anomCount > 1 ? 'nt' : ''} vérification`;
  }

  // Clause compliance
  const score = compliance?.overall ?? site.compliance_score ?? null;
  let clauseCompliance = '';
  if (score != null) {
    if (score < 60) {
      clauseCompliance = ` · score Décret Tertiaire ${score}/100 en zone à risque`;
    } else if (score < 75) {
      clauseCompliance = ` · score Décret Tertiaire ${score}/100 à surveiller`;
    } else {
      clauseCompliance = ` · score Décret Tertiaire ${score}/100 solide`;
    }
  }

  return `${nom} ${clauseEui}${clauseAnom}${clauseCompliance}.`;
}

/**
 * Sub-narrative : contexte hiérarchique + fraîcheur.
 */
export function buildSiteSubNarrative({ site }) {
  if (!site) return '';
  const parts = [];
  if (site.organisation_nom) parts.push(site.organisation_nom);
  if (site.entite_juridique_nom) parts.push(site.entite_juridique_nom);
  if (site.portefeuille_nom) parts.push(site.portefeuille_nom);
  const hierarchy = parts.length > 0 ? parts.join(` ${NBSP}›${NBSP} `) : null;
  const sources = 'Sources : scope patrimoine + RegOps canonique + shadow billing';
  return hierarchy ? `${hierarchy}. ${sources}.` : sources + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Status pill (compliance-driven)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Pill tone + label depuis compliance score ou statut_conformite.
 * Retourne null si aucun signal (omet le pill proprement).
 */
export function statusPillFromSite({ site, compliance }) {
  const score = compliance?.overall ?? site?.compliance_score ?? null;
  if (score != null) {
    if (score >= 75) return { tone: 'calme', label: 'Conforme' };
    if (score >= 60) return { tone: 'attention', label: 'À surveiller' };
    return { tone: 'afaire', label: 'À traiter' };
  }
  const statut = site?.statut_conformite;
  if (!statut) return null;
  if (statut === 'conforme') return { tone: 'calme', label: 'Conforme' };
  if (statut === 'a_risque') return { tone: 'attention', label: 'À risque' };
  if (statut === 'non_conforme') return { tone: 'afaire', label: 'Non conforme' };
  if (statut === 'a_evaluer') return { tone: 'attention', label: 'À évaluer' };
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Entity card fields
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fields pour SolEntityCard : ordre métier PDL → SIRET → Surface → Type → Adresse → Hiérarchie.
 * Fallback « — » pour champs absents (préservation de la grille).
 */
export function buildEntityCardFields({ site, deliveryPoints = [] }) {
  if (!site) return [];
  const pdl = Array.isArray(deliveryPoints) && deliveryPoints.length > 0
    ? deliveryPoints
        .map((dp) => dp.prm || dp.pdl || dp.identifier)
        .filter(Boolean)
        .slice(0, 2)
        .join(' · ')
    : null;
  const surfaceLabel = site.surface_m2 > 0 ? `${formatFR(site.surface_m2, 0)}${NBSP}m²` : '—';
  const addressParts = [site.adresse, site.code_postal, site.ville].filter(Boolean);
  const addressLabel = addressParts.length > 0 ? addressParts.join(', ') : '—';

  const fields = [
    { label: 'PDL / PRM', value: pdl || '—', mono: Boolean(pdl) },
    { label: 'SIRET', value: site.siret || '—', mono: Boolean(site.siret) },
    { label: 'Surface', value: surfaceLabel, mono: true },
    { label: 'Usage', value: labelUsage(site.usage || site.type) },
    { label: 'Adresse', value: addressLabel },
  ];

  if (site.conso_kwh_an > 0) {
    const mwh = Math.round(site.conso_kwh_an / 1000);
    fields.push({ label: 'Conso 12 mois', value: `${formatFR(mwh, 0)}${NBSP}MWh`, mono: true });
  }

  return fields;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Headline EUI : positionne vs benchmark ADEME en français clair.
 * Retourne business error fallback si data manquante.
 */
export function interpretSiteEui({ intensityData, site }) {
  if (!intensityData?.hasIntensity) {
    return 'Intensité énergétique indisponible — renseignez surface et importez 12 mois de conso.';
  }
  const { intensity, benchmark } = intensityData;
  if (!benchmark || benchmark <= 0) {
    return `EUI ${formatFR(intensity, 0)}${NBSP}kWh/m²/an. Benchmark ADEME indisponible pour cet usage.`;
  }
  const gapPct = Math.round(((intensity - benchmark) / benchmark) * 100);
  const bench = formatFR(benchmark, 0);
  const usageLabel = labelUsage(site?.usage || site?.type);
  if (gapPct > 10) {
    return `${gapPct}${NBSP}% au-dessus du benchmark ADEME ${usageLabel} (${bench}${NBSP}kWh/m²).`;
  }
  if (gapPct < -5) {
    return `${Math.abs(gapPct)}${NBSP}% mieux que le benchmark ADEME ${usageLabel} (${bench}${NBSP}kWh/m²).`;
  }
  return `Aligné sur la référence ADEME ${usageLabel} (${bench}${NBSP}kWh/m²/an).`;
}

/**
 * Headline conformité : breakdown DT/BACS/APER si dispo.
 */
export function interpretSiteCompliance({ compliance, site }) {
  const breakdown = compliance?.breakdown || {};
  const dt = breakdown.dt ?? breakdown.decret_tertiaire ?? null;
  const bacs = breakdown.bacs ?? null;
  const aper = breakdown.aper ?? null;
  const parts = [];
  if (dt != null) parts.push(`DT ${dt}`);
  if (bacs != null) parts.push(`BACS ${bacs}`);
  if (aper != null) parts.push(`APER ${aper}`);
  if (parts.length > 0) return parts.join(' · ');
  const score = compliance?.overall ?? site?.compliance_score ?? null;
  if (score == null) return 'Score en cours de calcul.';
  if (score < 60) return 'En zone à risque avant 2030, plan requis.';
  if (score < 75) return 'Trajectoire à surveiller — levier possible.';
  return 'Trajectoire Décret Tertiaire solide.';
}

/**
 * Headline risque financier : contextualise en phrase courte.
 */
export function interpretSiteRisque({ site, anomalies = [] }) {
  const risque = Number(site?.risque_eur) || 0;
  const anomCount = Array.isArray(anomalies)
    ? anomalies.filter((a) => a && !a.resolved_at).length
    : 0;
  if (risque <= 0 && anomCount === 0) {
    return 'Aucun risque financier identifié ce mois.';
  }
  if (risque <= 0 && anomCount > 0) {
    return `${anomCount}${NBSP}anomalie${anomCount > 1 ? 's' : ''} à analyser avant chiffrage.`;
  }
  if (anomCount > 0) {
    return `${formatFREur(risque, 0)} · ${anomCount}${NBSP}anomalie${anomCount > 1 ? 's' : ''} contestable${anomCount > 1 ? 's' : ''}.`;
  }
  return `${formatFREur(risque, 0)} identifiés, contestations en cours.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards (3 signaux de la semaine sur ce site)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards : top anomalie · prochaine échéance/action · validation récente ou
 * statut conforme. Fallbacks business_errors si rien à afficher.
 */
export function buildSiteWeekCards({ site, anomalies = [], topReco, compliance, onOpenTab }) {
  const cards = [];

  // Card 1 : top anomalie de facturation (ou fallback)
  const activeAnomalies = Array.isArray(anomalies)
    ? anomalies.filter((a) => a && !a.resolved_at)
    : [];
  if (activeAnomalies.length > 0) {
    const top = activeAnomalies[0];
    const euros = top.impact_eur ?? top.amount_eur ?? top.impact ?? null;
    cards.push({
      id: `anom-${top.id || 'top'}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: top.title || top.description || 'Anomalie de facturation',
      body: euros
        ? `Impact estimé ${formatFREur(euros, 0)}. Preuve disponible dans l'onglet Factures.`
        : 'Écart détecté avec le shadow billing. Preuve disponible dans l\'onglet Factures.',
      footerLeft: top.source || 'shadow billing',
      footerRight: '⌘K',
      onClick: () => onOpenTab?.('factures'),
    });
  } else {
    cards.push(businessErrorFallback('site.no_anomalies', cards.length));
  }

  // Card 2 : top reco (ou fallback)
  if (topReco?.title || topReco?.name) {
    const impact = topReco.impact_eur ?? topReco.economy_eur ?? topReco.potential_eur ?? null;
    cards.push({
      id: `reco-${topReco.id || 'top'}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: topReco.title || topReco.name,
      body: impact
        ? `Économie potentielle estimée ${formatFREur(impact, 0)}/an.`
        : (topReco.description || 'Recommandation à examiner dans l\'onglet Actions.'),
      footerLeft: topReco.category || 'optimisation',
      footerRight: 'Sol peut préparer',
      onClick: () => onOpenTab?.('actions'),
    });
  } else {
    cards.push(businessErrorFallback('site.no_reco', cards.length));
  }

  // Card 3 : statut conformité (bonne nouvelle si conforme)
  const score = compliance?.overall ?? site?.compliance_score ?? null;
  if (score != null && score >= 75) {
    cards.push({
      id: `comp-${site?.id || 'site'}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: 'Trajectoire Décret Tertiaire solide',
      body: `Score ${score}/100. Aucune dérive critique cette semaine.`,
      footerLeft: 'moteur RegOps',
      footerRight: '✓ Clean',
      onClick: () => onOpenTab?.('conformite'),
    });
  } else if (score != null) {
    cards.push({
      id: `comp-${site?.id || 'site'}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: 'Plan conformité à activer',
      body: `Score ${score}/100. Détails et leviers dans l'onglet Conformité.`,
      footerLeft: 'moteur RegOps',
      footerRight: 'Plan requis',
      onClick: () => onOpenTab?.('conformite'),
    });
  } else {
    cards.push(businessErrorFallback('conformite.no_recent_validation', cards.length));
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Trajectoire DT → data SolTrajectoryChart
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Construit la data SolTrajectoryChart pour la trajectoire DT 2030 du site.
 * Lineup canonique : 2020 (référence) → 2024 (année actuelle) → 2030 (objectif -40%).
 * Fallback : retourne null si data insuffisante (le composant affichera un
 * business_errors patrimoine.collection_in_progress).
 */
export function adaptComplianceToTrajectory({ site, compliance }) {
  const current = compliance?.overall ?? site?.compliance_score ?? null;
  if (current == null) return null;
  // Objectif DT : 75+ (conforme) en 2030. On trace la progression attendue.
  const target = 75;
  const baseline = compliance?.baseline ?? Math.max(50, current - 12);
  // SolTrajectoryChart utilise `month` comme clé X (dataKey hardcodé).
  // On l'alimente avec des libellés d'année (2020, 2024, 2030) — recharts les
  // affiche tels quels et la progression est lisible même avec 3 points.
  return [
    { month: '2020', score: baseline, label: 'Référence' },
    { month: '2024', score: current, label: 'Aujourd\'hui' },
    { month: '2030', score: target, label: 'Objectif DT' },
  ];
}

/**
 * Benchmark EUI ADEME pour le site (wrapper autour getBenchmark pour usage unique).
 * Utile quand la valeur `benchmark` n'est pas déjà dans intensityData.
 */
export function resolveSiteBenchmark(site) {
  if (!site) return null;
  const bench = getBenchmark(site.usage || site.type);
  return bench > 0 ? bench : null;
}
