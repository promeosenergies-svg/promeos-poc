/**
 * PROMEOS — DiagnosticConsoSol (Lot 3 Phase 5, refonte Sol Pattern A hybride)
 *
 * Hero + KPIs + BarChart + WeekGrid top insights pour la page dashboard
 * `/diagnostic-conso`. Pattern A CHOISI (pas Pattern C) car :
 *   - Pas de :id dans la route (page multi-sites scope optionnel)
 *   - Sélecteur de période (usePeriodParams 90j default)
 *   - Comportement dashboard, pas fiche entité
 *
 * Architecture :
 *   - ConsumptionDiagPage.jsx (parent) garde la totalité de sa logique
 *     métier (fetch, state insight drawer inline, liste détaillée,
 *     seed/diagnose actions). Ce composant Sol est INJECTÉ EN HAUT
 *     pour remplacer le hero + les tiles KPIs legacy par du Pattern A.
 *   - L'EvidenceDrawer 4 tabs inline (Evidence/Méthode/Actions/Flex)
 *     reste intégralement intact dans le parent — ne pas porter vers
 *     Sol (hors scope Lot 3, refonte dédiée v2.3+).
 */
import React from 'react';
import {
  SolPageHeader,
  SolHeadline,
  SolSubline,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolBarChart,
  SolWeekGrid,
  SolWeekCard,
} from '../ui/sol';
import {
  buildDiagnosticKicker,
  buildDiagnosticNarrative,
  buildDiagnosticSubNarrative,
  interpretTotalLoss,
  interpretDriftKwh,
  interpretSitesAffected,
  adaptInsightsToBarChart,
  buildDiagnosticWeekCards,
  formatFR,
  formatFREur,
  NBSP,
} from './diagnostic/sol_presenters';

/**
 * @param {Object} props
 * @param {Array} props.insights
 * @param {Object} props.summary
 * @param {Object} [props.scope]
 * @param {Object} [props.selectedSite]
 * @param {number} props.periodDays
 * @param {React.ReactNode} [props.actions] - boutons droit du header
 * @param {string} [props.customPrice]
 * @param {(insight:Object)=>void} [props.onOpenInsight]
 */
export default function DiagnosticConsoSol({
  insights = [],
  summary,
  scope,
  selectedSite = null,
  periodDays = 90,
  actions,
  customPrice,
  onOpenInsight,
}) {
  const kicker = buildDiagnosticKicker({ scope, selectedSite, periodDays });
  const narrative = buildDiagnosticNarrative({ summary, insights, scope, periodDays });
  const subNarrative = buildDiagnosticSubNarrative();

  const totalLossEur = Number(summary?.total_loss_eur) || 0;
  const totalLossKwh = Number(summary?.total_loss_kwh) || 0;
  const sitesAffected = Number(summary?.sites_with_insights) || 0;

  const barData = adaptInsightsToBarChart(insights);
  const weekCards = buildDiagnosticWeekCards({ insights, onOpenInsight });

  const sitesSuffix =
    scope?.sitesCount != null && !selectedSite ? ` · ${scope.sitesCount}${NBSP}sites` : '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={kicker}
        title="Diagnostic consommation"
        titleEm={`· ${periodDays}${NBSP}jours${sitesSuffix}`}
        narrative={narrative}
        subNarrative={subNarrative}
        rightSlot={actions}
      />

      <SolHeadline>
        <em>Votre patrimoine</em>{' '}
        {(() => {
          // Le backend peut renvoyer summary.total_insights=0 alors que
          // insights.length > 0 (mapping décalé). Fallback sur insights.length.
          const count = Number(summary?.total_insights) || insights.length || 0;
          if (count > 0) {
            return `présente ${count}${NBSP}anomalie${count > 1 ? 's' : ''} de consommation active${count > 1 ? 's' : ''} sur la période.`;
          }
          return 'est stable sur la fenêtre analysée.';
        })()}
      </SolHeadline>
      {summary?.total_loss_eur > 0 && (
        <SolSubline>
          Pertes cumulées estimées {formatFREur(totalLossEur, 0)} · excès énergétique{' '}
          {formatFR(Math.round(totalLossKwh / 1000), 0)}
          {NBSP}MWh.
        </SolSubline>
      )}

      <SolKpiRow>
        <SolKpiCard
          label="Pertes financières"
          value={totalLossEur > 0 ? formatFREur(totalLossEur, 0) : '—'}
          unit={`sur ${periodDays}${NBSP}jours`}
          semantic="cost"
          explainKey="diagnostic_total_loss_eur"
          headline={interpretTotalLoss({ summary, customPrice })}
          source={{ kind: 'calcul', origin: 'prix moyen pondéré' }}
        />
        <SolKpiCard
          label="Excès énergétique"
          value={totalLossKwh > 0 ? formatFR(Math.round(totalLossKwh / 1000), 0) : '—'}
          unit="MWh"
          semantic="cost"
          explainKey="diagnostic_total_loss_kwh"
          headline={interpretDriftKwh({ summary })}
          source={{ kind: 'calcul', origin: 'baseline DJU Météo-France' }}
        />
        <SolKpiCard
          label="Sites concernés"
          value={sitesAffected > 0 ? String(sitesAffected) : '—'}
          unit={sitesAffected > 1 ? 'sites' : 'site'}
          semantic="score"
          explainKey="diagnostic_sites_affected"
          headline={interpretSitesAffected({ summary })}
          source={{ kind: 'calcul', origin: 'détection ML LOF' }}
        />
      </SolKpiRow>

      <SolSectionHead
        title="Top sites par pertes estimées"
        meta={`${barData.length}${NBSP}site${barData.length > 1 ? 's' : ''} · cumul période`}
      />
      {barData.length > 0 ? (
        <SolBarChart
          data={barData}
          xAxisKey="site"
          xAxisType="category"
          yLabel="€ perdus"
          sourceChip={<SolSourceChip kind="calcul" origin="agrégation insights" />}
        />
      ) : (
        <p
          style={{
            color: 'var(--sol-ink-500)',
            fontStyle: 'italic',
            margin: 0,
            padding: '16px 0',
          }}
        >
          Aucun site avec pertes financières identifiées sur la période.
        </p>
      )}

      <SolSectionHead title="Cette semaine sur le diagnostic" meta="3 signaux prioritaires" />
      <SolWeekGrid>
        {weekCards.map((c) => (
          <SolWeekCard
            key={c.id}
            tagLabel={c.tagLabel}
            tagKind={c.tagKind}
            title={c.title}
            body={c.body}
            footerLeft={c.footerLeft}
            footerRight={c.footerRight}
            onClick={c.onClick}
          />
        ))}
      </SolWeekGrid>
    </div>
  );
}
