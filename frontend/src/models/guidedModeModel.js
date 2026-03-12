/**
 * guidedModeModel.js — Pure model for Guided Mode, Next Best Action, Données metrics.
 * Zero React imports — fully testable in isolation.
 *
 * Exports:
 *   GUIDED_STEPS                                       — 7-step definitions
 *   computeGuidedSteps(bundle, sitesData, summary, s)  — GuidedStep[]
 *   computeNextBestAction(bundle, sitesData, summary, s, _now) — NextBestAction
 *   computeDonneesMetrics(sitesData, dqResults, s)     — DonneesMetrics
 */

// ── Step definitions ─────────────────────────────────────────────────────
export const GUIDED_STEPS = [
  {
    id: 'assujettissement',
    order: 1,
    label: 'Assujettissement',
    description: "Identifiez les réglementations qui s'appliquent à vos sites.",
    cta: 'Voir les obligations',
    ctaTarget: { tab: 'obligations' },
  },
  {
    id: 'donnees',
    order: 2,
    label: 'Données',
    blocking: true,
    description: 'Vérifiez la qualité et complétude des données.',
    cta: 'Vérifier les données',
    ctaTarget: { tab: 'donnees' },
  },
  {
    id: 'deadlines',
    order: 3,
    label: 'Échéances',
    description: 'Visualisez les prochaines échéances réglementaires.',
    cta: 'Voir les échéances',
    ctaTarget: { tab: 'obligations' },
  },
  {
    id: 'plan',
    order: 4,
    label: "Plan d'action",
    description: 'Construisez votre plan de mise en conformité.',
    cta: 'Voir le plan',
    ctaTarget: { tab: 'execution' },
  },
  {
    id: 'cee_gouvernance',
    order: 5,
    label: 'CEE & gouvernance',
    description: 'Gérez les dossiers CEE et la gouvernance énergétique.',
    cta: 'Gérer les dossiers',
    ctaTarget: { path: '/compliance/pipeline' },
  },
  {
    id: 'preuves',
    order: 6,
    label: 'Preuves',
    description: 'Rassemblez les preuves de conformité.',
    cta: 'Joindre les preuves',
    ctaTarget: { tab: 'preuves' },
  },
  {
    id: 'mv',
    order: 7,
    label: 'M&V',
    description: 'Suivez la mesure et vérification des économies.',
    cta: 'Accéder au suivi',
    ctaTarget: { path: '/compliance/pipeline' },
  },
];

// ── Internal: evaluate a single step ─────────────────────────────────────
function evalStep(stepId, sitesData, summary, signals) {
  const {
    obligations = [],
    actionableFindings = [],
    proofFiles = {},
    workPackages,
    mvSummary,
  } = signals;

  switch (stepId) {
    case 'assujettissement':
      if (!sitesData?.length) return 'pending';
      if (obligations.length > 0 || summary?.total_findings > 0) return 'complete';
      return 'in_progress';

    case 'donnees':
      if (!sitesData?.length) return 'pending';
      if (sitesData.some((s) => s.data_quality_gate === 'BLOCKED')) return 'blocked';
      if (sitesData.some((s) => s.data_quality_gate === 'WARNING')) return 'in_progress';
      return 'complete';

    case 'deadlines':
      if (obligations.length === 0) return 'pending';
      return obligations.every(
        (o) => o.echeance || o.statut === 'conforme' || o.statut === 'hors_perimetre'
      )
        ? 'complete'
        : 'in_progress';

    case 'plan':
      if (obligations.length === 0) return 'pending';
      return actionableFindings.length === 0 ? 'complete' : 'in_progress';

    case 'cee_gouvernance':
      if (!workPackages || workPackages.length === 0) return 'pending';
      return workPackages.every(
        (wp) => !wp.cee_step || wp.cee_step === 'submitted' || wp.cee_step === 'validated'
      )
        ? 'complete'
        : 'in_progress';

    case 'preuves':
      if (obligations.length === 0) return 'pending';
      return obligations.every((o) => (proofFiles[o.id]?.length || 0) > 0)
        ? 'complete'
        : 'in_progress';

    case 'mv':
      if (!mvSummary) return 'pending';
      return mvSummary.has_data ? 'complete' : 'in_progress';

    default:
      return 'pending';
  }
}

