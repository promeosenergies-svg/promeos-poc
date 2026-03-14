/**
 * PROMEOS — Evidence V0 fixtures
 * Mock evidence objects for Cockpit + Explorer integration.
 */
import { buildEvidence } from './evidence';

export function evidenceConformite(scopeLabel, meta = null) {
  const w = meta?.framework_weights;
  const dtPct = w ? Math.round((w.tertiaire_operat ?? 0.45) * 100) : 45;
  const bacsPct = w ? Math.round((w.bacs ?? 0.3) * 100) : 30;
  const aperPct = w ? Math.round((w.aper ?? 0.25) * 100) : 25;
  const maxPenalty = meta?.critical_penalty?.max_pts ?? 20;

  return buildEvidence({
    id: 'exec-conformite',
    title: 'Score de conformité',
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Moteur RegOps — 3 réglementations',
        confidence: 'high',
        details: 'Évaluation déterministe Tertiaire (DT), BACS, APER.',
        freshness: 'Recalculé à chaque chargement du cockpit',
        links: [{ label: 'Voir RegOps', href: '/regops' }],
      },
      {
        kind: 'manual',
        label: 'Données patrimoniales',
        confidence: 'medium',
        details: 'Surface, usage, puissance CVC — importées via HELIOS.',
        links: [{ label: 'Patrimoine', href: '/patrimoine' }],
      },
    ],
    method: [
      `Score = moyenne pondérée DT (${dtPct}%) + BACS (${bacsPct}%) + APER (${aperPct}%) − pénalité findings critiques (max −${maxPenalty} pts).`,
      'Statut par site : pire statut parmi Décret Tertiaire et BACS.',
    ],
    assumptions: [
      'Les données patrimoniales (surface, usage) sont à jour.',
      "Aucun audit externe n'est intégré — évaluation interne uniquement.",
    ],
  });
}

export function evidenceRisque(scopeLabel, risqueEur) {
  return buildEvidence({
    id: 'exec-risque',
    title: 'Risque financier estimé',
    valueLabel: risqueEur != null ? `${Math.round(risqueEur / 1000)} k€` : null,
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Estimation heuristique V1',
        confidence: 'medium',
        details: 'Risque = somme des risque_eur par site non conforme.',
        freshness: 'Calculé dynamiquement',
      },
      {
        kind: 'calc',
        label: 'Findings réglementaires',
        confidence: 'high',
        details: "Chaque finding porte un risque unitaire basé sur la sévérité et l'urgence.",
        links: [{ label: "Plan d'action", href: '/action-plan' }],
      },
    ],
    method: [
      'Somme des champs risque_eur de chaque site (heuristique V1).',
      'Risque unitaire par finding = sévérité × urgence × barème réglementaire.',
      'Pondération : non conforme = 100%, à risque = 50%.',
    ],
    assumptions: [
      'Barèmes basés sur les sanctions théoriques maximales (Décret Tertiaire, BACS).',
      "Le risque réel dépend de l'application effective des sanctions par les autorités.",
    ],
  });
}

export function evidenceMaturite(scopeLabel) {
  return buildEvidence({
    id: 'exec-maturite',
    title: 'Score de maturité',
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Modèle de maturité PROMEOS',
        confidence: 'high',
        details: 'Évaluation sur 5 axes : données, conformité, actions, contrats, pilotage.',
        freshness: 'Recalculé à chaque chargement',
      },
      {
        kind: 'manual',
        label: 'Données importées',
        confidence: 'medium',
        details: 'Complétude des imports : compteurs, factures, contrats, patrimoine.',
        links: [{ label: 'Activation', href: '/activation' }],
      },
    ],
    method: [
      'Score = moyenne pondérée des 5 axes de maturité.',
      'Chaque axe : 0-100% selon le taux de complétion des données et actions.',
      'Pondérations : données 30%, conformité 25%, actions 20%, contrats 15%, pilotage 10%.',
    ],
    assumptions: [
      "Le score reflète la complétude des données dans PROMEOS, pas la maturité réelle de l'organisation.",
      'Importer plus de données fait progresser le score automatiquement.',
    ],
  });
}

export function evidenceCouverture(scopeLabel) {
  return buildEvidence({
    id: 'exec-couverture',
    title: 'Couverture des données',
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Briques de données PROMEOS',
        confidence: 'high',
        details: '5 briques : compteurs, factures, contrats, patrimoine, conformité.',
        freshness: 'Temps réel',
      },
    ],
    method: [
      'Couverture = nombre de briques alimentées / 5 briques totales × 100.',
      'Une brique est « alimentée » si au moins un enregistrement existe pour le périmètre courant.',
      'Le % reflète la diversité des sources, pas la profondeur de chacune.',
    ],
    assumptions: [
      'Toutes les briques ont le même poids dans le calcul.',
      'Un seul enregistrement suffit pour considérer une brique comme couverte.',
    ],
  });
}

export function evidenceKwhTotal(scopeLabel, periodLabel, kwhValue) {
  return buildEvidence({
    id: 'conso-kwh-total',
    title: `kWh total${periodLabel ? ` — ${periodLabel}` : ''}`,
    valueLabel: kwhValue,
    scopeLabel,
    periodLabel,
    sources: [
      {
        kind: 'enedis',
        label: 'Courbe de charge Enedis',
        confidence: 'high',
        details: 'Index horaires ou 15 min (selon disponibilité compteur).',
        freshness: 'Données seed HELIOS — 730 jours horaires',
        links: [{ label: 'Voir les compteurs', href: '/connectors' }],
      },
      {
        kind: 'calc',
        label: 'Agrégation PROMEOS',
        confidence: 'high',
        details: 'Somme des relevés filtrés par période et fréquence.',
      },
    ],
    method: [
      'Somme des mesures horaires (ou 15 min) sur la période sélectionnée.',
      "Filtrage par fréquence compatible (exclusion des lectures MONTHLY dans l'agrégation horaire).",
      'Multi-site : somme des totaux par site sélectionné.',
    ],
    assumptions: [
      'Données Enedis considérées comme source de vérité (compteur certifié).',
      'En cas de trou de données, aucune interpolation — le total peut être sous-estimé.',
    ],
  });
}

export function evidenceCO2e(scopeLabel, periodLabel, co2Value) {
  return buildEvidence({
    id: 'conso-co2e',
    title: `Émissions CO2e${periodLabel ? ` — ${periodLabel}` : ''}`,
    valueLabel: co2Value,
    scopeLabel,
    periodLabel,
    sources: [
      {
        kind: 'enedis',
        label: 'Consommation kWh (Enedis)',
        confidence: 'high',
        details: 'Base de calcul : kWh total sur la période.',
      },
      {
        kind: 'calc',
        label: "Facteur d'émission ADEME 2024",
        confidence: 'high',
        details: 'Mix électrique France : 0,052 kgCO2e/kWh.',
        links: [{ label: 'Référentiel ADEME', href: '/kb' }],
      },
    ],
    method: [
      'CO2e = kWh total × facteur ADEME (0,052 kgCO2e/kWh).',
      'Facteur unique pour le mix électrique français moyen.',
      'Pas de distinction heure creuse / heure pleine (facteur moyen).',
    ],
    assumptions: [
      'Facteur ADEME 2024 constant sur toute la période.',
      "Ne tient pas compte de l'autoconsommation PV éventuelle.",
    ],
  });
}
