/**
 * PROMEOS — EfaSol (Lot 3 Phase 4, refonte Sol Pattern C)
 *
 * Fiche EFA Décret Tertiaire en Pattern C :
 *   SolBreadcrumb 3 segments → SolDetailPage(entityCard + kpiRow + mainContent)
 *   mainContent = 3 KPIs + SolTrajectoryChart (3 jalons DT verticaux)
 *                + SolWeekGrid (variety guard).
 *
 * Architecture :
 *   - TertiaireEfaDetailPage.jsx (parent) = loader thin (fetch EFA,
 *     trajectory, déclaration courante).
 *   - EfaSol.jsx (ici) = pur composant de présentation.
 *   - ProofDepositCTA + ModulationDrawer préservés via callbacks
 *     `onOpenProofs` / `onOpenModulation`.
 *
 * SolTrajectoryChart a été étendu Phase 4 avec la prop `verticalMarkers`
 * pour afficher les 3 jalons DT (2030 / 2040 / 2050).
 */
import React from 'react';
import {
  SolDetailPage,
  SolEntityCard,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolTrajectoryChart,
  SolWeekGrid,
  SolWeekCard,
  SolButton,
} from '../ui/sol';
import {
  buildEfaKicker,
  buildEfaNarrative,
  buildEfaSubNarrative,
  statusPillFromEfa,
  buildEfaEntityCardFields,
  interpretEfaReference,
  interpretEfaCurrent,
  interpretEfaTarget2030,
  buildEfaTrajectoryChart,
  buildEfaWeekCards,
  latestConsumption,
  consumptionKwh,
  latestDeclaration,
  formatFR,
  NBSP,
} from './efa/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} props.efa              - Entité EFA normalisée
 * @param {Object} [props.trajectoryInfo] - validateEfaTrajectory() shape
 * @param {()=>void} [props.onOpenProofs]
 * @param {()=>void} [props.onOpenModulation]
 * @param {()=>void} [props.onExportOperat]
 * @param {(id:number)=>void} [props.onOpenBuilding]
 */
export default function EfaSol({
  efa,
  trajectoryInfo = null,
  onOpenProofs,
  onOpenModulation,
  onExportOperat,
  onOpenBuilding, // eslint-disable-line no-unused-vars
}) {
  if (!efa) {
    return (
      <div style={{ padding: 24, color: 'var(--sol-ink-500)', fontStyle: 'italic' }}>
        EFA introuvable dans votre périmètre.
      </div>
    );
  }

  const lastDeclaration = latestDeclaration(efa);
  const kicker = buildEfaKicker({ efa });
  const narrative = buildEfaNarrative({ efa });
  const subNarrative = buildEfaSubNarrative({ efa, lastDeclaration });
  const pill = statusPillFromEfa({
    efa,
    trajectoryStatus: trajectoryInfo?.final_status,
  });
  const fields = buildEfaEntityCardFields({ efa, lastDeclaration });

  const refMwh = efa.reference_year_kwh
    ? Math.round(efa.reference_year_kwh / 1000)
    : null;
  const latest = latestConsumption(efa);
  const currKwh = Number(consumptionKwh(latest)) || 0;
  const currMwh = currKwh > 0 ? Math.round(currKwh / 1000) : null;

  const {
    data: chartData,
    verticalMarkers,
    targetLine,
    targetLabel,
    yDomain,
  } = buildEfaTrajectoryChart(efa);

  const weekCards = buildEfaWeekCards({
    efa,
    lastDeclaration,
    onOpenProofs,
    onOpenModulation,
  });

  const titleEm = efa.reference_year
    ? `· référence ${efa.reference_year}`
    : '';

  const entityCardActions = (
    <>
      <SolButton variant="secondary" onClick={onOpenProofs}>
        Déposer pièce
      </SolButton>
      <SolButton variant="secondary" onClick={onOpenModulation}>
        Modulation
      </SolButton>
      <SolButton variant="ghost" onClick={onExportOperat}>
        Export OPERAT
      </SolButton>
    </>
  );

  const entityCard = (
    <SolEntityCard
      title={efa.nom || `EFA ${efa.id}`}
      subtitle={`EFA · Décret Tertiaire · ${efa.statut || '—'}`}
      status={pill}
      fields={fields}
      actions={entityCardActions}
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label={`Référence ${efa.reference_year || ''}`.trim()}
        value={refMwh != null ? formatFR(refMwh, 0) : '—'}
        unit="MWh/an"
        semantic="neutral"
        explainKey="efa_reference_year_kwh"
        headline={interpretEfaReference({ efa })}
        source={{ kind: 'calcul', origin: 'OPERAT ADEME' }}
      />
      <SolKpiCard
        label={`Actuel ${latest?.year || ''}`.trim()}
        value={currMwh != null ? formatFR(currMwh, 0) : '—'}
        unit="MWh/an"
        semantic="cost"
        explainKey="efa_current_year_kwh"
        headline={interpretEfaCurrent({ efa })}
        source={{ kind: 'calcul', origin: 'OPERAT ADEME' }}
      />
      <SolKpiCard
        label="Objectif 2030"
        value={targetLine != null ? formatFR(targetLine, 0) : '—'}
        unit="MWh/an"
        semantic="score"
        explainKey="efa_target_2030_kwh"
        headline={interpretEfaTarget2030({ efa })}
        source={{ kind: 'calcul', origin: '−25 % Décret Tertiaire' }}
      />
    </SolKpiRow>
  );

  const mainContent = (
    <>
      <SolSectionHead
        title="Trajectoire Décret Tertiaire"
        meta={`référence ${efa.reference_year || '—'} → 2050 · 3${NBSP}jalons réglementaires`}
      />
      {chartData.length > 0 ? (
        <SolTrajectoryChart
          data={chartData}
          dataKey="mwh"
          yDomain={yDomain}
          yLabel="MWh/an"
          showThresholdZones={false}
          targetLine={targetLine}
          targetLabel={targetLabel}
          verticalMarkers={verticalMarkers}
          sourceChip={<SolSourceChip kind="calcul" origin="OPERAT · baseline 2010" />}
          caption={interpretEfaCurrent({ efa })}
          height={240}
        />
      ) : (
        <p style={{ color: 'var(--sol-ink-500)', fontStyle: 'italic', margin: 0 }}>
          Référence non renseignée — impossible de tracer la trajectoire DT.
        </p>
      )}

      <SolSectionHead title="Cette semaine sur cette EFA" meta="3 signaux" />
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
    </>
  );

  return (
    <SolDetailPage
      breadcrumb={{
        segments: [
          { label: 'Conformité', to: '/conformite' },
          { label: 'Décret Tertiaire', to: '/conformite/tertiaire' },
          { label: efa.nom || `EFA ${efa.id}` },
        ],
        backTo: '/conformite/tertiaire',
      }}
      kicker={kicker}
      title={efa.nom || `EFA ${efa.id}`}
      titleEm={titleEm}
      narrative={narrative}
      subNarrative={subNarrative}
      entityCard={entityCard}
      kpiRow={kpiRow}
      mainContent={mainContent}
    />
  );
}