// ── computeGuidedSteps ───────────────────────────────────────────────────
/**
 * @param {object|null} bundle
 * @param {object[]} sitesData
 * @param {object|null} summary
 * @param {object} signals - { obligations, actionableFindings, proofFiles, workPackages, mvSummary }
 * @returns {GuidedStep[]} 7 steps with status
 */
export function computeGuidedSteps(bundle, sitesData, summary, signals = {}) {
  const donneesStatus = evalStep('donnees', sitesData, summary, signals);
  const donneesBlocked = donneesStatus === 'blocked';

  return GUIDED_STEPS.map((def) => {
    let status;
    if (def.id === 'donnees') {
      status = donneesStatus;
    } else if (donneesBlocked && def.order > 2) {
      status = 'blocked';
    } else {
      status = evalStep(def.id, sitesData, summary, signals);
    }
    return { ...def, status };
  });
}

// ── computeNextBestAction ────────────────────────────────────────────────
/**
 * Deterministic waterfall: first match wins.
 * @param {object|null} bundle
 * @param {object[]} sitesData
 * @param {object|null} summary
 * @param {object} signals
 * @param {Date} _now - injectable for test determinism
 * @returns {NextBestAction}
 */
export function computeNextBestAction(bundle, sitesData, summary, signals = {}, _now = new Date()) {
  const { obligations = [], actionableFindings = [], proofFiles = {} } = signals;

  // P1: Data blocker
  if (sitesData?.some((s) => s.data_quality_gate === 'BLOCKED')) {
    return {
      id: 'nba-data-blocker',
      title: 'Complétez les données manquantes',
      description: 'Des données essentielles manquent pour évaluer la conformité de vos sites.',
      severity: 'critical',
      ctaLabel: 'Compléter les données',
      ctaAction: { type: 'tab', tab: 'donnees' },
      icon: 'Database',
    };
  }

  // P2: Close deadline (< 90 days)
  const nowMs = _now.getTime();
  const closeDeadlines = obligations
    .filter((o) => o.echeance && o.statut !== 'conforme' && o.statut !== 'hors_perimetre')
    .filter((o) => {
      const d = new Date(o.echeance).getTime();
      return d > nowMs && d - nowMs < 90 * 86400000;
    })
    .sort((a, b) => a.echeance.localeCompare(b.echeance));

  if (closeDeadlines.length > 0) {
    const closest = closeDeadlines[0];
    return {
      id: `nba-deadline-${closest.code}`,
      title: `Préparez l'échéance ${closest.regulation || closest.code}`,
      description: `Échéance le ${closest.echeance} — ${closest.sites_concernes || 0} site(s) concerné(s).`,
      severity: 'high',
      ctaLabel: "Voir l'obligation",
      ctaAction: { type: 'tab', tab: 'obligations' },
      icon: 'Clock',
    };
  }

  // P3: Missing proofs for conforme obligations
  const conformeNoProof = obligations
    .filter((o) => o.statut === 'conforme')
    .filter((o) => !(proofFiles[o.id]?.length > 0));
  if (conformeNoProof.length > 0) {
    return {
      id: 'nba-missing-proofs',
      title: `${conformeNoProof.length} preuve${conformeNoProof.length > 1 ? 's' : ''} manquante${conformeNoProof.length > 1 ? 's' : ''}`,
      description: "Des obligations conformes n'ont pas encore de preuve jointe.",
      severity: 'medium',
      ctaLabel: 'Joindre les preuves',
      ctaAction: { type: 'tab', tab: 'preuves' },
      icon: 'FileText',
    };
  }

  // P4: Actionable findings — count by distinct regulation for clarity
  if (actionableFindings.length > 0) {
    const hasCritical = actionableFindings.some((f) => f.severity === 'critical');
    const regs = new Set(actionableFindings.map((f) => f.regulation));
    const regCount = regs.size;
    const findingCount = actionableFindings.length;
    return {
      id: 'nba-findings',
      title: `${findingCount} constat${findingCount > 1 ? 's' : ''} à traiter sur ${regCount} obligation${regCount > 1 ? 's' : ''}`,
      description: 'Des constats nécessitent une action corrective.',
      severity: hasCritical ? 'critical' : 'high',
      ctaLabel: "Voir le plan d'exécution",
      ctaAction: { type: 'tab', tab: 'execution' },
      icon: 'AlertTriangle',
    };
  }

  // P5: All good
  return {
    id: 'nba-all-good',
    title: 'Tout est sous contrôle',
    description: 'Aucune action urgente. Continuez la surveillance.',
    severity: 'low',
    ctaLabel: 'Explorer',
    ctaAction: { type: 'tab', tab: 'obligations' },
    icon: 'CheckCircle',
  };
}

