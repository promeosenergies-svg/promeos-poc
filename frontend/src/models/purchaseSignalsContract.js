/**
 * PROMEOS — PurchaseSignalsContract V36
 * Contract pour les signaux achat d'energie (renouvellement, couverture, manquants).
 *
 * Derive des endpoints existants:
 *   GET /api/purchase/renewals   → echeances contrats
 *   GET /api/patrimoine/contracts → liste contrats org-scoped
 *
 * Exports:
 *   normalizePurchaseSignals(raw)   → PurchaseSignals | EMPTY
 *   EMPTY_PURCHASE_SIGNALS          → valeur par defaut (safe)
 *   isPurchaseAvailable(signals)    → boolean
 */

/**
 * @typedef {object} PurchaseRenewal
 * @property {number}  contract_id
 * @property {number}  site_id
 * @property {string}  [site_nom]
 * @property {string}  [supplier_name]
 * @property {string}  [energy_type]
 * @property {string}  [end_date]
 * @property {number}  days_until_expiry
 * @property {boolean} [auto_renew]
 */

/**
 * @typedef {object} PurchaseSignals
 * @property {PurchaseRenewal[]} renewals       — echeances filtrees et validees
 * @property {number}  totalContracts           — nombre total de contrats en base
 * @property {number}  totalSites               — nombre total de sites dans le scope
 * @property {number}  expiringSoonCount        — contrats expirant dans <= 90 jours
 * @property {number[]} expiringSoonSites       — site_ids dedupliques des expirations proches
 * @property {number}  coverageContractsPct     — % de sites ayant au moins 1 contrat
 * @property {number}  missingContractsCount    — sites sans aucun contrat
 * @property {number|null} estimatedExposureEur — null en V1 (non calculable sans ref marche)
 * @property {boolean} isApproximate            — true en V1
 */

const EXPIRING_SOON_DAYS = 90;

export const EMPTY_PURCHASE_SIGNALS = Object.freeze({
  renewals: [],
  totalContracts: 0,
  totalSites: 0,
  expiringSoonCount: 0,
  expiringSoonSites: [],
  coverageContractsPct: 0,
  missingContractsCount: 0,
  estimatedExposureEur: null,
  isApproximate: true,
});

/**
 * Normalise les donnees brutes (renewals + contracts + totalSites) en PurchaseSignals.
 * Retourne EMPTY_PURCHASE_SIGNALS si input invalide ou vide.
 *
 * @param {any} raw — { renewals: ApiRenewalsResponse, contracts: ApiContractsResponse, totalSites: number }
 * @returns {PurchaseSignals}
 */
export function normalizePurchaseSignals(raw) {
  if (!raw || typeof raw !== 'object') return EMPTY_PURCHASE_SIGNALS;

  // Extraire les renewals valides
  const rawRenewals = raw.renewals?.renewals ?? raw.renewals?.data ?? [];
  const renewals = Array.isArray(rawRenewals)
    ? rawRenewals.filter((r) => r && typeof r.site_id === 'number' && typeof r.days_until_expiry === 'number')
    : [];

  // Extraire les contracts
  const rawContracts = raw.contracts?.contracts ?? raw.contracts?.data ?? [];
  const contractsList = Array.isArray(rawContracts) ? rawContracts : [];
  const totalContracts = typeof raw.contracts?.total === 'number' ? raw.contracts.total : contractsList.length;

  // Total sites
  const totalSites = typeof raw.totalSites === 'number' ? Math.max(0, raw.totalSites) : 0;

  // Si rien du tout → EMPTY
  if (renewals.length === 0 && totalContracts === 0 && totalSites === 0) return EMPTY_PURCHASE_SIGNALS;

  // Expirations proches (<= 90 jours)
  const expiringSoon = renewals.filter((r) => r.days_until_expiry <= EXPIRING_SOON_DAYS);
  const expiringSoonCount = expiringSoon.length;
  const expiringSoonSites = [...new Set(expiringSoon.map((r) => r.site_id))];

  // Couverture: sites uniques ayant au moins 1 contrat
  const sitesWithContract = new Set(contractsList.map((c) => c?.site_id).filter(Boolean));
  const coverageContractsPct = totalSites > 0 ? Math.round((sitesWithContract.size / totalSites) * 100) : 0;
  const missingContractsCount = Math.max(0, totalSites - sitesWithContract.size);

  return {
    renewals,
    totalContracts,
    totalSites,
    expiringSoonCount,
    expiringSoonSites,
    coverageContractsPct,
    missingContractsCount,
    estimatedExposureEur: null, // V1: non calculable sans donnees marche
    isApproximate: true,
  };
}

/**
 * Verifie si des signaux d'achat sont disponibles et exploitables.
 *
 * @param {PurchaseSignals|null|undefined} signals
 * @returns {boolean}
 */
export function isPurchaseAvailable(signals) {
  return !!(signals && (signals.expiringSoonCount > 0 || signals.missingContractsCount > 0 || signals.totalContracts > 0));
}
