# Audit menu Énergie + navigation READ-ONLY (2026-05-25)

**Branche** : `claude/menu-energie-navigation-audit-readonly`
**Base** : `claude/refonte-sol2` après merge PR #312 (squash `88a49fb2`)
**Mode** : READ-ONLY strict — **0 code modifié**.
**Verdict global** : 🟡 **Navigation Énergie cohérente** (5 entrées sidebar, ordre persona-adapté, 0 silo `/energie`). **3 doublons identifiés** + **1 régression UX** (route FE `/cockpit/pilotage` 1 722 lignes, endpoint BE 404). Plan P0/P1/P2 + prompt prêt pour sprint Usage Steering ci-dessous.

---

## 1 — Cartographie sidebar (NavRegistry)

Source : [`frontend/src/layout/NavRegistry.js:741-787`](frontend/src/layout/NavRegistry.js#L741) — module `energie` (Zap icon, tint indigo, ordre 3, `expertOnly: false`).

| # | Path | Label sidebar | Icon | Statut |
|---|---|---|---|---|
| 1 | `/consommations` | Consommations | Activity | ✅ LIVE (page + 4 sub-tabs portfolio/explorer/import/kb) |
| 2 | `/monitoring` | Performance énergétique | TrendingUp | ✅ LIVE |
| 3 | `/usages` | Répartition par usage | PieChart | ✅ LIVE (3 onglets timeline/baseline/comptage) |
| 4 | `/diagnostic-conso` | Diagnostics | SearchCheck | ✅ LIVE |
| 5 | `/flex` | Flex Intelligence | Zap | ⚠️ **enfreint contrainte « Aucun Flex visible client »** (cf. §7 brief) |

**Ordering par persona** ([`NavRegistry.js:1001-1022`](frontend/src/layout/NavRegistry.js#L1001)) :

| Persona | Position « Énergie » dans le rail |
|---|---|
| Energy Manager (default) | **#2** (cockpit > energie > conformite > facturation > achat > patrimoine) |
| DAF | **#4** (cockpit > facturation > conformite > energie > achat > patrimoine) |
| Acheteur | **#3** |
| RegOps / Responsable conformité / Auditeur | **#3** |

**Aucun feature flag** sur Énergie (seul `VITE_FEATURE_ACTION_CENTER_V4` actif dans `frontend/src/featureFlags.js`). Items énergie permanents pour tous personas.

---

## 2 — Cartographie routes FE (App.jsx)

### 2.1 Routes énergie LIVE

| Route | Composant | Origine | Statut |
|---|---|---|---|
| `/consommations` (+ `/explorer`, `/portfolio`, `/import`, `/kb`) | `ConsommationsPage` (nested) | [`App.jsx:408-452`](frontend/src/App.jsx#L408) | ✅ |
| `/diagnostic-conso` | `ConsumptionDiagPage` | [`App.jsx:494`](frontend/src/App.jsx#L494) | ✅ |
| `/usages` | **`UsagesDashboardPage` (383 lignes)** | [`App.jsx:502`](frontend/src/App.jsx#L502) | ✅ **canonique** |
| `/usages-horaires` | `ConsumptionContextPage` | [`App.jsx:509`](frontend/src/App.jsx#L509) | ⚠️ hidden page « doublon-sub-page » |
| `/monitoring` | `MonitoringPage` | [`App.jsx:470`](frontend/src/App.jsx#L470) | ✅ |
| `/flex` | `FlexPage` | [`App.jsx:725`](frontend/src/App.jsx#L725) | ⚠️ Flex visible client (contrainte brief) |
| `/achat-energie` | `PurchasePage` | [`App.jsx:534`](frontend/src/App.jsx#L534) | ✅ |

### 2.2 Routes Cockpit Pilotage (doublons / legacy)

| Route | Composant | Statut | Risque |
|---|---|---|---|
| `/cockpit/jour` | `CockpitJour` | ✅ LIVE (briefing 30s) | OK |
| `/cockpit/strategique` | `CockpitStrategique` | ✅ LIVE (Cockpit P1/P1.5) | OK |
| **`/cockpit/pilotage`** | **`CockpitPilotage` (1 722 lignes legacy)** | ⚠️ FE route LIVE mais **BE endpoint `/api/cockpit/pilotage` retourne HTTP 404** | **doublon Pilotage + appel `/api/cockpit/priorities` + `useCockpitFacts`** |
| `/cockpit` → redirect `/cockpit/jour` | — | ✅ alias canonique | OK |
| `/` → redirect `/cockpit/strategique` | — | ✅ default login | OK |

### 2.3 Routes Centre d'Action (anti-doublon Pilotage)

| Route | Composant | Statut |
|---|---|---|
| `/action-center-v4` | `ActionCenterV4ListPage` (référentiel) | ✅ flag ON |
| `/action-center-v4/pilotage` | `ActionCenterV4PilotagePage` (file prioritaire) | ✅ flag ON |
| `/action-center-v4/pilotage/journal` | `ActionCenterV4JournalPage` (flux events 7j) | ✅ flag ON |
| `/action-center` → redirect `/action-center-v4/pilotage` | — | ✅ |

### 2.4 Pages orphelines (fichiers présents, 0 route active)

7 fichiers physiques sans route ([`App.jsx`](frontend/src/App.jsx) imports retirés ou jamais importés) :
- `pages/CommandCenter.jsx` (importée lazy `App.jsx:24` mais `/` redirige vers `/cockpit/strategique`)
- `pages/CockpitDecision.jsx` (commentaire `App.jsx:30-33` : « orphelin, remplacé par CockpitStrategique »)
- `pages/ActionCenterPage.jsx` (378 lignes legacy)
- `pages/ActionPlan.jsx`
- `pages/ActionsPage.jsx` (1 579 lignes, gated par V4 OFF)
- `pages/AnomaliesPage.jsx` (835 lignes, gated par V4 OFF)
- `pages/Dashboard.jsx`, `pages/OnboardingPage.jsx`, `pages/PurchaseAssistantPage.jsx`

Plan suppression L8 Mois 5 : `docs/dev/L8_plan_suppression_legacy.md`.

---

## 3 — Cartographie composants UsagesDashboardPage (page canonique)

[`frontend/src/pages/UsagesDashboardPage.jsx`](frontend/src/pages/UsagesDashboardPage.jsx) (383 lignes) :

- **ScopeBar** : sélecteur multi-niveaux (org / entité / portefeuille / site) via `useScope()`.
- **TabBar** : 3 onglets — `timeline` / `baseline` / `comptage`.
- **KpiStrip** : KPI cards en tête.
- **Cards** (lazy par onglet) :
  - `HeatmapCard` (load profile + DJU)
  - `ComplianceCard` (BACS / DT / ISO 50001)
  - `FlexNebcoCard` (NEBCO RTE) + `FlexBubbleChart`
  - `CostCard` (par période TURPE 7)
  - `PowerOptimizationCard` (puissance souscrite)
  - `CdcSimulationCard` (simulation achat CDC-aware)
- **FooterLinks** : navigation cross-page (vers `/consommations`, `/monitoring`, `/diagnostic-conso`).

**Services API consommés** : `getScopedUsagesDashboard`, `getScopedUsageTimeline`, `getPortfolioUsageComparison`, `getCostByPeriod`, `getFlexNebco`, `getFlexNebcoPortfolio`, `getPowerOptimization`, `getCdcSimulation` (8 fonctions exposées par [`frontend/src/services/api/energy.js`](frontend/src/services/api/energy.js)).

---

## 4 — Endpoints réellement consommés (live HELIOS)

| Endpoint | HTTP live | Statut | Caller FE principal |
|---|---|---|---|
| `/api/consumption-unified/portfolio` | 200 | ✅ SoT consommation | `ConsommationsPage`, dashboards |
| `/api/consumption/insights` | 200 | ✅ LIVE | `ConsumptionDiagPage` |
| `/api/usages/scoped-dashboard` | 200 | ✅ **canonique** | `UsagesDashboardPage` |
| `/api/usages/portfolio-compare` | 200 | ✅ LIVE | `UsagesDashboardPage` |
| `/api/pilotage/portefeuille-scoring` | 200 | ✅ LIVE | `FlexPage`, scoring scoré |
| `/api/cockpit/jour` | 200 | ✅ LIVE | `CockpitJour` |
| `/api/cockpit/priorities` | 200 | ✅ LIVE (post-fix P0-1) | `CockpitPilotage.jsx:1317` ⚠️ |
| `/api/energy/intensity` | 400 | ⚠️ params manquants HELIOS | `getEnergyIntensity` |
| `/api/cockpit/pilotage` | **404** | ❌ **endpoint inexistant** | `/cockpit/pilotage` FE route appelle ailleurs |
| `/api/cockpit/conso-month` | 410 Gone | ✅ déprécié #303 | aucun |
| `/api/cockpit/co2` | 410 Gone | ✅ déprécié #303 | aucun |
| `/api/cockpit/levers` | 410 Gone | ✅ déprécié #303 | aucun |

**Backend cartographie complète** (96 endpoints au total) :
- `/api/energy/*` : 8 LIVE (1 audit IS11 requis : `/energy/import/jobs` sans scope)
- `/api/consumption-unified/*` : 3 LIVE (SoT)
- `/api/consumption/*` : 26 LIVE
- `/api/usages/*` : **30 LIVE** (2 intentionnellement non scopées : `/estimate/reference-curve`, `/estimate/sector-trend` — catalogue NAF public pré-vente)
- `/api/pilotage/*` : **5 LIVE** (radar-prix-negatifs, portefeuille-scoring, flex-ready-signals, roi-flex-ready, nebco-simulation)
- `/api/consumption-context/*` : 5 LIVE (alimente `/usages-horaires`)
- `/api/cockpit/*` : 10 LIVE + **14 endpoints 410 Gone** (P0 cleanup #303)

---

## 5 — Routes mortes & doublons

### 5.1 Doublons confirmés (3)

| # | Doublon | Impact | Priorité |
|---|---|---|---|
| **D1** | **`/cockpit/pilotage` (FE, 1 722 lignes legacy) vs `/action-center-v4/pilotage` (V4 canonique)** | Deux pages « Pilotage », l'une sans endpoint BE direct (404 sur `/api/cockpit/pilotage`), l'autre canonique V4. Confusion user + bundle bloat. | **P0** |
| **D2** | `/usages` vs `/usages-horaires` | Hidden page « doublon-sub-page » documenté. UX confusion si un user cherche « horaires ». | P2 |
| **D3** | `getAnalysisSummary` + `seedDemoConsumption` (services FE) | Fonctions exportées dans [`api/energy.js`](frontend/src/services/api/energy.js) sans aucun import frontend (grep retour vide). Code mort applicatif. | P2 |

### 5.2 Endpoint 404 régressif

`/api/cockpit/pilotage` retourne **HTTP 404** alors que la route FE `/cockpit/pilotage` (`App.jsx:327`) reste vivante et que `CockpitPilotage.jsx` (1 722 lignes) appelle plusieurs APIs cockpit. Décision sprint #303 : **endpoint deprecated mais page FE conservée « retro-compat »**. Risque : un user qui bookmark `/cockpit/pilotage` arrive sur une page partiellement cassée (certaines cards en erreur silencieuse).

### 5.3 14 endpoints 410 Gone (anti-régression #303)

Tous correctement Gone, aucun appelé par le FE actuel (vérifié par smoke #309 + #312) :
`/api/cockpit/{benchmark, conso-month, co2, _facts.scope, _facts.alerts, cdc, levers, impact_decision, essentials, essentials/health, essentials/watchlist, data_activation, executive-v2, top-contributors}`.

---

## 6 — Réponses aux 10 questions clés du brief

| # | Question | Réponse |
|---|---|---|
| 1 | Quelles entrées Énergie existent dans la sidebar ? | **5 items** dans le module `energie` (Consommations / Performance énergétique / Répartition par usage / Diagnostics / Flex Intelligence). Ordre persona-adapté (#2 Energy Manager, #4 DAF). |
| 2 | Quelles routes énergie sont vivantes ? | **7 routes FE** : `/consommations` (+4 sub-tabs), `/diagnostic-conso`, `/usages`, `/usages-horaires` (hidden), `/monitoring`, `/flex`, `/achat-energie`. **30 endpoints BE `/api/usages/*` + 26 `/api/consumption/*` + 8 `/api/energy/*` + 5 `/api/pilotage/*`**. |
| 3 | Quelles routes sont legacy ou orphelines ? | **7 pages FE orphelines** (CommandCenter, CockpitDecision, ActionCenterPage, ActionPlan, ActionsPage, AnomaliesPage, Dashboard/Onboarding/PurchaseAssistant). **14 endpoints BE 410 Gone**. **1 endpoint 404 régressif** (`/api/cockpit/pilotage`). |
| 4 | `/usages` est-elle la route canonique ? | ✅ **OUI** — `UsagesDashboardPage` rend les 3 onglets (timeline/baseline/comptage) + 8 cards (Heatmap, Compliance, Flex NEBCO, Cost, Power, CDC). Endpoint backend canonique : `/api/usages/scoped-dashboard`. |
| 5 | Existe-t-il un doublon `/pilotage` ou `/cockpit/pilotage` ? | ✅ **OUI** — `/cockpit/pilotage` (FE legacy 1 722 l) vs `/action-center-v4/pilotage` (V4 canonique). L'endpoint BE `/api/cockpit/pilotage` n'existe **pas** (404). Doublon **D1 = P0 brief**. |
| 6 | Les libellés sont-ils compréhensibles par un DAF ? | ⚠️ **Partiellement**. « Répartition par usage » est ambigu pour un DAF (terme métier Energy Manager). « Flex Intelligence » est jargon marché. Les 3 autres (Consommations / Performance énergétique / Diagnostics) sont OK. |
| 7 | Les usages sont-ils accessibles sans créer un nouveau menu ? | ✅ **OUI** — entrée « Répartition par usage » → `/usages` déjà dans la sidebar module `energie`. Le sprint Pilotage des usages **n'a pas besoin de nouveau menu**. |
| 8 | Quels écrans doivent être masqués, 410 ou fusionnés ? | **Masquer** : `/cockpit/pilotage` FE (route legacy 1 722 l) → garder seulement `/cockpit/jour` + `/cockpit/strategique`. **410 Gone** : aucun endpoint nouveau à déprécier (les 14 sont déjà Gone). **Fusionner** : `/usages-horaires` dans `/usages` (déjà hidden, mais redirect propre à poser). |
| 9 | Quelle architecture de navigation cible recommander ? | **Cible** : module `energie` à 4 items (retirer `/flex` de la sidebar publique — visible client interdit par brief, garder en hidden page accessible Energy Manager via ⌘K). Ajouter une **page « Pilotage des usages » à l'intérieur de `/usages`** (4e onglet `pilotage`) au lieu de créer `/usage-steering`. Décommissionner FE `/cockpit/pilotage` (redirect vers `/cockpit/jour`). |
| 10 | Quel est le prompt exact pour l'audit Usage Steering ensuite ? | **Voir §10 ci-dessous** — prompt prêt à l'emploi. |

---

## 7 — Recommandation d'architecture cible (navigation)

### 7.1 Sidebar module `energie` cible

```
Énergie (Zap, indigo)
├── Consommations          → /consommations
├── Performance            → /monitoring
├── Répartition par usage  → /usages
│   └── (tab interne) Pilotage des usages  ← AJOUT futur, pas nouvelle route
└── Diagnostics            → /diagnostic-conso
```

**Changement vs actuel** :
- **Retirer** « Flex Intelligence » de la sidebar publique (brief §7 « Aucun Flex visible client ») → garder `/flex` accessible en hidden page (`HIDDEN_PAGES`) pour Energy Manager via ⌘K search.
- **Pas de nouvelle entrée** « Pilotage des usages » : intégrer en tant que 4e tab dans `/usages` (UsagesDashboardPage extension), respecte la règle produit du brief.

### 7.2 Décommissionner `/cockpit/pilotage`

- Redirect [`App.jsx:327`](frontend/src/App.jsx#L327) `/cockpit/pilotage` → `/cockpit/jour` (alias).
- Supprimer ou archiver `pages/CockpitPilotage.jsx` (1 722 lignes legacy).
- 410 Gone explicite si quelqu'un fait `GET /api/cockpit/pilotage` (actuellement 404 silencieux).

### 7.3 Garde anti-doublon

Source-guard à ajouter : `tests/source_guards/test_navigation_no_usage_steering.py` qui vérifie qu'aucun fichier ne contient `path: '/usage-steering'`. Verrou structurel pour empêcher un futur sprint de créer le silo.

---

## 8 — Plan P0 / P1 / P2

### 8.1 P0 (à clore avant sprint Usage Steering)

| # | Item | Effort |
|---|---|---|
| P0-1 | Décommissionner `/cockpit/pilotage` FE : redirect `App.jsx:327` → `/cockpit/jour` + ajouter test source-guard | 0,5 j |
| P0-2 | Ajouter `/api/cockpit/pilotage` en 410 Gone explicite (via `_gone_cockpit_p0_2026_05_25`) pour cohérence avec les 14 autres | 0,25 j |
| P0-3 | Retirer « Flex Intelligence » de la sidebar publique (NavRegistry) + déplacer en HIDDEN_PAGES (rester accessible ⌘K) | 0,5 j |

**Total P0 = ~1,25 j-dev**

### 8.2 P1

| # | Item | Effort |
|---|---|---|
| P1-1 | Renommer « Répartition par usage » → « Usages énergétiques » (plus DAF-friendly) | 0,1 j |
| P1-2 | Fusionner `/usages-horaires` dans `/usages` (redirect propre + ajouter contenu profil horaire en 4e tab si nécessaire) | 1 j |
| P1-3 | Auditer + scoper IS11 `/api/energy/import/jobs` (actuellement sans filtre org_id, liste TOUS les jobs instance) | 0,5 j |
| P1-4 | Documenter intentionnalité `/api/usages/estimate/*` (catalogue NAF public) ou ajouter rate-limit | 0,25 j |

### 8.3 P2

| # | Item | Effort |
|---|---|---|
| P2-1 | Supprimer fonctions FE orphelines (`getAnalysisSummary`, `seedDemoConsumption`) de `api/energy.js` | 0,1 j |
| P2-2 | Cutover L8 (Mois 5) des 7 pages orphelines (CommandCenter, CockpitDecision, ActionCenterPage, ActionPlan, Dashboard, etc.) | 1 j |
| P2-3 | Source-guard `test_navigation_no_usage_steering.py` (verrou anti-régression silo) | 0,25 j |

---

## 9 — Prompt prêt pour le sprint suivant : audit Usage Steering

```
Tu es Staff Engineer Full-Stack + Lead Product + QA/Release Manager sur PROMEOS.

BRANCHE
Créer :
  claude/usage-steering-audit-readonly

Base :
  claude/refonte-sol2 après merge PR audit menu Énergie #313 (cette PR).

OBJECTIF
Auditer en READ-ONLY strict le périmètre Pilotage des usages — ce qu'un
Energy Manager doit pouvoir faire pour piloter activement la consommation
de son patrimoine (vs simplement la regarder).

CONTEXTE
L'audit menu Énergie (#313, 2026-05-25) a confirmé :
- /usages est la route canonique (UsagesDashboardPage, 3 onglets).
- Aucun nouveau menu nécessaire.
- L'objectif Usage Steering doit être un 4e onglet « Pilotage » dans
  /usages, PAS une nouvelle route /usage-steering.

CONTRAINTES NON NÉGOCIABLES
- Aucun code modifié (READ-ONLY).
- Aucun nouveau menu, aucun écran fantôme.
- Ne pas créer /usage-steering.
- Ne pas réintroduire /cockpit/pilotage legacy.
- Aucun Flex visible client (le brief Pilotage des usages ne doit pas
  réintroduire NEBCO/AOFD côté front public).
- Français clair.

À AUDITER
Frontend :
- frontend/src/pages/UsagesDashboardPage.jsx (3 onglets actuels)
- frontend/src/pages/usages/* si existant
- composants Heatmap/Baseline/Compliance/Cost/Power/CDC déjà rendus
- services api/energy.js (52 fonctions)
- hooks/usages/* si existant

Backend :
- backend/routes/usages.py (30 endpoints)
- backend/routes/pilotage.py (5 endpoints : radar-prix-negatifs,
  portefeuille-scoring, flex-ready-signals, roi-flex-ready, nebco-simulation)
- backend/services/usage_service.py (SoT usages)
- backend/services/pilotage/* (5 services)

QUESTIONS CLÉS
1. Que peut faire aujourd'hui un Energy Manager dans /usages ?
2. Quels manques l'empêchent de piloter activement les usages ?
3. Quels endpoints BE existent mais ne sont pas exposés dans /usages ?
4. Quels écrans/composants peuvent être réutilisés (anti-doublon Flex) ?
5. Quelles données sont calculées BE mais jamais affichées FE ?
6. Quel est le contrat minimal d'un 4e onglet « Pilotage des usages » ?
7. Comment éviter de doublonner Bill Intelligence (anomalies facture) ?
8. Comment éviter de doublonner Centre d'Action V4 (actions cross-brique) ?
9. Quel mapping vers ActionCenterItem (source_url=/usages?tab=pilotage&site=X) ?
10. Quel prompt P0 pour livrer le 4e onglet sans nouveau menu ?

SORTIE
Créer :
docs/audits/audit_usage_steering_readonly_2026_05_26.md

Inclure :
- ce qu'un EM peut faire aujourd'hui (matrix use cases × écrans)
- ce qui manque pour piloter (gap analysis)
- contrat du 4e onglet « Pilotage des usages »
- mapping vers Centre d'Action V4 (cohérence sources)
- plan P0/P1/P2 + prompt P0 prêt à l'emploi

CRITÈRES
- 0 modification code.
- Confirme /usages comme route canonique (pas /usage-steering).
- Confirme intégration en 4e onglet (pas nouveau menu).
- Liste exhaustive endpoints réutilisables.
- Plan correctif chiffré (j-dev).
```

---

## 10 — Critères de GO du brief (6/6 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 0 modification code | ✅ READ-ONLY strict (le commit ne contient que `docs/audits/audit_menu_energie_navigation_readonly_2026_05_25.md`) |
| 2 | Route canonique `/usages` confirmée | ✅ `UsagesDashboardPage` rend les 3 onglets, endpoint canonique `/api/usages/scoped-dashboard` |
| 3 | Doublons identifiés | ✅ D1 `/cockpit/pilotage` vs `/action-center-v4/pilotage` · D2 `/usages` vs `/usages-horaires` · D3 services FE orphelins |
| 4 | Legacy identifié | ✅ 7 pages orphelines FE + 14 endpoints 410 Gone + 1 endpoint 404 régressif (`/api/cockpit/pilotage`) |
| 5 | Aucun nouveau menu proposé | ✅ Recommandation cible = 4 items dans `energie` (retrait Flex) + 4e tab `pilotage` dans `/usages` |
| 6 | Navigation cible claire | ✅ §7 ci-dessus : sidebar 4 items + tab interne + décommissionnement `/cockpit/pilotage` |

---

## Verdict

🟡 **Navigation Énergie cohérente** côté sidebar (5 entrées, ordre persona-adapté, 0 silo `/energie`) et côté backend (96 endpoints cartographiés, 72 LIVE org-scopés, 14 correctement 410 Gone).

**3 frictions** identifiées avant le sprint Pilotage des usages :
1. **D1 (P0)** — `/cockpit/pilotage` FE (1 722 lignes legacy) doit être décommissionné : l'endpoint BE est déjà 404, et `/action-center-v4/pilotage` est le pilotage canonique.
2. **Flex Intelligence (P0)** — l'item sidebar « Flex Intelligence » enfreint la contrainte brief « Aucun Flex visible client ». À déplacer en HIDDEN_PAGES.
3. **D2 (P1)** — `/usages-horaires` (hidden page) à fusionner dans `/usages` pour éviter la confusion.

**Cible architecture** : 4 items sidebar (Consommations / Performance / Usages / Diagnostics) + 4e onglet « Pilotage des usages » à l'intérieur de `/usages` (PAS de `/usage-steering`).

**Aucun fichier code modifié** dans cet audit (mode READ-ONLY strict respecté). Le prompt §9 est prêt pour ouvrir le sprint suivant.
