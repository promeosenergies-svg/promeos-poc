/**
 * PROMEOS — Patrimoine Sol presenters (Phase 4.3)
 *
 * Helpers purs pour PatrimoineSol — transformation de la réponse
 * getPatrimoineKpis + getSites vers props Sol.
 *
 * APIs consommées :
 *   getPatrimoineKpis(params) → {total, conformes, aRisque, nonConformes,
 *                                 totalRisque, totalSurface, totalAnomalies,
 *                                 nb_contrats_expiring_90j, ...}
 *   getSites({org_id, limit}) → {total, sites: [{id, nom, type, usage,
 *                                                 surface_m2, conso_kwh_an,
 *                                                 compliance_score, risque_eur,
 *                                                 statut_conformite, ...}]}
 *
 * EUI moyen calculé côté client (formule Σ(conso) / Σ(surface)), pas
 * d'endpoint dédié. Benchmarks ADEME via utils/benchmarks.js.
 */
import {
  NBSP,
  formatFR,
  formatFREur,
  computeDelta,
  freshness,
} from '../cockpit/sol_presenters';
import { getBenchmark } from '../../utils/benchmarks';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildPatrimoineKicker({ scope, typeFilter } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  const filterSuffix = typeFilter ? ` · filtre ${typeFilter}` : '';
  return `Patrimoine · ${orgName}${sitesSuffix}${filterSuffix}`;
}

export function buildPatrimoineNarrative({ kpis, sites, euiAvg, benchmarkAvg, topDrivers } = {}) {
  const nbSites = kpis?.total ?? sites?.length ?? 0;
  const surface = kpis?.totalSurface ?? 0;

  if (nbSites === 0) {
    return "Aucun site dans votre portefeuille pour l'instant. Commencez par importer depuis SIREN.";
  }

  // Répartition par type
  const byType = groupByType(sites);
  const typeSummary = summarizeTypeDistribution(byType);

  if (euiAvg == null || benchmarkAvg == null) {
    return `${nbSites}${NBSP}site${nbSites > 1 ? 's' : ''}, surface totale ${formatFR(surface, 0)}${NBSP}m². ${typeSummary}`;
  }

  const gap = Math.round(((euiAvg - benchmarkAvg) / benchmarkAvg) * 100);
  const baseFigures = `${nbSites} sites, ${formatFR(surface, 0)}${NBSP}m² · EUI moyen ${formatFR(euiAvg, 0)}${NBSP}kWh/m²`;

  // Phase 5 L1 : lorsque moyenne aligned OU faiblement au-dessus, mais qu'un
  // site individuel dépasse de >30 %, expliciter le piège de la moyenne.
  // Évite la contradiction apparente "aligned" vs week-card "Toulouse +50 %".
  const outlier = (topDrivers || []).find((d) => d?.gapPct > 30);
  const outlierClause = outlier
    ? `, mais la moyenne masque un écart important : ${outlier.site?.nom || 'un site'} dépasse de ${outlier.gapPct}${NBSP}% sa référence.`
    : null;

  if (gap > 10) {
    // Patrimoine déjà franchement au-dessus — pas besoin d'explication "masque"
    return `${baseFigures}${NBSP}— ${gap}${NBSP}% au-dessus de la référence ADEME. ${typeSummary}`;
  }
  if (gap < -5) {
    return `${baseFigures}${NBSP}— ${Math.abs(gap)}${NBSP}% mieux que la référence ADEME. ${typeSummary}`;
  }
  // Aligned : ajouter la clause outlier si un site décroche
  if (outlierClause) {
    return `${baseFigures} aligné sur la référence ADEME${outlierClause} ${typeSummary}`;
  }
  return `${baseFigures} aligné sur la référence ADEME. ${typeSummary}`;
}

