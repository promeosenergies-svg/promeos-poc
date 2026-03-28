# AUDIT COMPLET PROMEOS — 27 mars 2026

## Score global : 68 / 100

> Plateforme fonctionnellement riche et cohérente sur les briques coeur (billing, conformité, cockpit). Faiblesses principales : auth manquante sur ~95 endpoints POST/PUT/DELETE, org-scoping partiel (EMS, BACS, KB), et CO₂/IA encore en mode stub. La base de données (174 Mo, 132 tables, 42 modèles) et le volume de code (254k lignes) témoignent d'une construction rapide qui nécessite un cycle de consolidation.

---

## Métriques du codebase

| Métrique | Valeur |
|----------|--------|
| Fichiers source frontend | 314 (.jsx/.js) |
| Fichiers test frontend | 144 (783 test cases) |
| Lignes frontend | 86 721 |
| Fichiers Python backend | 627 |
| Fichiers test backend | 236 |
| Lignes backend | 167 643 |
| **Lignes totales** | **254 364** |
| Endpoints API | 536 |
| Modèles SQLAlchemy | 42 |
| Tables DB | 132 |
| Pages frontend | 47 |
| Composants | 62 |
| Hooks custom | 13 |
| DB size | 174 Mo |

---

## Scores par brique

| Brique | Complétude | Qualité | Cohérence | Prod-ready | Score |
|--------|:---------:|:-------:|:---------:|:----------:|:-----:|
| Patrimoine / Onboarding | 9/10 | 8/10 | 8/10 | 7/10 | **80** |
| RegOps / Conformité | 9/10 | 8/10 | 8/10 | 8/10 | **83** |
| Bill Intelligence | 9/10 | 7/10 | 7/10 | 7/10 | **75** |
| Achat Énergie | 8/10 | 7/10 | 8/10 | 6/10 | **73** |
| Market Data | 8/10 | 8/10 | 8/10 | 6/10 | **75** |
| EMS / Monitoring | 8/10 | 6/10 | 6/10 | 5/10 | **63** |
| Cockpit Exécutif | 9/10 | 7/10 | 8/10 | 7/10 | **78** |
| Actions / Alertes | 8/10 | 7/10 | 7/10 | 5/10 | **68** |
| Connecteurs externes | 5/10 | 6/10 | 5/10 | 4/10 | **50** |
| IA / Agents | 4/10 | 6/10 | 5/10 | 3/10 | **45** |

---

## Détail par brique

### 1. Patrimoine / Onboarding (80/100)

**Modèles** : Organisation → EntiteJuridique → Portefeuille → Site → Batiment + Meter/MeterReading. Chaîne hiérarchique complète, soft-delete sur tous les modèles.

**Endpoints** : 21 (patrimoine_crud) + 7 (sites) + 3 (onboarding) + 2 (import_sites) = **33 endpoints**.

**Points forts** :
- CRUD complet sur toute la chaîne org→site
- Import CSV multi-entité fonctionnel
- Site360 (1619 lignes) — vue détaillée riche
- PatrimoineWizard (1163 lignes) — assistant de création

**Points faibles** :
- `patrimoine_crud.py` : org-scoping via path param `{org_id}` mais pas de vérification que l'utilisateur a accès à cette org
- Aucun test dédié pour `patrimoine_crud.py`, `sites.py`, `import_sites.py`
- `Patrimoine.jsx` (2243 lignes) — candidat au split

### 2. RegOps / Conformité (83/100)

**Moteur** : compliance_engine.py (1249 l) + compliance_rules.py (774 l) + aper_service.py (251 l) + bacs_engine.py = **2274+ lignes** de logique métier.

**Tests** : **24 fichiers** dédiés (compliance + BACS + regops), ~6000 lignes de tests. **Meilleure couverture du projet.**

**Points forts** :
- DT jalons canoniques {2030: -40%, 2040: -50%, 2050: -60%} centralisés `cockpit.py:431`
- BACS : scoring, remédiation, exemptions, workflow complet
- CEE : dossier + étapes
- APER : service dédié
- ComplianceFinding → ActionItem : chaîne traçable

**Points faibles** :
- BACS : 29 endpoints, **0 org-scoping** — risque d'accès cross-tenant
- `tertiaire.py` : 31 endpoints, 11 refs org — scoping partiel
- Pas de test pour `tertiaire.py` (31 endpoints non testés)

### 3. Bill Intelligence (75/100)

