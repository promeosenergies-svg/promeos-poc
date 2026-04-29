/**
 * legacyRedirects — Table canonique des redirects legacy.
 *
 * Phase 3.bis.a sprint refonte cockpit dual sol2 (29/04/2026). Factorise
 * les 31 `<Route path=X element={<Navigate to=Y replace />}>` qui étaient
 * dispersés dans App.jsx (P1 /simplify reuse audit fin Phase 3).
 *
 * Convention : chaque entrée [from, to] représente un alias historique
 * (ancien lien externe, anciens noms de page, branches mortes, ou
 * redirects post-restructuration de la nav). React Router résoud le
 * matching le plus spécifique → l'ordre de cette liste n'a pas d'impact
 * sur le routing, mais on groupe par thème pour faciliter l'audit.
 */

export const LEGACY_REDIRECTS = [
  // ── Patrimoine & sites ────────────────────────────────────────────────
  ['/patrimoine/nouveau', '/patrimoine?wizard=open'],
  ['/sites', '/patrimoine'],
  ['/sites-legacy/:id', '/patrimoine'],

  // ── Cockpit dual sol2 (Phase 3.1) ──────────────────────────────────────
  ['/cockpit', '/cockpit/jour'],
  ['/synthese', '/cockpit/strategique'],
  ['/executive', '/cockpit/strategique'],
  ['/dashboard', '/cockpit/strategique'],
  ['/dashboard-legacy', '/'],
  ['/tableau-de-bord', '/cockpit/jour'],

  // ── Conformité & action-plan ──────────────────────────────────────────
  ['/action-plan', '/anomalies'],
  ['/plan-action', '/anomalies?tab=actions'],
  ['/plan-actions', '/anomalies?tab=actions'],
  ['/compliance', '/conformite'],
  ['/compliance/sites', '/conformite'],

  // ── Bill-intel & facturation ──────────────────────────────────────────
  ['/factures', '/bill-intel'],
  ['/facturation', '/billing'],

  // ── Achat énergie ──────────────────────────────────────────────────────
  ['/achat-assistant', '/achat-energie?tab=assistant'],
  ['/achats', '/achat-energie'],
  ['/purchase', '/achat-energie'],
  ['/contracts-radar', '/renouvellements'],

  // ── Consommations / monitoring / EMS ──────────────────────────────────
  ['/conso', '/consommations/portfolio'],
  ['/explorer', '/consommations/portfolio'],
  ['/ems', '/consommations/portfolio'],
  ['/diagnostic', '/diagnostic-conso'],
  ['/performance', '/monitoring'],
  ['/donnees', '/activation'],

  // ── Imports / connecteurs / observabilité ────────────────────────────
  ['/imports', '/import'],
  ['/connexions', '/connectors'],
  ['/veille', '/watchers'],
  ['/alertes', '/notifications'],

  // ── Référentiels ──────────────────────────────────────────────────────
  ['/referentiels', '/kb'],
];
