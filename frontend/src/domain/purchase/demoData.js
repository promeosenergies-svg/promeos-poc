/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Demo Data — 2 portfolios, 5 offers (4 clean + 1 dirty)
 *
 * Ready-to-use datasets for demo mode.
 */
import { EnergyType, OfferStructure, SEASONALITY_ELEC, SEASONALITY_GAZ } from './types.js';

// ── Demo Organizations ─────────────────────────────────────────────

export const DEMO_ORGANIZATIONS = [
  {
    id: 'org-demo-1',
    name: 'Groupe Industriel Rhone-Alpes',
    siren: '123456789',
    entities: [
      {
        id: 'ej-demo-1',
        name: 'GIRA Production SAS',
        siret: '12345678900001',
        nafCode: '2511Z',
        sites: [
          {
            id: 1,
            name: 'Usine Lyon',
            city: 'Lyon',
            usage: 'Industriel',
            surfaceM2: 12000,
            energyType: EnergyType.ELEC,
            consumption: {
              annualKwh: 2400000,
              monthlyKwh: SEASONALITY_ELEC.map(c => Math.round(2400000 * c / 12)),
              granularity: 'monthly',
              profileFactor: 1.15,
              seasonality: [...SEASONALITY_ELEC],
              source: 'DEMO',
            },
            billing: {
              invoiceCount: 24,
              totalEur: 480000,
              totalKwh: 4800000,
              avgPricePerKwh: 0.10,
              anomalyCount: 2,
              estimatedLossEur: 3200,
            },
            anomalies: [
              { type: 'DOUBLE_CHARGE', severity: 'high', message: 'Double facturation detectee mois 06/2024', estimatedLossEur: 1800 },
              { type: 'ESTIMATION_ECART', severity: 'medium', message: 'Ecart estimation > 15% mois 11/2024', estimatedLossEur: 1400 },
            ],
          },
          {
            id: 2,
            name: 'Entrepot Grenoble',
            city: 'Grenoble',
            usage: 'Logistique',
            surfaceM2: 5000,
            energyType: EnergyType.ELEC,
            consumption: {
              annualKwh: 800000,
              monthlyKwh: SEASONALITY_ELEC.map(c => Math.round(800000 * c / 12)),
              granularity: 'monthly',
              profileFactor: 0.95,
              seasonality: [...SEASONALITY_ELEC],
              source: 'DEMO',
            },
            billing: {
              invoiceCount: 12,
              totalEur: 96000,
              totalKwh: 800000,
              avgPricePerKwh: 0.12,
              anomalyCount: 0,
              estimatedLossEur: 0,
            },
            anomalies: [],
          },
        ],
      },
    ],
  },
  {
    id: 'org-demo-2',
    name: 'Tertiaire Services IDF',
    siren: '987654321',
    entities: [
      {
        id: 'ej-demo-2',
        name: 'TSI Bureaux SARL',
        siret: '98765432100001',
        nafCode: '6820A',
        sites: [
          {
            id: 3,
            name: 'Siege Paris 8e',
            city: 'Paris',
            usage: 'Bureaux',
            surfaceM2: 3000,
            energyType: EnergyType.GAZ,
            consumption: {
              annualKwh: 600000,
              monthlyKwh: SEASONALITY_GAZ.map(c => Math.round(600000 * c / 12)),
              granularity: 'monthly',
              profileFactor: 1.0,
              seasonality: [...SEASONALITY_GAZ],
              source: 'DEMO',
            },
            billing: {
              invoiceCount: 18,
              totalEur: 54000,
              totalKwh: 600000,
              avgPricePerKwh: 0.09,
              anomalyCount: 1,
              estimatedLossEur: 500,
            },
            anomalies: [
              { type: 'INDEX_MISMATCH', severity: 'medium', message: 'Index PEG different du contrat', estimatedLossEur: 500 },
            ],
          },
        ],
      },
    ],
  },
];

// ── Demo Offers ────────────────────────────────────────────────────