**Moteur** : billing_engine/ (catalog 1261 l + engine 1057 l + turpe_calendar 355 l + seasonal_resolver 169 l) + billing_service.py (928 l) + billing_shadow_v2.py (575 l) = **6384 lignes**.

**Points forts** :
- 14+ règles d'anomalie (R1–R14)
- Shadow billing V2 avec TURPE 7 par segment (C5_BT, C4_BT, C3_HTA)
- Tarifs : tente `regulated_tariffs` DB d'abord, fallback constantes hardcodées
- Billing → ActionItem : pont automatique
- 109 tests dans `test_billing_engine.py` — la plus grande suite

**Points faibles** :
- Shadow V2 fallback hardcodé : `TURPE=0.0453`, `CSPE=0.02623`, `ATRD=0.025` — valeurs 2024, **pas à jour TURPE 7 (août 2025)**
- `billing.py` route : 1863 lignes — fichier le plus gros du backend, candidat split
- 4 endpoints POST sans auth : seed-demo, validate-canonical, perimeter/check, shadow-billing-check

### 4. Achat Énergie (73/100)

**Backend** : purchase.py (1265 l) + purchase_service.py (457 l) + purchase_pricing.py + seeds = **2373+ lignes**.

**Points forts** :
- Connexion market data via `MktPrice` (table mkt_prices) — pas de données mockées
- `get_reference_price()` depuis billing_service → prix de ref cohérent
- Stratégies : fixe, indexé, spot, hybride
- 43 tests dans `test_purchase.py`

**Points faibles** :
- Frontend : PurchasePage (2024 l) + PurchaseAssistantPage (1823 l) — **3847 lignes** de pages non splitées
- 3 endpoints POST seed sans auth
- `purchase_seed_wow.py` (480 l) — seed de démo, à exclure de la prod

### 5. Market Data (75/100)

**Tables** : mkt_prices, regulated_tariffs, price_signals, market_data_fetch_logs, price_decompositions — **5 tables**.

**Endpoints** : 14 (market.py + market_data.py) — spot, forwards, tarifs, décomposition, freshness.

**Points forts** :
- Architecture données complète (prix spot, forwards, tarifs réglementés, décomposition)
- Connecteur ENTSO-E existant (113 l)
- Connecteur RTE éCO₂mix existant (69 l)
- Endpoint `/tariffs/reload` pour mise à jour

