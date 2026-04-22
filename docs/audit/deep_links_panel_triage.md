# Triage panel deep-links — pré-vague 1

> **Contexte** : le commit `f679f14c` a vidé `PANEL_SECTIONS_BY_ROUTE = {}` pour corriger 14 divergences SSOT. Dommage collatéral : des deep-links paramétrés légitimes (`?filter=`, `?tab=`, `?horizon=`, `?fw=`) ont disparu avec.
>
> **But du doc** : trier chaque entrée historique des 14 routes en 3 catégories avant tout rétablissement. **Audit exhaustif puis rétablissement chirurgical.**
>
> **Date** : 2026-04-22 · **Source historique** : `git show 068b0979^:frontend/src/layout/NavRegistry.js`

## 3 types d'entrées historiques

| Type | Définition | Action |
|---|---|---|
| `DEEP_LINK` | Query param (`?x=y`) OU sous-path absent de NAV_SECTIONS. Raccourci additif légitime. | Candidat rétablissement (Vague 1 ou Vague 2) |
| `DIVERGENCE_SSOT` | Duplique un label/route de NAV_SECTIONS OU ajoute une section concurrente à l'architecture main. | ❌ NE PAS RÉTABLIR |
| `ITEM_CACHÉ_RÉEXPOSÉ` | Route volontairement masquée de NAV_SECTIONS main (ex: `/actions`, `/notifications` redirigés vers Centre d'actions header). | ❌ NE PAS RÉTABLIR |

## Classement par route (14 routes)

### `/` (Command Center)

| Entrée historique | Type | Décision |
|---|---|---|
| Section "Pouls patrimoine" → /actions, /notifications | `ITEM_CACHÉ_RÉEXPOSÉ` | ❌ NE PAS RÉTABLIR (masqués volontairement par NAV_SECTIONS[cockpit] pour redirection vers Centre d'actions header) |
| Section "Modules" → /cockpit, /conformite, /bill-intel, /patrimoine, /achat-energie | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (duplique le rail + labels divergents "Cockpit exécutif" vs SSOT "Accueil", "Facturation" top-level alors que sous-item Patrimoine) |

### `/cockpit`

| Entrée historique | Type | Décision |
|---|---|---|
| Section "Cette semaine" (Vue d'accueil, Journal d'actions, Alertes) | `DIVERGENCE_SSOT` + `ITEM_CACHÉ_RÉEXPOSÉ` | ❌ NE PAS RÉTABLIR (override complet + expose /actions, /notifications) |
| Section "Horizons" (/conformite "Trajectoire 2030", /conformite/aper "Trajectoire 2040") | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (relabellise des routes NAV_SECTIONS top-level) |
| Section "Vue d'ensemble" → /patrimoine "Patrimoine" | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (duplique label NAV_SECTIONS) |
| `/cockpit-fixtures` | `DEEP_LINK` (sous-path) | ⚠️ SKIP V1 (expert obscur, pas de valeur métier DAF/RSE) |

### `/conformite`

| Entrée historique | Type | Décision |
|---|---|---|
| Section "Surveillance" → /conformite, /conformite/audit-sme | `DEEP_LINK` partiel (audit-sme = sous-path légitime) | ⚠️ VAGUE 2 (à trancher UX) |
| Section "Échéances" → /conformite/tertiaire, /conformite/bacs, /conformite/aper + badges deadlines DT/BACS | `DEEP_LINK` enrichi (badges) | ⚠️ VAGUE 2 (badges = info enrichie, arbitrage produit) |
| Section "Sites critiques" → /compliance/pipeline, /regops/dashboard | `DEEP_LINK` (sous-paths) | ⚠️ VAGUE 2 (expert mais valeur opérationnelle) |

### `/conformite/aper`

| Entrée historique | Type | Décision |
|---|---|---|
| `?filter=parking` (> 1 500 m²) | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| `?filter=toiture` (> 500 m²) | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| Section "Actions" → /conformite "Retour conformité" | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (duplique top-level) |

### `/monitoring`

| Entrée historique | Type | Décision |
|---|---|---|
| Section "Surveillance" → /diagnostic-conso | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (duplique NAV_SECTIONS[energie] item "Diagnostics") |
| Section "Consommations" → /consommations, /usages, /usages-horaires | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (tous top-level NAV_SECTIONS[energie]) |

### `/bill-intel`

| Entrée historique | Type | Décision |
|---|---|---|
| `?tab=anomalies` | `DEEP_LINK` (query param) | ⚠️ VAGUE 2 |
| `?tab=contestations` | `DEEP_LINK` (query param) | ⚠️ VAGUE 2 |
| /portfolio-reconciliation | `DEEP_LINK` (sous-path) | ❌ SKIP définitif (expert obscur, 0 usage démo) |
| /payment-rules | `DEEP_LINK` (sous-path) | ❌ SKIP définitif (admin-like, peu d'usage) |
| /billing "Factures détaillées" | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (/billing = top-level NAV_SECTIONS) |

### `/patrimoine`

| Entrée historique | Type | Décision |
|---|---|---|
| `?type=bureau` | `DEEP_LINK` (query param) | ❌ SKIP V1 (faible preuve d'usage, pattern non standardisé) |
| `?type=entrepot` | `DEEP_LINK` | ❌ SKIP V1 |
| `?type=enseignement` | `DEEP_LINK` | ❌ SKIP V1 |
| /onboarding/sirene | `DEEP_LINK` (sous-path) | ❌ SKIP V1 (action ponctuelle, pas un filtre récurrent) |
| /bill-intel "Facturation" + /contrats "Contrats énergie" | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (duplique NAV_SECTIONS[patrimoine]) |

### `/achat-energie`

| Entrée historique | Type | Décision |
|---|---|---|
| `?tab=marche` | `DEEP_LINK` (query param) | ⚠️ VAGUE 2 (parcours DAF) |
| `?tab=assistant` | `DEEP_LINK` (query param) | ⚠️ VAGUE 2 |
| `?tab=portefeuille` | `DEEP_LINK` (query param) | ⚠️ VAGUE 2 |
| Section "Contrats" → /renouvellements, /contrats | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (top-level NAV_SECTIONS) |

### `/anomalies`

| Entrée historique | Type | Décision |
|---|---|---|
| `?fw=DECRET_TERTIAIRE` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| `?fw=FACTURATION` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| `?fw=BACS` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| Section "Actions" → /actions "Journal d'actions" | `ITEM_CACHÉ_RÉEXPOSÉ` | ❌ NE PAS RÉTABLIR |

### `/contrats`

| Entrée historique | Type | Décision |
|---|---|---|
| `?filter=expiring` | `DEEP_LINK` (query param) | ❌ SKIP V1 (à revalider UX, redondant avec /renouvellements?horizon=90) |
| `?filter=active` | `DEEP_LINK` | ❌ SKIP V1 (état par défaut, deep-link redondant) |
| Section "Achat d'énergie" → /renouvellements, /achat-energie | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR |

### `/renouvellements`

| Entrée historique | Type | Décision |
|---|---|---|
| `?horizon=90` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| `?horizon=180` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| `?horizon=365` | `DEEP_LINK` (query param) | ✅ **VAGUE 1** |
| Section "Contexte" → /contrats "Fiches contrats" | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR |

### `/usages`

| Entrée historique | Type | Décision |
|---|---|---|
| Section "Usages énergétiques" → /usages, /usages-horaires | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR (top-level NAV_SECTIONS[energie]) |
| Section "Contexte" → /diagnostic-conso, /monitoring | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR |

### `/usages-horaires`

| Entrée historique | Type | Décision |
|---|---|---|
| `?tab=profile` | `DEEP_LINK` (query param) | ❌ SKIP V1 (tab natif de la page, pas besoin d'exposer en panel) |
| `?tab=horaires` | `DEEP_LINK` | ❌ SKIP V1 |
| Section "Contexte" → /usages | `DIVERGENCE_SSOT` | ❌ NE PAS RÉTABLIR |

### `/watchers`

| Entrée historique | Type | Décision |
|---|---|---|
| `?status=new` | `DEEP_LINK` (query param) | ❌ SKIP V1 (status par défaut, peu valeur ajoutée) |
| `?status=applied` | `DEEP_LINK` | ❌ SKIP V1 |

## Récap Vague 1

✅ **8 deep-links rétablis** sur 3 routes à haute valeur métier réglementaire :

- `/anomalies` × 3 frameworks (DECRET_TERTIAIRE, FACTURATION, BACS)
- `/renouvellements` × 3 horizons (90j, 180j, 365j)
- `/conformite/aper` × 2 filtres (parking, toiture)

**Critères de sélection Vague 1** :
- Query param pur (pas de sous-path nouveau)
- Valeur métier démontrée (filtres réglementaires quotidiens DAF/RSE)
- Zéro risque SSOT (aucun label NAV_SECTIONS concurrent)

## Récap Vague 2 (non-incluse ce sprint)

⚠️ **À arbitrer après feedback Vague 1** :

- `/conformite` badges deadlines DT/BACS/APER + sous-pages (audit-sme, pipeline, regops/dashboard)
- `/bill-intel` tabs (anomalies, contestations)
- `/achat-energie` tabs (marché, assistant, portefeuille)

**Pourquoi Vague 2 séparée** : ces 3 cas demandent un arbitrage UX plus fin (badges = info enrichie avec data temps réel, tabs = navigation intra-page qui pourrait vivre dans les pages elles-mêmes).

## Récap SKIP définitif

❌ **Ne revient pas** (ni V1 ni V2) :

### Divergences SSOT structurelles (16 entrées)
- `/cockpit` sections sémantiques Sol ("Cette semaine / Horizons / Vue d'ensemble")
- `/monitoring`, `/usages`, `/usages-horaires` sections listant des top-level NAV_SECTIONS
- `/patrimoine`, `/contrats`, `/renouvellements`, `/achat-energie`, `/conformite/aper` sections "Actions" / "Contexte" listant des redirections rail

### Items cachés volontairement (4 entrées)
- `/actions`, `/notifications` (redirigés Centre d'actions header)
- Reapparitions "Journal d'actions", "Alertes", "Pouls patrimoine" depuis `/`, `/cockpit`, `/anomalies`

### Items experts obscurs ou usage faible (9 entrées)
- `/cockpit-fixtures` (démo Sol V1 expert)
- `/portfolio-reconciliation`, `/payment-rules` (bill-intel expert)
- `/patrimoine?type=bureau/entrepot/enseignement` (pattern non-standardisé)
- `/onboarding/sirene` (action ponctuelle)
- `/contrats?filter=expiring/active`, `/usages-horaires?tab=*`, `/watchers?status=*` (redondants ou à faible valeur)

## Total historique vs total récap

| Compte | Valeur |
|---|---|
| Entrées historiques totales | ~50 items sur 14 routes |
| Rétablies Vague 1 | **8** (16%) |
| Candidates Vague 2 | ~10 (20%) |
| SKIP définitif (SSOT + cachés + obscurs) | ~32 (64%) |

## Prochaines phases du sprint

- **GATE 2** : test invariance TDD (`panel_deep_links_invariant.test.js`) créé avant remplissage. Initialement vert sur `{}`.
- **GATE 3** : renommage `PANEL_SECTIONS_BY_ROUTE` → `PANEL_DEEP_LINKS_BY_ROUTE` + merge additif (append "Raccourcis" à NAV_SECTIONS, pas replace).
- **GATE 4** : remplissage Vague 1 + test présence 8 deep-links.
- **GATE 5** : QA manuel + 12 captures A/B + régression 81/81 NavRegistry.
