/**
 * PROMEOS — UsagesHorairesSol presenters (Lot 2 Phase 6, Pattern A compact)
 *
 * Helpers purs pour l'injection Sol compacte en haut de /usages-horaires.
 *
 * API consommée (parent ConsumptionContextPage.jsx) :
 *   getConsumptionContext(siteId, days=30) → {
 *     profile: { baseload_kw, total_kwh, ... },
 *     anomalies: {
 *       behavior_score (0-100),
 *       kpis: { offhours_pct, night_ratio, weekend_ratio, drift_pct }
 *     },
 *     activity: { schedule, ... }
 *   }
 *
 * IMPORTANT — divergences spec user → API réelle :
 *   Le user spec parlait de `hp_pct`, `hc_pct`, `hp_mwh`, `shift_potential_mwh`
 *   (vocabulaire HP/HC tarifaire). L'API réelle expose une autre dimension :
 *   **comportement énergétique** (score, hors-horaires, talon, dérive).
 *   Les 3 KPIs sont remappés sur cette data honnête. Glossary terms adaptés :
 *   `hourly_behavior_score`, `hourly_offhours_pct`, `hourly_baseload_kw`.
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildHourlyKicker({ siteName, periodDays = 30 } = {}) {
  const label = siteName ? siteName.toUpperCase() : 'SITE';
  return `PROFILS HORAIRES · ${label} · ${periodDays}${NBSP}JOURS`;
}

export function buildHourlyNarrative({ data, siteName } = {}) {
  if (!data) {
    return 'Analyse du profil horaire en cours — minimum 14 jours de données 30-min requis pour un signal robuste.';
  }
  const score = Number(data?.anomalies?.behavior_score);
  const offhours = Number(data?.anomalies?.kpis?.offhours_pct) || 0;
  const baseload = Number(data?.profile?.baseload_kw) || 0;
  const drift = Number(data?.anomalies?.kpis?.drift_pct) || 0;

  const site = siteName || 'Ce site';
  const parts = [];
  if (Number.isFinite(score)) {
    if (score >= 80)
      parts.push(
        `${site} affiche un profil cohérent avec son activité (score ${Math.round(score)}${NBSP}/${NBSP}100)`
      );
    else if (score >= 50)
      parts.push(
        `${site} montre un profil à surveiller (score ${Math.round(score)}${NBSP}/${NBSP}100)`
      );
    else
      parts.push(
        `${site} présente des anomalies comportementales marquées (score ${Math.round(score)}${NBSP}/${NBSP}100)`
      );
  } else {
    parts.push(`${site} en cours de qualification`);
  }
  if (offhours > 20)
    parts.push(`${Math.round(offhours)}${NBSP}% de consommation hors horaires d'ouverture`);
  if (baseload > 0) parts.push(`talon ${formatFR(baseload, 0)}${NBSP}kW (Q10 nuit)`);
  if (Math.abs(drift) > 10) {
    const sign = drift > 0 ? '+' : '';
    parts.push(`dérive ${sign}${Math.round(drift)}${NBSP}% sur la période`);
  }
  return parts.join(' · ') + '.';
}

export function buildHourlySubNarrative() {
  return 'Méthodologie : baseline 14 jours · seuils night_ratio + weekend_ratio + drift · archétype ADEME par NAF.';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretBehaviorScore({ data } = {}) {
  const score = Number(data?.anomalies?.behavior_score);
  if (!Number.isFinite(score)) return 'Score en cours de calcul — 14 jours minimum requis.';
  if (score >= 80) return 'Profil aligné sur activité · aucune anomalie marquée.';
  if (score >= 50) return 'Profil à surveiller · quelques écarts détectés.';
  return 'Anomalies comportementales marquées · investigation recommandée.';
}

export function interpretOffhours({ data } = {}) {
  const p = Number(data?.anomalies?.kpis?.offhours_pct);
  if (!Number.isFinite(p)) return 'Consommation hors horaires à qualifier.';
  if (p > 30) return 'Part significative · vérifier programmation CVC + éclairage.';
  if (p > 15) return 'Part modérée · surveillance active recommandée.';
  return "Part faible · profil optimisé sur horaires d'ouverture.";
}

export function interpretBaseload({ data } = {}) {
  const kw = Number(data?.profile?.baseload_kw);
  const totalKwh = Number(data?.profile?.total_kwh) || 0;
  if (!Number.isFinite(kw) || kw <= 0) return 'Talon non mesuré — sous-comptage 30-min requis.';
  // Heuristique : talon > 30 % de la puissance moyenne = suspect
  const avgKw = totalKwh > 0 ? totalKwh / (30 * 24) : 0;
  if (avgKw > 0 && kw / avgKw > 0.3) {
    return `Talon élevé (${Math.round((kw / avgKw) * 100)}${NBSP}% de la puissance moyenne) · investiguer équipements permanents.`;
  }
  return 'Puissance minimale mesurée Q10 nuit (22h-6h).';
}

// ─────────────────────────────────────────────────────────────────────────────
// Profile classifier (utilisé pour displayValue KPI 1 si besoin)
// ─────────────────────────────────────────────────────────────────────────────

export function classifyProfile({ data } = {}) {
  const score = Number(data?.anomalies?.behavior_score);
  if (!Number.isFinite(score)) return { label: '—', tone: 'calme' };
  if (score >= 80) return { label: 'Cohérent', tone: 'succes' };
  if (score >= 50) return { label: 'À surveiller', tone: 'attention' };
  return { label: 'Anomalies', tone: 'refuse' };
}