export function buildPatrimoineSubNarrative({ kpis } = {}) {
  const conformes = kpis?.conformes ?? 0;
  const aRisque = kpis?.aRisque ?? 0;
  const nonConformes = kpis?.nonConformes ?? 0;
  const expiring = kpis?.nb_contrats_expiring_90j ?? 0;
  const total = conformes + aRisque + nonConformes;

  if (total === 0) {
    return "Sources : moteur de conformité RegOps + référentiel ADEME ODP 2024.";
  }

  const parts = [];
  if (conformes > 0) parts.push(`${conformes}${NBSP}conforme${conformes > 1 ? 's' : ''}`);
  if (aRisque > 0) parts.push(`${aRisque}${NBSP}à${NBSP}risque`);
  if (nonConformes > 0) parts.push(`${nonConformes}${NBSP}non${NBSP}conforme${nonConformes > 1 ? 's' : ''}`);
  const statut = parts.join(' · ');

  const contrats = expiring > 0
    ? ` · ${expiring}${NBSP}contrat${expiring > 1 ? 's' : ''} expirant sous 90${NBSP}jours`
    : '';

  return `${statut}${contrats}. Sources : RegOps canonique + ADEME ODP 2024.`;
}

function groupByType(sites) {
  if (!Array.isArray(sites)) return {};
  const out = {};
  for (const s of sites) {
    const t = s?.type || s?.usage || 'autre';
    out[t] = (out[t] || 0) + 1;
  }
  return out;
}

function summarizeTypeDistribution(byType) {
  const entries = Object.entries(byType).sort((a, b) => b[1] - a[1]).slice(0, 3);
  if (entries.length === 0) return '';
  return entries.map(([type, n]) => `${n}${NBSP}${labelType(type, n)}`).join(', ') + '.';
}

const TYPE_LABEL_FR = {
  bureau: { s: 'bureau', p: 'bureaux' },
  bureaux: { s: 'bureau', p: 'bureaux' },
  entrepot: { s: 'entrepôt', p: 'entrepôts' },
  logistique: { s: 'site logistique', p: 'sites logistiques' },
  enseignement: { s: 'école', p: 'écoles' },
  commerce: { s: 'commerce', p: 'commerces' },
  magasin: { s: 'magasin', p: 'magasins' },
  hotel: { s: 'hôtel', p: 'hôtels' },
  hotellerie: { s: 'hôtel', p: 'hôtels' },
  sante: { s: 'site santé', p: 'sites santé' },
  industrie: { s: 'site industriel', p: 'sites industriels' },
  usine: { s: 'usine', p: 'usines' },
  autre: { s: 'autre', p: 'autres' },
};

function labelType(type, n) {
  const entry = TYPE_LABEL_FR[type] || TYPE_LABEL_FR.autre;
  return n > 1 ? entry.p : entry.s;
}

// ─────────────────────────────────────────────────────────────────────────────
// EUI calculations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule l'EUI d'un site (kWhEF/m²/an).
 * Retourne null si surface ou conso manquantes.
 */
export function computeSiteEui(site) {
  if (!site) return null;
  const surface = Number(site.surface_m2) || 0;
  const conso = Number(site.conso_kwh_an) || 0;
  if (surface === 0 || conso === 0) return null;
  return Math.round((conso / surface) * 10) / 10;
}

/**
 * EUI moyen pondéré par surface : Σ(conso) / Σ(surface).
 * Retourne null si aucun site a conso+surface.
 */
export function computeAvgEui(sites) {
  if (!Array.isArray(sites)) return null;
  let totalConso = 0;
  let totalSurface = 0;
  for (const s of sites) {
    const surface = Number(s?.surface_m2) || 0;
    const conso = Number(s?.conso_kwh_an) || 0;
    if (surface > 0 && conso > 0) {
      totalConso += conso;
      totalSurface += surface;
    }
  }
  if (totalSurface === 0) return null;
  return Math.round((totalConso / totalSurface) * 10) / 10;
}

/**
 * Benchmark ADEME pondéré par surface selon le mix des usages.
 */
