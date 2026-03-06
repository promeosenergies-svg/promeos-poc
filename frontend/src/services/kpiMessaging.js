/**
 * PROMEOS — C.4: Messages intelligents par KPI
 * Chaque KPI est accompagné d'un message contextuel + action recommandée.
 *
 * Usage :
 *   const msg = getKpiMessage('conformite', 75, { totalSites: 100, sitesAtRisk: 3 });
 *   // → { simple, expert, severity, action? }
 */

/**
 * @param {string} kpiId — identifiant du KPI
 * @param {number|string|null} value — valeur brute (avant formatage)
 * @param {object} ctx — contexte additionnel (totalSites, sitesAtRisk, etc.)
 * @returns {{ simple: string, expert: string, severity: string, action?: { label: string, path: string } }}
 */
export function getKpiMessage(kpiId, value, ctx = {}) {
  const v = typeof value === 'string' ? parseFloat(value) : value;
  const handler = HANDLERS[kpiId];
  if (!handler) return null;
  return handler(v, ctx);
}

// ── Handlers par KPI ────────────────────────────────────────────────────────

const HANDLERS = {
  // ── Cockpit executive KPIs ──────────────────────────────────────────────

  conformite: (v, ctx) => {
    const { totalSites = 0, sitesAtRisk = 0, sitesNonConformes = 0 } = ctx;
    if (v == null || isNaN(v)) {
      return {
        simple: 'Données insuffisantes pour calculer la conformité.',
        expert: 'Score unifié A.2 : Tertiaire 45% + BACS 30% + APER 25%. Aucune évaluation disponible.',
        severity: 'neutral',
        action: { label: 'Lancer un audit', path: '/conformite' },
      };
    }
    if (v >= 70) {
      return {
        simple: `Bonne conformité (${v}/100). ${sitesAtRisk > 0 ? `${sitesAtRisk} site${sitesAtRisk > 1 ? 's' : ''} à surveiller.` : 'Continuez ainsi.'}`,
        expert: `Score ${v}/100 (DT 45% + BACS 30% + APER 25%). ${sitesNonConformes} non conformes, ${sitesAtRisk} à risque sur ${totalSites} sites.`,
        severity: 'ok',
      };
    }
    if (v >= 40) {
      return {
        simple: `Conformité moyenne (${v}/100). ${sitesAtRisk + sitesNonConformes} site${(sitesAtRisk + sitesNonConformes) > 1 ? 's' : ''} nécessite${(sitesAtRisk + sitesNonConformes) > 1 ? 'nt' : ''} attention.`,
        expert: `Score ${v}/100 (DT 45% + BACS 30% + APER 25%). ${sitesNonConformes} non conformes sur ${totalSites}. Priorisez les échéances proches.`,
        severity: 'warn',
        action: { label: 'Voir les sites à risque', path: '/conformite' },
      };
    }
    return {
      simple: `Conformité faible (${v}/100). Actions urgentes requises.`,
      expert: `Score ${v}/100 seulement (DT 45% + BACS 30% + APER 25%). ${sitesNonConformes} non conformes sur ${totalSites}. Risque d'amende.`,
      severity: 'crit',
      action: { label: 'Plan de mise en conformité', path: '/conformite' },
    };
  },

  risque: (v, ctx) => {
    const { sitesAtRisk = 0 } = ctx;
    if (v == null || isNaN(v)) {
      return {
        simple: 'Risque financier non évalué.',
        expert: 'Pas de données suffisantes pour quantifier le risque.',
        severity: 'neutral',
      };
    }
    if (v === 0) {
      return {
        simple: 'Aucun risque financier identifié. Situation maîtrisée.',
        expert: 'Risque = 0 €. Tous les sites sont conformes ou couverts.',
        severity: 'ok',
      };
    }
    if (v < 10000) {
      return {
        simple: `Risque modéré. ${sitesAtRisk} site${sitesAtRisk > 1 ? 's' : ''} concerné${sitesAtRisk > 1 ? 's' : ''}.`,
        expert: `Risque total ${v.toLocaleString('fr-FR')} €. ${sitesAtRisk} sites contributeurs.`,
        severity: 'warn',
        action: { label: 'Voir le détail', path: '/actions' },
      };
    }
    return {
      simple: `Risque élevé. Traitez les ${sitesAtRisk} sites prioritaires.`,
      expert: `Risque total ${v.toLocaleString('fr-FR')} €. ${sitesAtRisk} sites. Actions correctives urgentes.`,
      severity: 'crit',
      action: { label: 'Actions prioritaires', path: '/actions' },
    };
  },

  maturite: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Score de maturité non disponible.',
        expert: 'Données insuffisantes pour le calcul de maturité.',
        severity: 'neutral',
      };
    }
    if (v >= 70) {
      return {
        simple: 'Bonne maturité. Vos données et processus sont bien en place.',
        expert: `Maturité ${v}%. Données, conformité et actions bien couvertes.`,
        severity: 'ok',
      };
    }
    if (v >= 40) {
      return {
        simple: 'Maturité en progression. Complétez vos données pour progresser.',
        expert: `Maturité ${v}%. Axes d'amélioration : couverture données et suivi actions.`,
        severity: 'warn',
        action: { label: 'Compléter les données', path: '/consommations/import' },
      };
    }
    return {
      simple: 'Maturité faible. Importez vos données pour débloquer les analyses.',
      expert: `Maturité ${v}%. Données manquantes sur plusieurs axes. Import prioritaire.`,
      severity: 'crit',
      action: { label: 'Importer des données', path: '/consommations/import' },
    };
  },

  couverture: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Couverture des données non calculée.',
        expert: 'Aucune brique de données évaluée.',
        severity: 'neutral',
      };
    }
    if (v >= 80) {
      return {
        simple: 'Excellente couverture. Vos analyses sont fiables.',
        expert: `Couverture ${v}%. Les 5 briques de données sont bien alimentées.`,
        severity: 'ok',
      };
    }
    if (v >= 50) {
      return {
        simple: 'Couverture partielle. Certaines analyses sont estimées.',
        expert: `Couverture ${v}%. Briques manquantes : vérifiez compteurs et contrats.`,
        severity: 'warn',
        action: { label: 'Voir les manques', path: '/consommations/import' },
      };
    }
    return {
      simple: 'Couverture insuffisante. Importez plus de données.',
      expert: `Couverture ${v}% seulement. KPIs peu fiables. Import critique.`,
      severity: 'crit',
      action: { label: 'Importer', path: '/consommations/import' },
    };
  },

  // ── Billing KPIs ────────────────────────────────────────────────────────

  anomalies: (v, ctx) => {
    const { totalLoss = 0 } = ctx;
    if (v == null || isNaN(v) || v === 0) {
      return {
        simple: 'Aucune anomalie de facturation détectée.',
        expert: 'Moteur d\'audit : 0 anomalie. Factures conformes aux attendus.',
        severity: 'ok',
      };
    }
    if (v <= 3) {
      return {
        simple: `${v} anomalie${v > 1 ? 's' : ''} à vérifier.`,
        expert: `${v} anomalie${v > 1 ? 's' : ''}, perte estimée ${totalLoss.toLocaleString('fr-FR')} €.`,
        severity: 'warn',
        action: { label: 'Analyser', path: '/bill-intel' },
      };
    }
    return {
      simple: `${v} anomalies détectées. Vérification urgente recommandée.`,
      expert: `${v} anomalies, perte estimée ${totalLoss.toLocaleString('fr-FR')} €. Shadow billing actif.`,
      severity: 'crit',
      action: { label: 'Voir les anomalies', path: '/bill-intel' },
    };
  },

  billing_coverage: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Couverture facturation non évaluée.',
        expert: 'Aucune facture importée pour cette période.',
        severity: 'neutral',
        action: { label: 'Importer', path: '/consommations/import' },
      };
    }
    const pct = Math.round(v * 100);
    if (pct >= 90) {
      return {
        simple: 'Bonne couverture facturation. Analyses fiables.',
        expert: `${pct}% des mois couverts par des factures importées.`,
        severity: 'ok',
      };
    }
    if (pct >= 60) {
      return {
        simple: `${100 - pct}% des mois sans facture. Importez les manquantes.`,
        expert: `Couverture ${pct}%. ${100 - pct}% de mois manquants = analyses partielles.`,
        severity: 'warn',
        action: { label: 'Compléter', path: '/consommations/import' },
      };
    }
    return {
      simple: `Couverture très faible. La plupart des mois manquent.`,
      expert: `Couverture ${pct}% seulement. Analyses non fiables sans données complètes.`,
      severity: 'crit',
      action: { label: 'Importer les factures', path: '/consommations/import' },
    };
  },

  // ── Monitoring / Performance KPIs ───────────────────────────────────────

  data_quality_score: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Qualité des données non évaluée.',
        expert: 'Score DQ non calculable (pas de données).',
        severity: 'neutral',
      };
    }
    if (v >= 80) {
      return {
        simple: 'Données de bonne qualité. Analyses fiables.',
        expert: `Score qualité ${v}/100. Complétude et fraîcheur conformes.`,
        severity: 'ok',
      };
    }
    if (v >= 50) {
      return {
        simple: 'Qualité moyenne. Certains relevés manquent.',
        expert: `Score qualité ${v}/100. Vérifiez la fraîcheur des compteurs.`,
        severity: 'warn',
      };
    }
    return {
      simple: 'Qualité insuffisante. Vérifiez les connexions compteurs.',
      expert: `Score qualité ${v}/100. Données incomplètes ou obsolètes.`,
      severity: 'crit',
    };
  },

  off_hours_ratio: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Consommation hors horaires non analysée.',
        expert: 'Ratio hors-horaires non calculable.',
        severity: 'neutral',
      };
    }
    const pct = Math.round(v * 100);
    if (pct <= 15) {
      return {
        simple: 'Peu de consommation hors horaires. Bon pilotage.',
        expert: `${pct}% de conso hors-horaires. Programmation efficace.`,
        severity: 'ok',
      };
    }
    if (pct <= 35) {
      return {
        simple: 'Consommation hors horaires significative. Vérifiez la programmation.',
        expert: `${pct}% de conso hors-horaires. Potentiel d'économie par ajustement GTC.`,
        severity: 'warn',
      };
    }
    return {
      simple: 'Consommation excessive hors horaires. Économies possibles.',
      expert: `${pct}% hors-horaires. Programmation défaillante ou équipements non coupés.`,
      severity: 'crit',
      action: { label: 'Voir les usages', path: '/usages-horaires' },
    };
  },

  load_factor: (v, ctx) => {
    const { archetype = 'default' } = ctx;
    if (v == null || isNaN(v)) {
      return {
        simple: 'Facteur de charge non disponible.',
        expert: 'Load factor non calculable (données insuffisantes).',
        severity: 'neutral',
      };
    }
    if (v >= 50) {
      return {
        simple: 'Bon facteur de charge. Consommation bien lissée.',
        expert: `LF ${v}% (profil ${archetype}). Pas de pics excessifs.`,
        severity: 'ok',
      };
    }
    if (v >= 25) {
      return {
        simple: 'Facteur de charge moyen. Pics de consommation à surveiller.',
        expert: `LF ${v}% (profil ${archetype}). Ratio pic/moy élevé, optimisez les appels de puissance.`,
        severity: 'warn',
      };
    }
    return {
      simple: 'Facteur de charge faible. Appels de puissance très irréguliers.',
      expert: `LF ${v}% seulement (profil ${archetype}). Risque de dépassement TURPE. Lissage recommandé.`,
      severity: 'crit',
      action: { label: 'Analyser les pics', path: '/monitoring' },
    };
  },

  night_ratio: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Ratio nuit non disponible.',
        expert: 'Ratio consommation nocturne non calculable.',
        severity: 'neutral',
      };
    }
    const pct = Math.round(v * 100);
    if (pct <= 20) {
      return {
        simple: 'Faible consommation nocturne. Bonne maîtrise.',
        expert: `${pct}% de conso entre 22h-6h. Talon nuit maîtrisé.`,
        severity: 'ok',
      };
    }
    if (pct <= 40) {
      return {
        simple: 'Consommation nocturne significative. Vérifiez les équipements.',
        expert: `${pct}% de conso nocturne. Vérifiez CVC, éclairage, serveurs.`,
        severity: 'warn',
      };
    }
    return {
      simple: 'Consommation nocturne excessive. Équipements probablement non coupés.',
      expert: `${pct}% de conso nocturne. Talon anormalement élevé. Audit GTC recommandé.`,
      severity: 'crit',
      action: { label: 'Voir profil nuit', path: '/monitoring' },
    };
  },

  weekend_ratio: (v) => {
    if (v == null || isNaN(v)) {
      return {
        simple: 'Ratio week-end non disponible.',
        expert: 'Ratio consommation week-end non calculable.',
        severity: 'neutral',
      };
    }
    const pct = Math.round(v * 100);
    if (pct <= 15) {
      return {
        simple: 'Très faible consommation le week-end. Bonne gestion.',
        expert: `${pct}% de conso week-end vs semaine. Arrêt efficace.`,
        severity: 'ok',
      };
    }
    if (pct <= 35) {
      return {
        simple: 'Consommation week-end notable. Certains équipements restent actifs.',
        expert: `${pct}% de conso week-end. Vérifiez programmation GTC et relance lundi.`,
        severity: 'warn',
      };
    }
    return {
      simple: 'Consommation week-end excessive. Économies significatives possibles.',
      expert: `${pct}% de conso week-end. Fonctionnement quasi continu détecté. Programmation horaire défaillante.`,
      severity: 'crit',
      action: { label: 'Voir profil week-end', path: '/monitoring' },
    };
  },

  kwh_m2: (v, ctx) => {
    const { benchmark = 145, usage = 'bureaux' } = ctx;
    if (v == null || isNaN(v)) {
      return {
        simple: 'Intensité énergétique non calculée.',
        expert: 'kWh/m²/an non disponible (surface ou conso manquante).',
        severity: 'neutral',
      };
    }
    const delta = Math.round(((v - benchmark) / benchmark) * 100);
    if (v <= benchmark) {
      return {
        simple: `${Math.abs(delta)}% sous la moyenne du secteur. Performance exemplaire.`,
        expert: `${v} kWh/m²/an vs ${benchmark} (réf. ${usage}). ${Math.abs(delta)}% sous la moyenne.`,
        severity: 'ok',
      };
    }
    if (delta <= 30) {
      return {
        simple: `${delta}% au-dessus de la moyenne. Marge d'amélioration.`,
        expert: `${v} kWh/m²/an vs ${benchmark} (réf. ${usage}). +${delta}%.`,
        severity: 'warn',
      };
    }
    return {
      simple: `${delta}% au-dessus de la moyenne. Économies significatives possibles.`,
      expert: `${v} kWh/m²/an vs ${benchmark} (réf. ${usage}). +${delta}%. Audit recommandé.`,
      severity: 'crit',
      action: { label: 'Analyser la conso', path: '/consommations/explorer' },
    };
  },
};

/**
 * Liste des KPI IDs supportés.
 */
export const SUPPORTED_KPIS = Object.keys(HANDLERS);
