/**
 * PROMEOS — UsagesHorairesSol (Lot 2 Phase 6, Pattern A compact)
 *
 * Injection Sol compacte en haut de ConsumptionContextPage. Le legacy
 * body (KPI strip 4 cartes + 2 onglets Profil & Heatmap / Horaires &
 * Anomalies + graphes spécialisés ProfileHeatmapTab +
 * HorairesAnomaliesTab) reste préservé intégralement dessous.
 *
 * Pattern A compact : pas de SolBarChart (legacy a ses graphes
 * spécialisés), pas de SolWeekGrid (page très technique sans signal
 * narratif évident, acceptable de skip — cf note Phase 6 spec user).
 */
import React from 'react';
import { SolPageHeader, SolHeadline, SolKpiRow, SolKpiCard } from '../ui/sol';
import {
  buildHourlyKicker,
  buildHourlyNarrative,
  buildHourlySubNarrative,
  interpretBehaviorScore,
  interpretOffhours,
  interpretBaseload,
  classifyProfile,
  formatFR,
  NBSP,
} from './usages-horaires/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} props.data       getConsumptionContext() result
 * @param {string} [props.siteName]
 * @param {number} [props.periodDays]
 */
export default function UsagesHorairesSol({ data, siteName, periodDays = 30 }) {
  const score = Number(data?.anomalies?.behavior_score);
  const offhours = Number(data?.anomalies?.kpis?.offhours_pct);
  const baseload = Number(data?.profile?.baseload_kw);
  const profileClass = classifyProfile({ data });

  const kicker = buildHourlyKicker({ siteName, periodDays });
  const narrative = buildHourlyNarrative({ data, siteName });
  const subNarrative = buildHourlySubNarrative();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '24px 28px 0' }}>
      <SolPageHeader
        kicker={kicker}
        title="Profils horaires"
        titleEm={`· signature ${periodDays}${NBSP}jours`}
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolHeadline>
        <em>Votre site</em>{' '}
        {Number.isFinite(score)
          ? `présente un profil ${profileClass.label.toLowerCase()} sur la période analysée.`
          : 'est en cours de qualification — données 30-min en agrégation.'}
      </SolHeadline>

      <SolKpiRow>
        <SolKpiCard
          label="Score comportement"
          value={Number.isFinite(score) ? String(Math.round(score)) : '—'}
          unit="/100"
          semantic="score"
          explainKey="hourly_behavior_score"
          headline={interpretBehaviorScore({ data })}
          source={{ kind: 'calcul', origin: 'moteur anomalies comportementales' }}
        />
        <SolKpiCard
          label="Hors horaires"
          value={Number.isFinite(offhours) ? `${Math.round(offhours)}` : '—'}
          unit="%"
          semantic="cost"
          explainKey="hourly_offhours_pct"
          headline={interpretOffhours({ data })}
          source={{ kind: 'calcul', origin: 'comparaison horaires ouverture' }}
        />
        <SolKpiCard
          label="Talon"
          value={Number.isFinite(baseload) && baseload > 0 ? formatFR(baseload, 0) : '—'}
          unit="kW"
          semantic="cost"
          explainKey="hourly_baseload_kw"
          headline={interpretBaseload({ data })}
          source={{ kind: 'calcul', origin: 'Q10 nuit 22h-6h' }}
        />
      </SolKpiRow>
    </div>
  );
}
