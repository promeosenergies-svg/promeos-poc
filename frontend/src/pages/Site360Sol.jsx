/**
 * PROMEOS — Site360Sol (Lot 3 Phase 2, refonte Sol Pattern C)
 *
 * Onglet « Résumé » de /sites/:id en Pattern C (fiche détail) :
 *   SolBreadcrumb → SolDetailPage (entityCard gauche + mainContent droite)
 *   mainContent = SolKpiRow 3 KPIs + trajectoire DT + SolWeekGrid 3 signaux.
 *
 * Scope strict : remplace UNIQUEMENT le rendu TabResume (Site360.jsx:2145).
 * Les 8 autres onglets (conso, analytics, factures, réconciliation, conformité,
 * actions, puissance, usages) restent rendus par Site360.jsx legacy via
 * ?tab=<id>. Aucune modif de routing (/sites/:id reste pointé sur Site360).
 *
 * APIs consommées :
 *   - site (prop, depuis scopedSites dans parent Site360.jsx)
 *   - intensityData (prop, déjà calculé parent via /api/energy/sites/{id}/intensity)
 *   - siteComplianceScore (prop, déjà fetch parent via /api/compliance/sites/{id}/score)
 *   - unifiedAnomalies (prop, déjà fetch parent via /patrimoine/sites/{id}/anomalies-unified)
 *   - topReco (prop)
 *   - deliveryPoints (fetch local, 1 request) via patrimoineDeliveryPoints(site.id)
 *
 * Drawers/modals préservés : ActionDrawerProvider monté dans SolAppShell global.
 * Les triggers vivent dans les autres onglets (Actions, Factures…) — ce
 * composant ne déclenche pas de drawer, seulement de la navigation tab.
 */
import React, { useEffect, useState } from 'react';
import {
  SolDetailPage,
  SolEntityCard,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolWeekGrid,
  SolWeekCard,
  SolTrajectoryChart,
  SolButton,
} from '../ui/sol';
import { patrimoineDeliveryPoints } from '../services/api';
import {
  buildSiteKicker,
  buildSiteNarrative,
  buildSiteSubNarrative,
  statusPillFromSite,
  buildEntityCardFields,
  interpretSiteEui,
  interpretSiteCompliance,
  interpretSiteRisque,
  buildSiteWeekCards,
  adaptComplianceToTrajectory,
  labelUsage,
  formatFR,
  formatFREur,
  NBSP,
} from './sites/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} props.site        - Entity depuis scopedSites
 * @param {string} [props.orgId]
 * @param {number} [props.unifiedCount]
 * @param {Array} [props.anomalies]
 * @param {boolean} [props.anomLoading]
 * @param {Object} [props.topReco]
 * @param {Object} props.intensityData - {intensity, benchmark, hasIntensity, ...}
 * @param {Object} [props.compliance]  - {overall, breakdown, baseline}
 * @param {(tab:string)=>void} props.onOpenTab
 */
