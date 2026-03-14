/**
 * PROMEOS — KPI Labels Simple/Expert
 * Mode Simple : langage metier, comprehensible sans formation
 * Mode Expert : terminologie technique standard
 */
export const KPI_LABELS = {
  // Monitoring / Performance
  pmax_kw: {
    simple: 'Pic de puissance',
    expert: 'Puissance maximale (Pmax)',
    unit: 'kW',
  },
  p95_kw: {
    simple: 'Pointe puissance',
    expert: 'P95 puissance (percentile 95)',
    unit: 'kW',
  },
  pbase_kw: {
    simple: 'Consommation minimum',
    expert: 'Talon (baseload P10)',
    unit: 'kW',
  },
  pmean_kw: {
    simple: 'Puissance moyenne',
    expert: 'Puissance moyenne (Pmoy)',
    unit: 'kW',
  },
  load_factor: {
    simple: 'Taux d\u2019utilisation',
    expert: 'Facteur de charge (Pmoy/Pmax)',
    unit: '%',
  },
  off_hours_ratio: {
    simple: 'Part hors horaires',
    expert: 'Ratio hors-horaires d\u2019activite',
    unit: '%',
  },
  off_hours_kwh: {
    simple: 'Gaspillage estime',
    expert: 'Consommation hors-horaires',
    unit: 'kWh',
  },
  night_ratio: {
    simple: 'Conso. nocturne',
    expert: 'Ratio nuit (22h-6h / 6h-22h)',
    unit: '%',
  },
  weekend_ratio: {
    simple: 'Part weekend',
    expert: 'Ratio samedi+dimanche',
    unit: '%',
  },
  data_quality_score: {
    simple: 'Fiabilité des données',
    expert: 'Score qualité données (DQ)',
    unit: '/100',
  },
  risk_power_score: {
    simple: 'Risque depassement',
    expert: 'Score risque puissance',
    unit: '/100',
  },
  total_kwh: {
    simple: 'Conso. totale',
    expert: 'Conso. totale',
    unit: 'kWh',
  },
  kwh_m2: {
    simple: 'Intensité énergétique',
    expert: 'Ratio kWh/m\u00B2/an',
    unit: 'kWh/m\u00B2',
  },
  behavior_score: {
    simple: 'Score comportemental',
    expert: 'Behavior score (4 penalites)',
    unit: '/100',
  },
  // Signature energetique
  r_squared: {
    simple: 'Fiabilite du modele',
    expert: 'Coefficient R\u00B2 (regression)',
    unit: '',
  },
  heating_slope: {
    simple: 'Sensibilite au froid',
    expert: 'Pente chauffage (kWh/\u00B0C)',
    unit: 'kWh/\u00B0C',
  },
  cooling_slope: {
    simple: 'Sensibilite a la chaleur',
    expert: 'Pente refroidissement (kWh/\u00B0C)',
    unit: 'kWh/\u00B0C',
  },
  balance_point_heat: {
    simple: 'Seuil de chauffage',
    expert: 'Point d\u2019equilibre chaud (\u00B0C)',
    unit: '\u00B0C',
  },
  balance_point_cool: {
    simple: 'Seuil de climatisation',
    expert: 'Point d\u2019equilibre froid (\u00B0C)',
    unit: '\u00B0C',
  },
  // CO2
  total_kgco2e: {
    simple: 'Total émissions',
    expert: 'Total émissions',
    unit: 'kgCO\u2082e',
  },
  total_tco2e: {
    simple: 'Emissions CO\u2082',
    expert: 'Emissions totales (tCO\u2082e)',
    unit: 'tCO\u2082e',
  },
  // Explorer / InsightsPanel
  avg_per_day: {
    simple: 'Moyenne journaliere',
    expert: 'Moyenne / jour',
    unit: 'kWh/j',
  },
  anomaly_count: {
    simple: 'Anomalies detectees',
    expert: 'Anomalies detectees (> P99)',
    unit: '',
  },
  p05_kw: {
    simple: 'Consommation plancher',
    expert: 'Talon P05 (percentile 5)',
    unit: 'kWh',
  },
  // Monitoring extras
  climate_sensitivity: {
    simple: 'Sensibilite climatique',
    expert: 'Sensibilite climatique (kWh/j)/\u00B0C',
    unit: '(kWh/j)/\u00B0C',
  },
};

/**
 * Retourne le label adapte au mode.
 * @param {string} kpiId
 * @param {boolean} isExpert
 * @returns {string}
 */
export function getKpiLabel(kpiId, isExpert = false) {
  const entry = KPI_LABELS[kpiId];
  if (!entry) return kpiId;
  return isExpert ? entry.expert : entry.simple;
}

/**
 * Retourne l'unite du KPI.
 */
export function getKpiUnit(kpiId) {
  return KPI_LABELS[kpiId]?.unit || '';
}
