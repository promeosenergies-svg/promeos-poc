/**
 * PROMEOS — Registry canonique des onglets Site360 (Sprint P0 routes mortes).
 *
 * Source de vérité unique pour les onglets de la vue Site360. Chaque
 * onglet doit respecter le contrat :
 *
 *   {
 *     id          : string  — identifiant interne (activeTab switch)
 *     label       : string  — libellé FR métier (jamais de jargon EN)
 *     status      : 'enabled' | 'hidden'
 *     renderMode  : 'panel' | 'redirect' | 'link'
 *     targetRoute : string? — route canonique si redirect/link (résolue
 *                              côté composant avec le siteId)
 *     emptyState  : string? — message FR métier si données absentes
 *     testId      : string  — sélecteur stable pour vitest/Playwright
 *   }
 *
 * Doctrine P0 :
 * - Aucun onglet visible ne doit être vide / mort / décoratif.
 * - Aucun label « Analytics », « TODO », « Coming soon ».
 * - Aucun lien `#` ou route 404.
 * - Réconciliation reste cachable si module non raccordé (status='hidden').
 */

/**
 * @typedef {Object} Site360TabDef
 * @property {string} id
 * @property {string} label
 * @property {'enabled'|'hidden'} status
 * @property {'panel'|'redirect'|'link'} renderMode
 * @property {string=} targetRoute
 * @property {string=} emptyState
 * @property {string} testId
 */

/** @type {Site360TabDef[]} */
export const SITE360_TABS = [
  {
    id: 'resume',
    label: 'Résumé',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Compléter les données du site pour activer la synthèse 360.',
    testId: 'site360-tab-resume',
  },
  {
    id: 'conso',
    label: 'Consommation',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Aucune mesure de consommation sur ce site.',
    testId: 'site360-tab-conso',
  },
  {
    id: 'analytics',
    label: 'Analyse énergétique',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Données analytiques en cours de construction pour ce site.',
    testId: 'site360-tab-analytics',
  },
  {
    id: 'factures',
    label: 'Factures',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Aucune facture importée pour ce site.',
    testId: 'site360-tab-factures',
  },
  {
    id: 'reconciliation',
    label: 'Réconciliation',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Aucune anomalie de réconciliation détectée.',
    testId: 'site360-tab-reconciliation',
  },
  {
    id: 'conformite',
    label: 'Conformité',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Compléter les données réglementaires du site.',
    testId: 'site360-tab-conformite',
  },
  {
    id: 'actions',
    label: 'Actions',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Aucune action ouverte sur ce site.',
    testId: 'site360-tab-actions',
  },
  {
    id: 'puissance',
    label: 'Puissance',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Aucune mesure de puissance disponible pour ce site.',
    testId: 'site360-tab-puissance',
  },
  {
    id: 'usages',
    label: 'Usages',
    status: 'enabled',
    renderMode: 'panel',
    emptyState: 'Données d’usages à compléter pour ce site.',
    testId: 'site360-tab-usages',
  },
];

/**
 * Routes canoniques cibles pour les CTA Site360 (jamais hardcodées
 * dans les composants). Toutes ces routes doivent exister dans App.jsx.
 */
export const SITE360_CANONICAL_ROUTES = Object.freeze({
  consommation: '/consommations/courbe',
  monitoring: '/monitoring',
  factures: '/billing',
  achatEnergie: '/achat-energie',
  conformite: '/conformite',
  actionsCenter: '/action-center-v4',
  usages: '/usages',
  patrimoine: '/patrimoine',
  kb: '/kb',
  regops: '/regops',
});

/** Retourne uniquement les tabs `status === 'enabled'`. */
export function getEnabledSite360Tabs() {
  return SITE360_TABS.filter((t) => t.status === 'enabled');
}

/** Recherche d'un tab par son `id`. */
export function findSite360Tab(id) {
  return SITE360_TABS.find((t) => t.id === id) || null;
}