**Points faibles** :
- Connecteurs non activés en production (pas de cron/scheduler)
- 0 org-scoping (données marché = globales, OK pour l'instant)
- 0 tests dédiés

### 6. EMS / Monitoring (63/100)

**Endpoints** : 35 (ems) + 11 (monitoring) + 36 (consumption_*) = **82 endpoints** — le plus gros module.

**Frontend** : MonitoringPage (3112 l) — **fichier le plus volumineux du projet**. ConsommationsUsages (1240 l), ConsumptionExplorerPage (979 l), ConsumptionPortfolioPage (978 l).

**Points forts** :
- Timeseries + signatures énergétiques
- Views/Collections EMS personnalisables
- ConsumptionDiag complet (940 l backend)

**Points faibles** :
- **0 org-scoping** sur EMS (24 endpoints) et monitoring (11 endpoints) — **CRITIQUE**
- MonitoringPage.jsx (3112 l) — ingérable, doit être splitté
- 11 endpoints POST EMS sans auth (views, collections, demo/generate, demo/purge)
- Aucun test pour `ems.py`, `monitoring.py`, `consumption_diagnostic.py`

### 7. Cockpit Exécutif (78/100)

**Composants** : 23 composants cockpit dédiés — architecture bien découpée.

**Hooks** : useCockpitData (204 l), useCockpitSignals (71 l), useCommandCenterData (167 l).

**Backend** : 7 endpoints cockpit — tous avec org-scoping (27 refs).

**Points forts** :
- Architecture composants exemplaire (23 fichiers dédiés)
- Cockpit.jsx (1070 l) orchestre bien les sous-composants
- Signaux header (EPEX, CO₂, alertes) — maintenant connectés (fix ce sprint)
- Trajectory section avec jalons DT
- Rapport COMEX print

**Points faibles** :
- CO₂ badge : affiche le facteur ADEME statique (52 g/kWh), pas le CO₂ réseau temps réel
- Pas de test dédié pour cockpit.py

### 8. Actions / Alertes (68/100)

**Backend** : actions.py (1317 l) + action_center.py (590 l) + action_plan_engine.py (182 l) = **2089 lignes**.

**Sources** : BILLING, COMPLIANCE, MANUAL, INSIGHT — 4 sources confirmées en code.

**Points forts** :
- Modèle ActionItem riche (source_type, priority, status, evidence)
- action_center : bulk operations, override-priority, reopen
- Pont Billing→Actions et Compliance→Actions automatiques

**Points faibles** :
- **8 endpoints POST action_center sans auth** — bulk assign, update-due-date, update-status
- **0 org-scoping** sur action_center (8 refs sur 38 endpoints — insuffisant)
- Aucun test pour action_center.py, action_templates.py
- ActionDetailDrawer.jsx (1327 l) — monolithique

### 9. Connecteurs externes (50/100)

**Connecteurs** :
| Connecteur | Lignes | Stub |
|------------|--------|------|
| entsoe_connector | 113 | Non |
| rte_eco2mix | 69 | Non |
| contracts | 92 | Non |
| pvgis | 77 | Non |
| enedis_dataconnect | 26 | Non |
| enedis_opendata | 18 | Non |
| meteofrance | 26 | Non |

**Points forts** :
- 7 connecteurs avec code réel (pas de stub)
- Architecture `Connector` base class propre

**Points faibles** :
- Connecteurs minimalistes (18–113 lignes) — fetch basique sans retry, pagination, rate-limiting
- Enedis DataConnect (26 l) — squelette, pas de OAuth complet
- MétéoFrance (26 l) — squelette
- Aucun scheduler/cron pour les appels automatiques
- 4 endpoints sans auth (test, sync)
- Aucun test

### 10. IA / Agents (45/100)

**Architecture** : `ai_layer/` avec client.py, registry.py, 5 agents spécialisés.

**Agents** :
- data_quality_agent
- exec_brief_agent
- regops_explainer
- regops_recommender
- reg_change_agent

**Points forts** :
- Architecture propre (client + registry + agents)
- Fallback stub automatique quand AI_API_KEY absent
- Modèle AiInsight en DB pour persister les résultats

**Points faibles** :
- **Mode stub par défaut** — sans API_KEY, tout retourne un placeholder
- 5 endpoints (ai_route) avec seulement 2 refs org-scoping
- Aucun test dédié
- Pas de retry/circuit-breaker sur les appels Claude API

---

## Fichiers volumineux (> 1000 lignes)

### Frontend (19 fichiers > 1000 lignes)
| Fichier | Lignes | Risque |
|---------|--------|--------|
| MonitoringPage.jsx | 3112 | **CRITIQUE** — split obligatoire |
| Patrimoine.jsx | 2243 | Élevé |
| PurchasePage.jsx | 2024 | Élevé |
| PurchaseAssistantPage.jsx | 1823 | Élevé |
| Site360.jsx | 1619 | Modéré |
| ActionsPage.jsx | 1579 | Élevé |
| ActionDetailDrawer.jsx | 1327 | Modéré |
| BillIntelPage.jsx | 1246 | Modéré |
| ConsommationsUsages.jsx | 1240 | Modéré |
| UsagesDashboardPage.jsx | 1203 | Modéré |
| ConsumptionDiagPage.jsx | 1173 | Modéré |
| PatrimoineWizard.jsx | 1163 | Modéré |
| ObligationsTab.jsx | 1155 | Modéré |
| TertiaireEfaDetailPage.jsx | 1099 | Modéré |
| Cockpit.jsx | 1070 | Modéré |
| SiteCreationWizard.jsx | 1040 | Modéré |

### Backend (10 fichiers > 1000 lignes)
| Fichier | Lignes |
|---------|--------|
| billing.py (routes) | 1863 |
| migrations.py | 1621 |
| patrimoine_service.py | 1429 |
| actions.py (routes) | 1317 |
| seed_data.py | 1308 |
| purchase.py (routes) | 1265 |
| billing_engine/catalog.py | 1261 |
| compliance_engine.py | 1249 |
| gen_readings.py | 1219 |
| ems.py (routes) | 1208 |

---

## Fichiers morts / orphelins

### Pages non importées dans App.jsx
- `ActionPlan` — pas importé (code mort ou route manquante)
- `LoginBackground` — composant décoratif non référencé

### Composants non importés
- `AnomalyActionModal` — 0 imports
- `DemoBanner` — 0 imports
- `MeterBreakdownChart` — 0 imports
- `PerformanceSnapshot` — 0 imports
- `SitePicker` — 0 imports

> **5 composants et 2 pages potentiellement morts** — à vérifier et supprimer si confirmé.

---

## Sécurité

### Auth manquante — **~95 endpoints POST/PUT/DELETE sans auth**

Modules les plus exposés :
| Module | Endpoints sans auth | Gravité |
|--------|:------------------:|---------|
| BACS | 16 | **CRITIQUE** — données conformité |
| Tertiaire | 14 | **CRITIQUE** — données réglementaires |
| EMS | 10 | Élevé — vues, collections, démo |
| Action Center | 8 | Élevé — bulk ops, override priority |
| Actions | 5 | Élevé — patch, comments, evidence |
| Admin Users | 5 | **CRITIQUE** — CRUD utilisateurs |
| Intake | 6 | Modéré |
| Demo/DevTools | 7 | Faible (outils démo) |

> **Note** : En `DEMO_MODE=true` le middleware auth est permissif. Mais ces endpoints n'ont même pas le `Depends(get_optional_auth)` — ils seraient ouverts même en mode production.

### Org-scoping lacunaire

Modules avec **0 org-scoping** :
- `ems` (24 endpoints)
- `monitoring` (11 endpoints)
- `bacs` (29 endpoints)
- `kb_usages` (13 endpoints)
- `usages` (10 endpoints)
- `site_config` (4 endpoints)
- `compteurs` (3 endpoints)
- `connectors_route` (4 endpoints)
- `energy` (7 endpoints)
- `guidance` (2 endpoints)
- `intake` (8 endpoints)

> **115 endpoints sans aucune notion d'org-scope** — en multi-tenant, un utilisateur pourrait accéder aux données d'une autre organisation.

### JWT
- Secret par défaut : `dev-secret-change-me-in-prod` — **warning en production** (code existant ligne 39)
- Expiration : 30 min — OK
- CORS : `["*"]` en DEMO_MODE — acceptable pour démo

---

## Couverture tests

### Backend : 236 fichiers, top modules
| Fichier test | Tests |
|-------------|:-----:|
| test_billing_engine | 109 |
| test_invariants | 87 |
| test_turpe_calendar | 74 |
| test_iam | 61 |
| test_import_mapping | 53 |
| test_consumption_v10 | 51 |
| test_compliance_engine | 49 |
| test_billing | 41 |
| test_purchase | 43 |
| test_onboarding | 43 |

### 26 modules de routes sans aucun test dédié
`action_center`, `action_templates`, `admin_users`, `ai_route`, `alertes`, `aper`, `auth`, `compteurs`, `connectors_route`, `consommations`, `consumption_diagnostic`, `contracts_radar`, `copilot`, `dashboard_2min`, `dev_tools`, `energy`, `geocoding`, `import_sites`, `onboarding_stepper`, `patrimoine_crud`, `referentiel`, `site_config`, `sites`, `tertiaire`, `usages`, `watchers_route`

### Frontend : 144 fichiers, 783 test cases
- Couverture correcte sur les composants cockpit et domaine
- Manque de tests E2E sur les parcours critiques (onboarding, billing workflow)

---

## Constantes canoniques

### CO₂
- **Source unique** : `config/emission_factors.py` — ADEME Base Empreinte V23.6
- Élec : **0.052 kgCO₂eq/kWh** — confirmé ×3 sources
- Gaz : **0.227 kgCO₂eq/kWh**
- Réseau chaleur : 0.110, Fioul : 0.324
- ✅ Aucune duplication détectée

### DT Jalons
- Source unique : `cockpit.py:431` — `{2030: -0.40, 2040: -0.50, 2050: -0.60}`
- ✅ Cohérent partout

### TURPE / Shadow billing
- Shadow V2 tente d'abord `regulated_tariffs` DB
- Fallback hardcodé : TURPE C5_BT=0.0453, CSPE=0.02623, ATRD=0.025
- ⚠️ Valeurs pré-TURPE 7 — à mettre à jour avec les tarifs août 2025

---

## Lazy loading frontend
- **48 pages lazy-loaded** sur 47 pages → ✅ couverture totale
- **86 suppressions eslint** (`eslint-disable`) — à auditer pour faux positifs

---

## Top 10 items P0 (bloquants démo/pilote)

| # | Fichier | Problème | Correction | Effort |
|---|---------|----------|------------|--------|
| 1 | `routes/admin_users.py:141-312` | 5 endpoints CRUD users sans auth — création/suppression user ouverts | Ajouter `Depends(get_current_user)` + vérification rôle admin | 1h |
| 2 | `routes/bacs.py` (16 endpoints) | Aucun auth ni org-scoping — données conformité BACS exposées cross-tenant | Ajouter auth + filtrage par org_id sur tous les endpoints | 3h |
| 3 | `routes/action_center.py:566-584` | Bulk assign/update sans auth — un anonyme peut modifier des actions en masse | Ajouter `Depends(get_optional_auth)` | 1h |
| 4 | `routes/ems.py` (24 endpoints) | 0 org-scoping — timeseries de tous les sites accessibles | Filtrer par org_id via resolve_org_id | 4h |
| 5 | `routes/tertiaire.py` (14 POST sans auth) | Création/suppression EFA, buildings, events sans auth | Ajouter auth middleware | 2h |
| 6 | `services/billing_shadow_v2.py:32-35` | Fallback TURPE=0.0453 — taux pré-TURPE 7 (devrait être ~0.048+ depuis août 2025) | Mettre à jour les constantes fallback ou forcer DB | 1h |
| 7 | `hooks/useCockpitSignals.js:42` | ~~CO₂ hardcodé null~~ → **CORRIGÉ** ce sprint (branché sur /cockpit/co2) | ✅ Fait | — |
| 8 | `routes/monitoring.py` (11 endpoints) | 0 org-scoping — alertes monitoring cross-tenant | Ajouter filtrage org | 2h |
| 9 | `routes/dev_tools.py:26` | POST `/reset_db` sans auth — **destruction totale de la DB** en un appel | Restreindre à DEMO_MODE + auth admin, ou retirer en prod | 30min |
| 10 | `routes/intake.py` (6 POST sans auth) | Answers, apply-suggestions, complete — modification données site sans auth | Ajouter auth | 1h |

---

## Top 10 items P1 (crédibilité)

| # | Fichier | Problème | Correction | Effort |
|---|---------|----------|------------|--------|
| 1 | `MonitoringPage.jsx` | 3112 lignes — ingérable, perf dégradée | Splitter en 5+ sous-composants (timeseries, alertes, signatures, co2, demo) | 4h |
| 2 | `billing.py` (routes) | 1863 lignes — plus gros fichier route backend | Extraire seed-demo, shadow-billing, canonical validation en sous-modules | 3h |
| 3 | 5 composants morts | AnomalyActionModal, DemoBanner, MeterBreakdownChart, PerformanceSnapshot, SitePicker | Supprimer ou ré-intégrer | 1h |
| 4 | 26 modules routes sans test | auth, patrimoine_crud, sites, tertiaire, admin_users, etc. | Créer smoke tests (status 200 + schema) | 8h |
| 5 | `Patrimoine.jsx` | 2243 lignes | Extraire tableau, filtres, carte en composants | 3h |
| 6 | `PurchasePage.jsx` + `PurchaseAssistantPage.jsx` | 3847 lignes combinées | Extraire les sections en composants dédiés | 4h |
| 7 | 86 eslint-disable | Potentiels bugs masqués | Auditer et corriger les root causes | 3h |
| 8 | `kb_usages.py` (13 endpoints, 0 org-scope) | Base de connaissance usages accessible cross-tenant | Ajouter org-scoping | 2h |
| 9 | Connecteur Enedis DataConnect | 26 lignes squelette — pas d'OAuth | Implémenter le flux OAuth2 Enedis complet | 8h |
| 10 | `ActionsPage.jsx` | 1579 lignes | Extraire filtres, table, drawer | 3h |

---

## Top 10 items P2 (best-in-class)

| # | Thème | Description | Effort |
|---|-------|-------------|--------|
| 1 | CO₂ temps réel | Activer RTEEco2MixConnector avec cron → CO₂ réseau instantané dans le badge cockpit | 4h |
| 2 | IA live | Configurer AI_API_KEY + tester les 5 agents avec Claude API | 2h |
| 3 | Connecteur MétéoFrance | Enrichir avec DJU pour normalisation conso (compliance DT) | 4h |
| 4 | ENTSO-E cron | Scheduler pour import automatique des prix spot jour J | 3h |
| 5 | PDF export natif | Rapport COMEX → PDF généré (pas window.print) avec graphiques vectoriels | 8h |
| 6 | Rate limiting API | Protéger les endpoints publics (login, seed, reset) | 2h |
| 7 | Audit trail | Logger toutes les mutations (create/update/delete) avec user_id + timestamp | 4h |
| 8 | Websocket alertes | Push notifications temps réel au lieu de polling | 6h |
| 9 | Multi-langue | i18n framework (react-intl) pour les labels front | 8h |
| 10 | Dashboard perf | Métriques backend (response time p95, DB query time) exposées dans /monitoring | 4h |

---

## Architecture — recommandations structurelles

### 1. Auth middleware global
Au lieu d'ajouter `Depends(get_optional_auth)` endpoint par endpoint, configurer un **middleware global** qui injecte l'auth context sur toutes les routes sauf whitelist (`/login`, `/health`, `/docs`). Cela élimine d'un coup les ~95 endpoints sans auth.

### 2. Org-scoping centralisé
Créer un `OrgScopedSession` (dependency injection) qui filtre automatiquement toutes les queries par `org_id` résolu depuis le JWT. Implémentation inspirée de SQLAlchemy `Session.info` + `@event.listens_for`.

### 3. Split fichiers > 1500 lignes
Règle : aucun fichier > 800 lignes. Les 16 fichiers frontend et 10 fichiers backend > 1000 lignes sont des dettes techniques accumulées. Prioriser MonitoringPage (3112), Patrimoine (2243), billing.py (1863).

### 4. Connecteurs — architecture scheduler
Ajouter un scheduler (APScheduler ou Celery Beat) pour déclencher les connecteurs (ENTSO-E, RTE, Enedis) sur cron. Actuellement tout est manuel.

### 5. Tests — couverture minimale
Objectif : 1 smoke test par endpoint route (status code + schema). Les 26 modules sans test représentent ~200 endpoints non validés.

---

## Feuille de route recommandée (4 sprints)

### Sprint V111 — Sécurité & Auth (1 semaine)
- [ ] Middleware auth global (whitelist login/health/docs)
- [ ] Fix P0 #1 (admin_users), #3 (action_center bulk), #5 (tertiaire), #9 (dev_tools), #10 (intake)
- [ ] Org-scoping EMS (#4), BACS (#2), monitoring (#8)
- [ ] Mettre à jour constantes TURPE 7 shadow billing (#6)

### Sprint V112 — Qualité & Refactoring (1 semaine)
- [ ] Split MonitoringPage.jsx → 5 sous-composants
- [ ] Split billing.py routes → 3 sous-modules
- [ ] Supprimer 5 composants morts + 2 pages orphelines
- [ ] Auditer 86 eslint-disable
- [ ] Split Patrimoine.jsx, PurchasePage.jsx

### Sprint V113 — Tests & Robustesse (1 semaine)
- [ ] Smoke tests pour les 26 modules sans test (200+ endpoints)
- [ ] Tests E2E Playwright : parcours onboarding → billing → actions
- [ ] Tests org-scoping : vérifier isolation cross-tenant
- [ ] CI : ajouter coverage report avec seuil minimum

### Sprint V114 — Connecteurs & IA (1 semaine)
- [ ] Activer connecteur RTE éCO₂mix → CO₂ temps réel cockpit
- [ ] Scheduler APScheduler pour ENTSO-E + RTE (cron quotidien)
- [ ] Configurer AI_API_KEY → tester 5 agents live
- [ ] Enrichir connecteur Enedis DataConnect (OAuth)
- [ ] Connecteur MétéoFrance → DJU pour normalisation

---

## Annexes

### Routes API par module (536 endpoints)

| Module | GET | POST/PUT/PATCH/DELETE | Total |
|--------|:---:|:--------------------:|:-----:|
| action_center | — | 38 | 38 |
| tertiaire | — | 31 | 31 |
| bacs | — | 29 | 29 |
| billing | — | 28 | 28 |
| ems | — | 24 | 24 |
| compliance | — | 23 | 23 |
| consumption_diagnostic | — | 23 | 23 |
| purchase | — | 22 | 22 |
| patrimoine_crud | — | 21 | 21 |
| actions | — | 20 | 20 |
| *Autres (45 modules)* | — | — | *257* |

### Couverture tests backend (top 10)

| Suite | Tests |
|-------|:-----:|
| billing_engine | 109 |
| invariants | 87 |
| turpe_calendar | 74 |
| iam | 61 |
| import_mapping | 53 |
| consumption_v10 | 51 |
| compliance_engine | 49 |
| step8_billing_5sites | 44 |
| purchase | 43 |
| onboarding | 43 |