// ── computeDonneesMetrics ────────────────────────────────────────────────
/**
 * @param {object[]} sitesData
 * @param {{ coverage_pct?, confidence_score? }[]} dataQualityResults
 * @param {{ billingMonthCount? }} signals
 * @returns {DonneesMetrics}
 */
export function computeDonneesMetrics(sitesData = [], dataQualityResults = [], signals = {}) {
  // Complétude: average coverage_pct from DQ results, fallback to estimating from sitesData
  let completude_pct = 0;
  if (dataQualityResults.length > 0) {
    const sum = dataQualityResults.reduce((s, dq) => s + (dq.coverage_pct || 0), 0);
    completude_pct = Math.round(sum / dataQualityResults.length);
  } else if (sitesData.length > 0) {
    // Fallback: estimate from site-level fields
    const filledCount = sitesData.filter(
      (s) => s.findings?.length > 0 || s.conso_kwh_an || s.surface_m2
    ).length;
    completude_pct = Math.round((filledCount / sitesData.length) * 100);
  }

  // Confiance
  const avgConfidence =
    dataQualityResults.length > 0
      ? dataQualityResults.reduce((s, dq) => s + (dq.confidence_score || 0), 0) /
        dataQualityResults.length
      : completude_pct >= 80
        ? 75
        : completude_pct >= 50
          ? 50
          : 25;

  let confiance_level, confiance_label;
  if (avgConfidence >= 70) {
    confiance_level = 'high';
    confiance_label = 'Élevée';
  } else if (avgConfidence >= 40) {
    confiance_level = 'medium';
    confiance_label = 'Moyenne';
  } else {
    confiance_level = 'low';
    confiance_label = 'Faible';
  }

  // Couverture factures
  const billingMonths = signals.billingMonthCount ?? 0;
  const couverture_factures_cible = 24;

  // Gaps
  const gaps = [];
  if (completude_pct < 80) {
    gaps.push({
      id: 'patrimoine_incomplet',
      label: 'Données patrimoine incomplètes',
      ctaPath: '/patrimoine',
      ctaLabel: 'Compléter le patrimoine',
    });
  }
  if (sitesData.length > 0 && sitesData.every((s) => !s.conso_kwh_an)) {
    gaps.push({
      id: 'conso_manquante',
      label: 'Consommations manquantes',
      ctaPath: '/consommations',
      ctaLabel: 'Importer les consommations',
    });
  }
  if (billingMonths < couverture_factures_cible) {
    gaps.push({
      id: 'factures_insuffisantes',
      label: 'Historique factures insuffisant',
      ctaPath: '/factures',
      ctaLabel: "Compléter l'historique",
    });
  }

  return {
    completude_pct,
    confiance_level,
    confiance_label,
    couverture_factures_mois: billingMonths,
    couverture_factures_cible,
    gaps,
  };
}
