# Navigation — Legacy URL Redirects Inventory

Inventaire des alias `<Navigate>` dans `frontend/src/App.jsx`.
Ces routes existent pour compatibilité (bookmarks V1-V6, liens externes,
SEO potentiel). **Horizon de suppression : post-Lot 10 (~Q4 2026)**.

Généré : 2026-04-19 (chantier 2 navigation cleanup, branche `claude/refonte-visuelle-sol`).

## Alias actifs (22)

### Redirections simples (route → cible canonique)

| Alias (`path`) | Cible (`Navigate to`) | Raison |
|---|---|---|
| `/patrimoine/nouveau` | `/patrimoine?wizard=open` | Ouvre wizard site dans la page unifiée |
| `/sites` | `/patrimoine` | V1 avait `/sites` séparé, merged V92 |
| `/dashboard-legacy` | `/` | Ancien dashboard interne |
| `/sites-legacy/:id` | `/patrimoine` | Route historique Site V1 |
| `/action-plan` | `/anomalies` | Fusion actions+anomalies V103 |
| `/compliance` | `/conformite` | Route anglaise → canonique FR (V92) |
| `/compliance/sites` | `/conformite` | Idem, alias liste |
| `/achat-assistant` | `/achat-energie?tab=assistant` | Assistant embarqué comme tab PurchasePage |
| `/explorer` | `/consommations/portfolio` | Onglet regroupement par défaut |

### URL aliases (section documentée App.jsx)

| Alias | Cible | Raison |
|---|---|---|
| `/plan-action` | `/anomalies?tab=actions` | Wording pilote → canonique |
| `/plan-actions` | `/anomalies?tab=actions` | Variant pluriel |
| `/factures` | `/bill-intel` | Terme métier → route technique |
| `/facturation` | `/billing` | Mode expert facturation |
| `/diagnostic` | `/diagnostic-conso` | Shortcut sans suffix |
| `/performance` | `/monitoring` | Wording V6 |
| `/achats` | `/achat-energie` | Pluriel naturel |
| `/purchase` | `/achat-energie` | Route anglaise |
| `/referentiels` | `/kb` | Ancien nom Mémobox |
| `/synthese` | `/cockpit` | Ancien nom cockpit |
| `/executive` | `/cockpit` | Ancien nom cockpit exécutif |
| `/dashboard` | `/cockpit` | Ancien nom (V1) |
| `/conso` | `/consommations/portfolio` | Shortcut |
| `/imports` | `/import` | Pluriel |
| `/connexions` | `/connectors` | FR → EN (config technique) |
| `/veille` | `/watchers` | FR → EN (config technique) |
| `/alertes` | `/notifications` | Ancien nom Centre notifications |
| `/ems` | `/consommations/portfolio` | Route historique EMS V1 |
| `/donnees` | `/activation` | Page activation données |
| `/contracts-radar` | `/renouvellements` | Route technique → canonique FR |

## Plan de suppression (horizon Lot 10, post-refonte complète)

1. Analyser les logs d'accès sur 3 mois (via nginx ou backend middleware).
2. Pour chaque alias avec < 10 hits/mois : retirer le `<Navigate>` + ajouter
   aux 404 smart redirects côté backend si nécessaire.
3. Alias `/sites`, `/purchase`, `/dashboard` : probablement à garder plus
   longtemps (bookmarks historiques fréquents).
4. Après suppression : update ce fichier + changelog navigation + annoncer
   aux pilotes (3 mois de préavis minimum).

## Notes

- Les alias NE SONT PAS mappés dans `NAV_REGISTRY.ROUTE_MODULE_MAP`
  (volontairement — on ne veut pas qu'ils apparaissent dans la nav).
- Le breadcrumb (`Breadcrumb.jsx`) connaît certains segments d'alias
  (`factures`, `achats`, `synthese`…) pour le cas où un user atterrit sur
  l'URL alias avant que React Router ait effectué le redirect (rare).
- Tests Playwright smoke : vérifier que chaque alias redirige bien vers
  sa cible canonique (non-régression).