export const DEMO_OFFERS = [
  // Offer 1: FIXE — EDF Entreprises
  {
    id: 'offer-fixe-edf',
    supplierName: 'EDF Entreprises',
    structure: OfferStructure.FIXE,
    pricing: {
      fixedPriceEurPerMwh: 95,
      indexName: null,
      spreadEurPerMwh: 0,
      capEurPerMwh: null,
      floorEurPerMwh: null,
      fixedSharePct: 1,
      indexedSharePct: 0,
      spotSharePct: 0,
    },
    breakdown: [
      { component: 'FOURNITURE', sharePct: 0.38, eurPerMwh: 36.1, status: 'KNOWN' },
      { component: 'ACHEMINEMENT', sharePct: 0.26, eurPerMwh: 24.7, status: 'KNOWN' },
      { component: 'TAXES_CSPE', sharePct: 0.14, eurPerMwh: 13.3, status: 'KNOWN' },
      { component: 'CTA', sharePct: 0.03, eurPerMwh: 2.85, status: 'KNOWN' },
      { component: 'TVA', sharePct: 0.10, eurPerMwh: 9.5, status: 'KNOWN' },
      { component: 'CEE', sharePct: 0.04, eurPerMwh: 3.8, status: 'KNOWN' },
      { component: 'CAPACITE', sharePct: 0.03, eurPerMwh: 2.85, status: 'KNOWN' },
      { component: 'ABONNEMENT', sharePct: 0.02, eurPerMwh: 1.9, status: 'KNOWN' },
    ],
    contractTerms: {
      durationMonths: 24,
      noticePeriodDays: 90,
      earlyTerminationPenalty: 'MODERATE',
      indexationClause: 'CLEAR',
      slaLevel: 'BASIC',
      greenCertified: false,
      clauseFlags: [],
    },
    intermediation: {
      hasIntermediary: false,
      feeDisclosed: true,
      feeEurPerMwh: 0,
      passThroughPolicy: 'FULL',
    },
    dataTerms: {
      curvesAccess: true,
      dplus1: true,
      csvExport: true,
      apiAccess: false,
    },
  },

  // Offer 2: INDEXE — Engie Pro
  {
    id: 'offer-indexe-engie',
    supplierName: 'Engie Pro',
    structure: OfferStructure.INDEXE,
    pricing: {
      fixedPriceEurPerMwh: 0,
      indexName: 'EPEX Spot FR',
      spreadEurPerMwh: 5,
      capEurPerMwh: 130,
      floorEurPerMwh: 50,
      fixedSharePct: 0,
      indexedSharePct: 1,
      spotSharePct: 0,
    },
    breakdown: [
      { component: 'FOURNITURE', sharePct: 0.36, eurPerMwh: null, status: 'ESTIMATED' },
      { component: 'ACHEMINEMENT', sharePct: 0.27, eurPerMwh: 24.3, status: 'KNOWN' },
      { component: 'TAXES_CSPE', sharePct: 0.15, eurPerMwh: 13.5, status: 'KNOWN' },
      { component: 'CTA', sharePct: 0.03, eurPerMwh: 2.7, status: 'KNOWN' },
      { component: 'TVA', sharePct: 0.10, eurPerMwh: null, status: 'ESTIMATED' },
      { component: 'CEE', sharePct: 0.04, eurPerMwh: 3.6, status: 'KNOWN' },
      { component: 'CAPACITE', sharePct: 0.03, eurPerMwh: 2.7, status: 'KNOWN' },
      { component: 'ABONNEMENT', sharePct: 0.02, eurPerMwh: 1.8, status: 'KNOWN' },
    ],
    contractTerms: {
      durationMonths: 12,
      noticePeriodDays: 60,
      earlyTerminationPenalty: 'LOW',
      indexationClause: 'CLEAR',
      slaLevel: 'PREMIUM',
      greenCertified: true,
      clauseFlags: [],
    },
    intermediation: {
      hasIntermediary: false,
      feeDisclosed: true,
      feeEurPerMwh: 0,
      passThroughPolicy: 'FULL',
    },
    dataTerms: {
      curvesAccess: true,
      dplus1: true,
      csvExport: true,
      apiAccess: true,
    },
  },

  // Offer 3: HYBRIDE — TotalEnergies
  {
    id: 'offer-hybride-total',
    supplierName: 'TotalEnergies',
    structure: OfferStructure.HYBRIDE,
    pricing: {
      fixedPriceEurPerMwh: 92,
      indexName: 'EPEX Spot FR',
      spreadEurPerMwh: 3,
      capEurPerMwh: 120,
      floorEurPerMwh: null,
      fixedSharePct: 0.60,
      indexedSharePct: 0.25,
      spotSharePct: 0.15,
    },
    breakdown: [
      { component: 'FOURNITURE', sharePct: 0.37, eurPerMwh: null, status: 'ESTIMATED' },
      { component: 'ACHEMINEMENT', sharePct: 0.27, eurPerMwh: 24.3, status: 'KNOWN' },
      { component: 'TAXES_CSPE', sharePct: 0.14, eurPerMwh: 12.6, status: 'KNOWN' },
      { component: 'CTA', sharePct: 0.03, eurPerMwh: 2.7, status: 'KNOWN' },
      { component: 'TVA', sharePct: 0.10, eurPerMwh: null, status: 'ESTIMATED' },
      { component: 'CEE', sharePct: 0.04, eurPerMwh: 3.6, status: 'KNOWN' },
      { component: 'CAPACITE', sharePct: 0.03, eurPerMwh: 2.7, status: 'KNOWN' },
      { component: 'ABONNEMENT', sharePct: 0.02, eurPerMwh: 1.8, status: 'KNOWN' },
    ],
    contractTerms: {
      durationMonths: 24,
      noticePeriodDays: 90,
      earlyTerminationPenalty: 'LOW',
      indexationClause: 'CLEAR',
      slaLevel: 'BASIC',
      greenCertified: true,
      clauseFlags: [],
    },
    intermediation: {
      hasIntermediary: true,
      feeDisclosed: true,
      feeEurPerMwh: 2.5,
      passThroughPolicy: 'PARTIAL',
    },
    dataTerms: {
      curvesAccess: true,
      dplus1: false,
      csvExport: true,
      apiAccess: false,
    },
  },

  // Offer 4: SPOT — Alpiq
  {
    id: 'offer-spot-alpiq',
    supplierName: 'Alpiq',
    structure: OfferStructure.SPOT,
    pricing: {
      fixedPriceEurPerMwh: 0,
      indexName: 'EPEX Spot FR',
      spreadEurPerMwh: 0,
      capEurPerMwh: null,
      floorEurPerMwh: null,
      fixedSharePct: 0,
      indexedSharePct: 0,
      spotSharePct: 1,
    },
    breakdown: [
      { component: 'FOURNITURE', sharePct: 0.40, eurPerMwh: null, status: 'UNKNOWN' },
      { component: 'ACHEMINEMENT', sharePct: 0.25, eurPerMwh: 22.5, status: 'KNOWN' },
      { component: 'TAXES_CSPE', sharePct: 0.14, eurPerMwh: 12.6, status: 'KNOWN' },
      { component: 'CTA', sharePct: 0.03, eurPerMwh: 2.7, status: 'KNOWN' },
      { component: 'TVA', sharePct: 0.10, eurPerMwh: null, status: 'UNKNOWN' },
    ],
    contractTerms: {
      durationMonths: 12,
      noticePeriodDays: 30,
      earlyTerminationPenalty: 'NONE',
      indexationClause: 'ABSENT',
      slaLevel: 'NONE',
      greenCertified: false,
      clauseFlags: ['NO_VOLUME_COMMITMENT'],
    },
    intermediation: {
      hasIntermediary: false,
      feeDisclosed: true,
      feeEurPerMwh: 0,
      passThroughPolicy: 'FULL',
    },
    dataTerms: {
      curvesAccess: false,
      dplus1: false,
      csvExport: false,
      apiAccess: false,
    },
  },

  // Offer 5: DIRTY — "Courtier Opaque SARL" (intentionally flawed)
  {
    id: 'offer-dirty-courtier',
    supplierName: 'Courtier Opaque SARL',
    structure: OfferStructure.HYBRIDE,
    pricing: {
      fixedPriceEurPerMwh: 105,
      indexName: 'Index Proprietaire',
      spreadEurPerMwh: 8,
      capEurPerMwh: null,    // no cap
      floorEurPerMwh: null,
      fixedSharePct: 0.30,
      indexedSharePct: 0.30,
      spotSharePct: 0.40,    // very high spot share
    },
    breakdown: [
      { component: 'FOURNITURE', sharePct: 0.45, eurPerMwh: null, status: 'UNKNOWN' },
      { component: 'ACHEMINEMENT', sharePct: 0.20, eurPerMwh: null, status: 'UNKNOWN' },
      // Only 2 components known — should trigger low transparency
    ],
    contractTerms: {
      durationMonths: 48,        // very long
      noticePeriodDays: 240,     // very long notice
      earlyTerminationPenalty: 'HIGH',
      indexationClause: 'VAGUE',
      slaLevel: 'NONE',
      greenCertified: false,
      clauseFlags: ['TACIT_RENEWAL', 'UNILATERAL_PRICE_CHANGE', 'NO_AUDIT_RIGHT'],
    },
    intermediation: {
      hasIntermediary: true,
      feeDisclosed: false,       // undisclosed fee
      feeEurPerMwh: 8,           // high hidden fee
      passThroughPolicy: 'UNLIMITED',  // unlimited pass-through
    },
    dataTerms: {
      curvesAccess: false,
      dplus1: false,
      csvExport: false,
      apiAccess: false,
    },
  },
];

