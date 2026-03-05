/**
 * anomalyEvidence — V114b
 * Builds an Evidence object from an anomaly for the "Pourquoi ?" drawer.
 */
import { buildEvidence } from '../ui/evidence';

const FW_LABEL = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  FACTURATION: 'Facturation',
  BACS: 'BACS',
};

function fmtRisk(eur) {
  if (!eur || eur <= 0) return null;
  return `${eur.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} €`;
}

export function buildAnomalyEvidence(anom) {
  const framework = anom.regulatory_impact?.framework;
  const riskEur = anom.business_impact?.estimated_risk_eur;
  const confidence = anom.business_impact?.confidence || 'medium';

  const sources = [
    {
      kind: 'calc',
      label: `Règle : ${anom.code || 'ANOMALIE'}`,
      confidence,
      details: anom.regulatory_impact?.explanation_fr || null,
    },
  ];

  const method = [];
  if (anom.detail_fr) method.push(anom.detail_fr);
  if (anom.business_impact?.explanation_fr) method.push(anom.business_impact.explanation_fr);

  const assumptions = [];
  if (anom.fix_hint_fr) assumptions.push(anom.fix_hint_fr);

  return buildEvidence({
    id: `anomaly-${anom.site_id}-${anom.code}`,
    title: anom.title_fr || 'Anomalie',
    valueLabel: fmtRisk(riskEur),
    scopeLabel: anom.site_nom || null,
    periodLabel: FW_LABEL[framework] || framework || null,
    sources,
    method,
    assumptions,
  });
}
