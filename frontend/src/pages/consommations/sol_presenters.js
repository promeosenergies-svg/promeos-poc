/**
 * PROMEOS — ConsommationsSol presenters (Sprint REFONTE-P6 S1 — wrappers)
 *
 * Helpers pour ConsommationsSol (hub), ConsumptionPortfolioSol, ConsumptionExplorerSol.
 */

import { NBSP, formatFREur } from '../cockpit/sol_presenters';

export { NBSP };

/**
 * Build kicker hub "ÉNERGIE · CONSOMMATIONS · 758,4 MWh"
 */
export function buildConsoHubKicker({ portfolioSummary } = {}) {
  const t = portfolioSummary?.totals || {};
  const segments = ['ÉNERGIE', 'CONSOMMATIONS'];
  if (t.kwh_total) {
    const mwh = t.kwh_total / 1000;
    segments.push(`${mwh.toFixed(mwh >= 100 ? 0 : 1).replace('.', ',')}${NBSP}MWh`);
  }
  return segments.join(` ${NBSP}·${NBSP} `);
}

export function buildConsoHubNarrative({ portfolioSummary, sitesCount } = {}) {
  const t = portfolioSummary?.totals || {};
  const cov = portfolioSummary?.coverage || {};
  const parts = [];
  if (t.kwh_total) {
    const mwh = (t.kwh_total / 1000).toFixed(1).replace('.', ',');
    parts.push(`${mwh}${NBSP}MWh sur 12 mois glissants`);
  }
  if (t.eur_total) parts.push(formatFREur(t.eur_total));
  if (t.co2_total) parts.push(`${t.co2_total.toFixed(1).replace('.', ',')}${NBSP}t CO₂`);
  if (cov.sites_with_data && cov.sites_total) {
    parts.push(`couverture ${cov.sites_with_data}/${cov.sites_total} sites`);
  } else if (sitesCount) {
    parts.push(`${sitesCount} site${sitesCount > 1 ? 's' : ''}`);
  }

  const intro = parts.length > 0 ? parts.join(` ${NBSP}·${NBSP} `) + '.' : 'En attente des données consommation.';
  const sources = 'Sources : Enedis SGE + GRDF ADICT + consumption_unified_service. Facteurs ADEME V23.6.';
  return `${intro} ${sources}`;
}

/**
 * Portfolio — kicker + narrative + 3 week cards
 */
export function buildPortfolioKicker({ portfolioSummary } = {}) {
  const t = portfolioSummary?.totals || {};
  const segments = ['ÉNERGIE', 'PORTEFEUILLE'];
  if (t.kwh_total) {
    const mwh = t.kwh_total / 1000;
    segments.push(`${mwh.toFixed(mwh >= 100 ? 0 : 1).replace('.', ',')}${NBSP}MWh`);
  }
  if (t.eur_total) segments.push(formatFREur(t.eur_total));
  return segments.join(` ${NBSP}·${NBSP} `);
}

export function buildPortfolioNarrative({ portfolioSummary, topImpact = [] } = {}) {
  const cov = portfolioSummary?.coverage || {};
  const parts = [];
  if (cov.sites_with_data && cov.sites_total) {
    const pct = Math.round((cov.sites_with_data / cov.sites_total) * 100);
    parts.push(`Couverture ${pct}% (${cov.sites_with_data}/${cov.sites_total} sites)`);
  }
  if (topImpact.length > 0) {
    parts.push(`Top impact : ${topImpact[0].site_name || 'n/a'}`);
  }

  const intro = parts.length > 0 ? parts.join(` ${NBSP}·${NBSP} `) + '.' : 'En attente portfolio summary.';
  const sources = 'consumption_unified_service · metered/billed/reconciled selon disponibilité. Benchmark ADEME.';
  return `${intro} ${sources}`;
}

export function interpretPortfolioWeek({ portfolioSummary } = {}) {
  const topImpact = portfolioSummary?.top_impact || [];
  const topDrift = portfolioSummary?.top_drift || [];
  const topBaseNight = portfolioSummary?.top_base_night || [];

  const aRegarder = topImpact.length > 0
    ? {
        tagKind: 'afaire',
        tagLabel: 'Impact financier',
        title: topImpact[0].site_name || 'Site à impact',
        body: `${formatFREur(topImpact[0].impact_eur_estimated || 0)} d'économie potentielle détectée`,
        footerRight: 'ouvrir →',
      }
    : {
        tagKind: 'calme',
        tagLabel: 'Impact financier',
        title: 'Pas de dérive coût détectée',
        body: 'Le portefeuille consommation suit les attendus budget.',
      };

  const deriveDetectee = topDrift.length > 0
    ? {
        tagKind: 'attention',
        tagLabel: 'Dérive détectée',
        title: topDrift[0].site_name || 'Site en dérive',
        body: `${topDrift[0].diagnostics_count || 0} alerte${(topDrift[0].diagnostics_count || 0) > 1 ? 's' : ''} consommation active${(topDrift[0].diagnostics_count || 0) > 1 ? 's' : ''}`,
        footerRight: 'diagnostic →',
      }
    : {
        tagKind: 'calme',
        tagLabel: 'Dérive détectée',
        title: 'Aucune dérive active',
        body: 'Les signatures énergétiques sont conformes aux attendus 12 mois.',
      };

  const bonneNouvelle = {
    tagKind: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: topBaseNight.length > 0 ? `${topBaseNight.length} sites analysés nuit` : 'Portefeuille sous contrôle',
    body:
      topBaseNight.length > 0
        ? 'Talon de nuit cartographié sur la période — data quality haute.'
        : 'Pas d\'alerte portefeuille sur la dernière analyse.',
  };

  return { aRegarder, deriveDetectee, bonneNouvelle };
}

/**
 * Explorer — kicker minimal (wrapper Option A)
 */
export function buildExplorerKicker() {
  return `ÉNERGIE ${NBSP}·${NBSP} CONSOMMATIONS ${NBSP}·${NBSP} EXPLORATEUR`;
}

export function buildExplorerNarrative() {
  return `Courbes de charge 30${NBSP}min multi-sites · 12 analyses spécialisées (timeseries, signature, météo, tunnel, objectifs, HP/HC, gaz, benchmark, CDC, hiérarchie, data quality). Sources : Enedis SGE + GRDF ADICT + EMS motor.`;
}
