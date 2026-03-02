/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Data Adapter — Bridge between B1/B2 backend and domain layer
 *
 * Fetches data from existing APIs (B1 patrimoine, B2 billing)
 * and maps it to the domain types expected by the engine.
 * Falls back to demo data when APIs are unavailable.
 */
import {
  getSites, getSite,
} from '../../services/api.js';
import {
  getSiteBilling, getBillingInsights,
} from '../../services/api.js';
import {
  getPurchaseAssumptions, getPurchasePreferences,
} from '../../services/api.js';
import { EnergyType, SEASONALITY_ELEC, SEASONALITY_GAZ } from './types.js';
import { DEMO_ORGANIZATIONS, DEMO_OFFERS, aggregateDemoSites } from './demoData.js';

// ── Organization & Sites Adapter ───────────────────────────────────

/**
 * Fetch sites from B1 and map to domain format
 * @param {Object} [params]
 * @returns {Promise<import('./types.js').Site[]>}
 */
export async function fetchSites(params = {}) {
  try {
    const data = await getSites(params);
    const sites = Array.isArray(data) ? data : data?.items || data?.sites || [];
    return sites.map(mapBackendSiteToDomain);
  } catch {
    // Fallback to demo
    return DEMO_ORGANIZATIONS.flatMap(org =>
      org.entities.flatMap(e => e.sites)
    );
  }
}

/**
 * Fetch a single site with billing data
 * @param {number} siteId
 * @returns {Promise<import('./types.js').Site>}
 */
export async function fetchSiteWithBilling(siteId) {
  try {
    const [siteData, billingData] = await Promise.all([
      getSite(siteId),
      getSiteBilling(siteId).catch(() => null),
    ]);
    const site = mapBackendSiteToDomain(siteData);
    if (billingData) {
      site.billing = mapBillingToDomain(billingData);
    }
    return site;
  } catch {
    // Search demo
    for (const org of DEMO_ORGANIZATIONS) {
      for (const entity of org.entities) {
        const found = entity.sites.find(s => s.id === siteId);
        if (found) return found;
      }
    }
    return null;
  }
}

/**
 * Fetch billing anomalies for selected sites
 * @param {number[]} siteIds
 * @returns {Promise<import('./types.js').Anomaly[]>}
 */
export async function fetchAnomalies(siteIds) {
  try {
    const insights = await getBillingInsights({ site_ids: siteIds.join(',') });
    const items = Array.isArray(insights) ? insights : insights?.items || [];
    return items
      .filter(i => i.severity === 'high' || i.severity === 'critical' || i.severity === 'medium')
      .map(mapInsightToAnomaly);
  } catch {
    // Fallback: aggregate demo anomalies
    const agg = aggregateDemoSites(siteIds);
    return agg.anomalies;
  }
}

/**
 * Fetch purchase preferences (persona, horizon, etc.)
 * @returns {Promise<Object>}
 */
export async function fetchPreferences() {
  try {
    return await getPurchasePreferences();
  } catch {
    return null;
  }
}

/**
 * Fetch purchase assumptions for a site
 * @param {number} siteId
 * @returns {Promise<Object>}
 */
export async function fetchAssumptions(siteId) {
  try {
    return await getPurchaseAssumptions(siteId);
  } catch {
    return null;
  }
}

// ── Demo Mode Adapter ──────────────────────────────────────────────

/**
 * Get full demo dataset (orgs, sites, offers)
 * @returns {{ organizations: Object[], offers: Object[], sites: Object[] }}
 */
export function getDemoDataset() {
  const sites = DEMO_ORGANIZATIONS.flatMap(org =>
    org.entities.flatMap(e =>
      e.sites.map(s => ({
        ...s,
        organizationName: org.name,
        entityName: e.name,
      }))
    )
  );

  return {
    organizations: DEMO_ORGANIZATIONS,
    offers: DEMO_OFFERS,
    sites,
  };
}

// ── Mapping Functions ──────────────────────────────────────────────

function mapBackendSiteToDomain(backendSite) {
  const energyType = (backendSite.type_energie || backendSite.energy_type || 'ELEC').toUpperCase();
  const isElec = energyType === 'ELEC' || energyType === 'ELECTRICITE';
  const annualKwh = backendSite.conso_annuelle_kwh || backendSite.annual_kwh || 0;
  const seasonality = isElec ? [...SEASONALITY_ELEC] : [...SEASONALITY_GAZ];

  return {
    id: backendSite.id,
    name: backendSite.nom || backendSite.name || `Site ${backendSite.id}`,
    city: backendSite.ville || backendSite.city || '',
    usage: backendSite.usage || backendSite.type_usage || '',
    surfaceM2: backendSite.surface_m2 || backendSite.surface || 0,
    energyType: isElec ? EnergyType.ELEC : EnergyType.GAZ,
    consumption: {
      annualKwh,
      monthlyKwh: (() => { const sum = seasonality.reduce((a, b) => a + b, 0); return seasonality.map(c => Math.round(annualKwh * c / sum)); })(),
      granularity: 'monthly',
      profileFactor: 1,
      seasonality,
      source: annualKwh > 0 ? 'B1' : 'DEFAULT',
    },
    billing: null,
    anomalies: [],
  };
}

function mapBillingToDomain(billingData) {
  if (!billingData) return null;

  const invoices = billingData.invoices || billingData.factures || [];
  const totalEur = invoices.reduce((sum, inv) => sum + (inv.montant_ttc || inv.total_eur || 0), 0);
  const totalKwh = invoices.reduce((sum, inv) => sum + (inv.kwh || inv.total_kwh || 0), 0);
  const anomalyCount = billingData.anomaly_count || billingData.nb_anomalies || 0;

  return {
    invoiceCount: invoices.length,
    totalEur,
    totalKwh,
    avgPricePerKwh: totalKwh > 0 ? totalEur / totalKwh : 0,
    anomalyCount,
    estimatedLossEur: billingData.estimated_loss_eur || billingData.perte_estimee || 0,
  };
}

function mapInsightToAnomaly(insight) {
  return {
    type: insight.rule_code || insight.type || 'UNKNOWN',
    severity: insight.severity || 'medium',
    message: insight.message || insight.description || '',
    estimatedLossEur: insight.impact_eur || insight.estimated_loss_eur || 0,
  };
}
