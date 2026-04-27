/**
 * PROMEOS — Labels centralisés Monitoring (FR).
 *
 * Source de vérité unique pour les libellés affichés côté monitoring
 * (page MonitoringPage + composants alert listing). Sprint 2 Vague B
 * ét6' (label_registries cross-vue, 27/04/2026).
 *
 * Doctrine : labels en français côté frontend uniquement. Le backend
 * (alert_engine.py) retourne des codes types snake_case ou UPPER_SNAKE
 * (`BASE_NUIT_ELEVEE`, `consumption_spike`...) — la traduction est ici.
 *
 * Note compromis EM (audit personas Vague A) : les KPI tooltips gardent
 * la formule technique en queue (P=E/dt, kWh/jour par °C, P95 95ᵉ
 * centile) pour ne pas appauvrir le power-user, tout en plaçant la
 * narrative humaine en tête.
 */

/**
 * 24 codes alertes monitoring → libellés FR. Couvre les 13 codes UPPER_SNAKE
 * du moteur historique + 11 variantes snake_case du nouveau moteur.
 *
 * Vague A ét5' déjargonnage : DOUBLONS_DST → "Doublons au passage à l'heure
 * d'été", P95_HAUSSE → "Pointe récurrente en hausse", DEPASSEMENT_PUISSANCE
 * → "Dépassement puissance souscrite". Reste FR-readable conservé (vocabulaire
 * métier EM : talon, signature climatique).
 */
export const MONITORING_ALERT_TYPE_LABELS = Object.freeze({
  // Codes UPPER_SNAKE (moteur historique)
  BASE_NUIT_ELEVEE: 'Base nuit élevée',
  WEEKEND_ANORMAL: 'Week-end anormal',
  DERIVE_TALON: 'Dérive du talon',
  PIC_ANORMAL: 'Pic anormal',
  P95_HAUSSE: 'Pointe récurrente en hausse',
  DEPASSEMENT_PUISSANCE: 'Dépassement puissance souscrite',
  RUPTURE_PROFIL: 'Rupture de profil',
  HORS_HORAIRES: 'Consommation hors horaires',
  COURBE_PLATE: 'Courbe plate',
  DONNEES_MANQUANTES: 'Données manquantes',
  DOUBLONS_DST: "Doublons au passage à l'heure d'été",
  VALEURS_NEGATIVES: 'Valeurs négatives',
  SENSIBILITE_CLIMATIQUE: 'Sensibilité climatique',
  // Variantes snake_case (moteur monitoring v2)
  off_hours_consumption: 'Consommation hors horaires',
  high_night_base: 'Base nuit élevée',
  power_risk: 'Risque dépassement puissance souscrite',
  weekend_anomaly: 'Anomalie week-end',
  high_base_load: 'Talon élevé',
  peak_anomaly: 'Pic anormal',
  profile_break: 'Rupture de profil',
  flat_curve: 'Courbe plate',
  missing_data: 'Données manquantes',
  climate_sensitivity: 'Sensibilité climatique',
});

/**
 * 5 KPI hero monitoring (Pmax / loadFactor / risk / quality / climate)
 * → tooltips narratifs avec formule technique préservée comme preuve
 * (compromis EM Vague A ét5' : ne pas appauvrir le power-user).
 *
 * Pattern : narrative humaine en tête → formule en queue. Anti-pattern
 * §6.3 levé sur formules brutes (P=E/dt, E_totale/(Pmax×heures)).
 */
export const MONITORING_KPI_TOOLTIPS = Object.freeze({
  pmax: 'Puissance maximale réellement appelée sur la période. Le P95 (95ᵉ centile) sert à neutraliser les pics ponctuels et représente la pointe récurrente. Calcul : puissance = énergie / durée.',
  loadFactor:
    'À quel point votre courbe est plate : 100 % = consommation parfaitement constante, 0 % = pic isolé sur fond nul. Calcul : énergie totale / (Pmax × heures de la période).',
  risk: 'Probabilité de dépasser votre puissance souscrite et déclencher une pénalité. Combine 4 signaux : ratio P95/puissance souscrite, fréquence des pointes, volatilité minute, dépassements observés.',
  quality:
    'Fiabilité de vos données de comptage : trous, doublons, valeurs négatives, valeurs aberrantes (outliers) et complétude globale.',
  climate:
    "À quel point votre conso suit la météo : pente kWh/jour par °C de la signature énergétique. Élevé = forte dépendance chauffage ou climatisation, opportunité d'optimisation thermique.",
});

/**
 * Helper text fallback : retourne le label canonique si présent,
 * sinon le code brut (pour codes types non encore narrativisés).
 */
export function monitoringAlertLabel(type) {
  return MONITORING_ALERT_TYPE_LABELS[type] || type;
}