export function computeAvgBenchmark(sites) {
  if (!Array.isArray(sites) || sites.length === 0) return null;
  let weighted = 0;
  let totalSurface = 0;
  for (const s of sites) {
    const surface = Number(s?.surface_m2) || 0;
    if (surface === 0) continue;
    const bench = getBenchmark(s?.usage || s?.type);
    weighted += bench * surface;
    totalSurface += surface;
  }
  if (totalSurface === 0) return null;
  return Math.round(weighted / totalSurface);
}

/**
 * Sites avec EUI > benchmark ADEME (top-drivers à surveiller).
 * Retourne les 3 plus critiques.
 */
export function topEuiDrivers(sites) {
  if (!Array.isArray(sites)) return [];
  const withGap = sites
    .map((s) => {
      const eui = computeSiteEui(s);
      const bench = getBenchmark(s?.usage || s?.type);
      if (eui == null || !bench) return null;
      const gapPct = Math.round(((eui - bench) / bench) * 100);
      return { site: s, eui, bench, gapPct };
    })
    .filter(Boolean)
    .filter((x) => x.gapPct > 0)
    .sort((a, b) => b.gapPct - a.gapPct);
  return withGap.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretSites({ kpis, sites } = {}) {
  const nb = kpis?.total ?? sites?.length ?? 0;
  if (nb === 0) return 'Aucun site dans votre portefeuille.';
  const byType = groupByType(sites);
  return summarizeTypeDistribution(byType) || `${nb} site${nb > 1 ? 's' : ''} actifs.`;
}

export function interpretSurface({ kpis, sites } = {}) {
  const surface = kpis?.totalSurface ?? 0;
  const nb = kpis?.total ?? sites?.length ?? 0;
  if (surface === 0) return 'Surface non renseignée.';
  if (nb === 0) return `${formatFR(surface, 0)}${NBSP}m² cumulés.`;
  const avg = Math.round(surface / nb);
  return `${nb} bâtiments · moyenne ${formatFR(avg, 0)}${NBSP}m²/site.`;
}

export function interpretEUI({ euiAvg, benchmarkAvg, topDrivers } = {}) {
  if (euiAvg == null) {
    return 'Renseignez les surfaces et importez 12 mois de consommations pour activer ce calcul.';
  }
  if (benchmarkAvg == null) {
    return `EUI moyen ${formatFR(euiAvg, 0)}${NBSP}kWh/m²/an.`;
  }
  const gap = Math.round(((euiAvg - benchmarkAvg) / benchmarkAvg) * 100);
  const drivers = (topDrivers || []).slice(0, 3).map((d) => d.site.nom).filter(Boolean);
  if (gap > 10) {
    const driverList = drivers.length > 0
      ? ` ${drivers.length > 1 ? 'Sites tirant la moyenne' : 'Site tirant la moyenne'} : ${drivers.join(', ')}.`
      : '';
    return `${gap}${NBSP}% au-dessus de la référence ADEME ${formatFR(benchmarkAvg, 0)}${NBSP}kWh/m².${driverList}`;
  }
  if (gap < -5) {
    return `${Math.abs(gap)}${NBSP}% mieux que la référence ADEME ${formatFR(benchmarkAvg, 0)}${NBSP}kWh/m².`;
  }
  return `Aligné sur la référence ADEME ${formatFR(benchmarkAvg, 0)}${NBSP}kWh/m²/an.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Adapter sites → SolBarChart catégoriel (xAxisType='category')
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit une liste de sites → data SolBarChart (axe catégoriel par site).
 * Current = conso_kwh_an en MWh. Previous = fallback 0 si pas de N-1 dispo.
 */
export function adaptSitesToBarChart(sites, options = {}) {
  if (!Array.isArray(sites)) return [];
  const limit = options.limit || 8;
  return sites
    .filter((s) => s?.conso_kwh_an > 0)
    .sort((a, b) => (Number(b.conso_kwh_an) || 0) - (Number(a.conso_kwh_an) || 0))
    .slice(0, limit)
    .map((s) => ({
      site: shortName(s.nom || s.site || 'Site'),
      current: Math.round((Number(s.conso_kwh_an) || 0) / 1000), // kWh → MWh
      previous: s.conso_kwh_an_n1 != null
        ? Math.round(Number(s.conso_kwh_an_n1) / 1000)
        : Math.round(((Number(s.conso_kwh_an) || 0) * 1.04) / 1000), // mock +4 % N-1
    }));
}

function shortName(name) {
  // "Siège HELIOS Paris" → "Siège Paris" ou "Bureau Régional Lyon" → "Lyon"
  if (!name) return 'Site';
  const clean = name.replace(/HELIOS\s*/gi, '').trim();
  return clean.length > 18 ? clean.slice(0, 16) + '…' : clean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards Patrimoine
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards Patrimoine avec fallbacks businessErrors.
 *   Card 1 "À regarder"  : site top-EUI au-dessus benchmark
 *   Card 2 "À faire"     : site avec prochaine échéance réglementaire
 *   Card 3 "Bonne nouvelle" : site meilleure progression ou EUI sous benchmark
 */
export function buildPatrimoineWeekCards({ sites, topDrivers, onNavigateSite } = {}) {
  const cards = [];

  // Card 1 : top-driver EUI
  const topDriver = (topDrivers || [])[0];
  if (topDriver) {
    cards.push({
      id: `driver-${topDriver.site.id}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: topDriver.site.nom,
      body: `EUI ${formatFR(topDriver.eui, 0)}${NBSP}kWh/m² · ${topDriver.gapPct}${NBSP}% au-dessus du benchmark ADEME ${topDriver.bench}.`,
      footerLeft: `conso ${formatFR(Math.round((topDriver.site.conso_kwh_an || 0) / 1000), 0)}${NBSP}MWh/an`,
      footerRight: '⌘K',
      onClick: () => onNavigateSite?.(topDriver.site.id),
    });
  } else {
    cards.push(businessErrorFallback('patrimoine.all_conforming', cards.length));
  }

  // Card 2 : site avec risque financier le plus élevé (échéance réglementaire)
  const topRisk = (sites || [])
    .filter((s) => s?.risque_eur > 0)
    .sort((a, b) => (Number(b.risque_eur) || 0) - (Number(a.risque_eur) || 0))[0];
  if (topRisk) {
    cards.push({
      id: `risk-${topRisk.id}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: topRisk.nom,
      body: `Risque financier ${formatFREur(topRisk.risque_eur, 0)} · statut ${topRisk.statut_conformite?.replace('_', ' ') || 'à évaluer'}.`,
      footerLeft: `score DT ${topRisk.compliance_score ?? '—'}/100`,
      footerRight: 'Plan requis',
      onClick: () => onNavigateSite?.(topRisk.id),
    });
  } else {
    cards.push(businessErrorFallback('conformite.no_upcoming'));
  }

  // Card 3 : site le plus conforme / meilleur EUI
  const bestSite = (sites || [])
    .filter((s) => s?.statut_conformite === 'conforme' || (s?.compliance_score ?? 0) >= 75)
    .sort((a, b) => (Number(b.compliance_score) || 0) - (Number(a.compliance_score) || 0))[0];
  if (bestSite) {
    cards.push({
      id: `best-${bestSite.id}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: bestSite.nom,
      body: `Conforme · score DT ${bestSite.compliance_score ?? '—'}/100. Exemple à valoriser auprès des autres sites.`,
      footerLeft: `${formatFR(bestSite.surface_m2 || 0, 0)}${NBSP}m²`,
      footerRight: '✓ Clean',
      onClick: () => onNavigateSite?.(bestSite.id),
    });
  } else {
    cards.push(businessErrorFallback('patrimoine.all_conforming', cards.length));
  }

  return cards.slice(0, 3);
}

// Re-exports
export { formatFR, formatFREur, computeDelta, freshness };