export default function Site360Sol({
  site,
  orgId, // eslint-disable-line no-unused-vars
  unifiedCount, // eslint-disable-line no-unused-vars
  anomalies = [],
  anomLoading = false,
  topReco = null,
  intensityData = {},
  compliance = null,
  onOpenTab,
}) {
  const [deliveryPoints, setDeliveryPoints] = useState([]);

  useEffect(() => {
    if (!site?.id) return undefined;
    let stale = false;
    patrimoineDeliveryPoints(site.id)
      .then((data) => {
        if (!stale) setDeliveryPoints(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!stale) setDeliveryPoints([]);
      });
    return () => {
      stale = true;
    };
  }, [site?.id]);

  if (!site) {
    // Fallback : rendu minimal si le site n'est pas dans le scope courant.
    // Le parent Site360.jsx affiche déjà un loader en amont, ce cas n'apparaît
    // qu'en cas de race condition (scope switch + URL directe).
    return (
      <div style={{ padding: 24, color: 'var(--sol-ink-500)', fontStyle: 'italic' }}>
        Site introuvable dans votre périmètre.
      </div>
    );
  }

  const kicker = buildSiteKicker(site);
  const narrative = buildSiteNarrative({ site, intensityData, anomalies, compliance });
  const subNarrative = buildSiteSubNarrative({ site });
  const pill = statusPillFromSite({ site, compliance });
  const fields = buildEntityCardFields({ site, deliveryPoints });

  const usageLabel = labelUsage(site.usage || site.type);
  const titleEm =
    site.surface_m2 > 0
      ? `· ${usageLabel} · ${formatFR(site.surface_m2, 0)}${NBSP}m²`
      : `· ${usageLabel}`;

  const trajectory = adaptComplianceToTrajectory({ site, compliance });
  const complianceScore = compliance?.overall ?? site.compliance_score ?? null;

  const weekCards = buildSiteWeekCards({
    site,
    anomalies,
    topReco,
    compliance,
    onOpenTab,
  });

  // EntityCard actions : navigation rapide vers les onglets métier.
  const entityCardActions = (
    <>
      <SolButton variant="secondary" onClick={() => onOpenTab?.('factures')}>
        Factures
      </SolButton>
      <SolButton variant="secondary" onClick={() => onOpenTab?.('conformite')}>
        Conformité
      </SolButton>
      <SolButton variant="ghost" onClick={() => onOpenTab?.('actions')}>
        Actions
      </SolButton>
    </>
  );

  const entityCard = (
    <SolEntityCard
      title={site.nom || 'Site'}
      subtitle={site.ville ? `${usageLabel} · ${site.ville}` : usageLabel}
      status={pill}
      fields={fields}
      actions={entityCardActions}
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Intensité énergétique"
        value={intensityData?.hasIntensity ? formatFR(intensityData.intensity, 0) : '—'}
        unit={`kWh/m²/an`}
        semantic="cost"
        explainKey="kwh_m2_an"
        headline={interpretSiteEui({ intensityData, site })}
        source={{ kind: 'calcul', origin: 'ADEME ODP 2024' }}
      />
      <SolKpiCard
        label="Conformité"
        value={complianceScore != null ? String(complianceScore) : '—'}
        unit="/100"
        semantic="score"
        explainKey="compliance_score"
        headline={interpretSiteCompliance({ compliance, site })}
        source={{ kind: 'calcul', origin: 'RegOps canonique' }}
      />
      <SolKpiCard
        label="Risque financier"
        value={site.risque_eur > 0 ? formatFREur(site.risque_eur, 0) : '—'}
        unit=""
        semantic="cost"
        explainKey="anomalie"
        headline={interpretSiteRisque({ site, anomalies })}
        source={{ kind: 'factures', origin: 'shadow billing' }}
      />
    </SolKpiRow>
  );

  const mainContent = (
    <>
      <SolSectionHead title="Trajectoire Décret Tertiaire" meta="référence 2020 · objectif 2030" />
      {trajectory ? (
        <SolTrajectoryChart
          data={trajectory}
          targetLine={75}
          targetLabel="Cible DT 2030"
          yDomain={[0, 100]}
          yLabel="score /100"
          sourceChip={<SolSourceChip kind="calcul" origin="RegOps" />}
          caption={interpretSiteCompliance({ compliance, site })}
        />
      ) : (
        <p style={{ color: 'var(--sol-ink-500)', fontStyle: 'italic', margin: 0 }}>
          Score en cours de calcul — revenez dans quelques minutes.
        </p>
      )}

      <SolSectionHead title="Cette semaine sur ce site" meta="3 signaux" />
      {anomLoading ? (
        <p style={{ color: 'var(--sol-ink-500)', fontStyle: 'italic', margin: 0 }}>
          Analyse des anomalies en cours…
        </p>
      ) : (
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
      )}
    </>
  );

  return (
    <SolDetailPage
      breadcrumb={{
        segments: [{ label: 'Patrimoine', to: '/patrimoine' }, { label: site.nom || 'Site' }],
        backTo: '/patrimoine',
      }}
      kicker={kicker}
      title={site.nom || 'Site'}
      titleEm={titleEm}
      narrative={narrative}
      subNarrative={subNarrative}
      entityCard={entityCard}
      kpiRow={kpiRow}
      mainContent={mainContent}
    />
  );
}
