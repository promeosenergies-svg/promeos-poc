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

  // ── Cockpit dual sol2 (Phase 3.1, MAJ Phase 13.D) ─────────────────────
  // Phase 13.D — Démo CFO/investisseur : /cockpit redirige vers la Vue
  // exécutive (Synthèse stratégique CFO 3min) au lieu du Briefing du jour
  // (Energy Manager 30s). Cohérent avec la sidebar qui place "Vue exécutive"
  // en premier (audience démo principale = CFO/DG/VC).
  ['/cockpit', '/cockpit/strategique'],
  ['/synthese', '/cockpit/strategique'],
  ['/executive', '/cockpit/strategique'],
  ['/dashboard', '/cockpit/strategique'],
  ['/dashboard-legacy', '/'],
  ['/tableau-de-bord', '/cockpit/jour'],

  // ── Conformité & action-plan ──────────────────────────────────────────
  // M2-5.11.L — bookmarks externes legacy repointés directement sur la
  // refonte Centre d'Action V4 (au lieu de /anomalies qui re-redirige V4
  // quand flag ON — anti double-hop). Voir audit routes M2-5.11.I+J+K.
  ['/action-plan', '/action-center-v4/pilotage'],
  ['/plan-action', '/action-center-v4/pilotage'],
  ['/plan-actions', '/action-center-v4/pilotage'],
  ['/compliance', '/conformite'],
  ['/compliance/sites', '/conformite'],
  // Sprint P0 Conformité (2026-05-20) — APER n'a plus de page dédiée
  // (doctrine C1 : encart léger dans /conformite onglet Obligations).
  // Préserve les bookmarks externes / liens dans la KB historique.
  ['/conformite/aper', '/conformite?tab=obligations&filter=aper'],

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
  // M2-5.11.L — alertes pointe directement le Journal V4 (cross-items 7j)
  // au lieu de /notifications qui re-redirige (anti double-hop).
  ['/alertes', '/action-center-v4/pilotage/journal'],

  // ── Référentiels ──────────────────────────────────────────────────────
  ['/referentiels', '/kb'],
];