// ── Aggregate Consumption Helper ───────────────────────────────────

/**
 * Aggregate consumption from demo sites
 * @param {number[]} siteIds - selected site IDs
 * @param {Object} [org] - organization to search in
 * @returns {{ annualKwh: number, energyType: string, consumption: Object, billing: Object, anomalies: Object[] }}
 */
export function aggregateDemoSites(siteIds, org = null) {
  const orgs = org ? [org] : DEMO_ORGANIZATIONS;
  const sites = [];

  for (const o of orgs) {
    for (const entity of o.entities) {
      for (const site of entity.sites) {
        if (siteIds.includes(site.id)) {
          sites.push(site);
        }
      }
    }
  }

  if (sites.length === 0) {
    return {
      annualKwh: 0,
      energyType: EnergyType.ELEC,
      consumption: { annualKwh: 0, granularity: 'monthly', profileFactor: 1, seasonality: [...SEASONALITY_ELEC], source: 'DEMO' },
      billing: { invoiceCount: 0, totalEur: 0, totalKwh: 0, avgPricePerKwh: 0, anomalyCount: 0, estimatedLossEur: 0 },
      anomalies: [],
    };
  }

  const annualKwh = sites.reduce((sum, s) => sum + s.consumption.annualKwh, 0);
  const energyType = sites[0].energyType;

  const billing = {
    invoiceCount: sites.reduce((sum, s) => sum + (s.billing?.invoiceCount || 0), 0),
    totalEur: sites.reduce((sum, s) => sum + (s.billing?.totalEur || 0), 0),
    totalKwh: sites.reduce((sum, s) => sum + (s.billing?.totalKwh || 0), 0),
    avgPricePerKwh: 0,
    anomalyCount: sites.reduce((sum, s) => sum + (s.billing?.anomalyCount || 0), 0),
    estimatedLossEur: sites.reduce((sum, s) => sum + (s.billing?.estimatedLossEur || 0), 0),
  };
  billing.avgPricePerKwh = billing.totalKwh > 0 ? billing.totalEur / billing.totalKwh : 0;

  const anomalies = sites.flatMap(s => s.anomalies || []);

  return {
    annualKwh,
    energyType,
    consumption: {
      annualKwh,
      granularity: 'monthly',
      profileFactor: 1,
      seasonality: energyType === EnergyType.GAZ ? [...SEASONALITY_GAZ] : [...SEASONALITY_ELEC],
      source: 'DEMO',
    },
    billing,
    anomalies,
  };
}

/**
 * Get all demo sites flat list
 * @returns {Array}
 */
export function getAllDemoSites() {
  const sites = [];
  for (const org of DEMO_ORGANIZATIONS) {
    for (const entity of org.entities) {
      for (const site of entity.sites) {
        sites.push({
          ...site,
          organizationName: org.name,
          entityName: entity.name,
        });
      }
    }
  }
  return sites;
}
