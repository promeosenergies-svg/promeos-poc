# RAPPORT D'AUDIT GLOBAL PROMEOS
## Date : 2026-04-03
## Baseline : 3780 tests FE (3 fails) + BE (1 fail sur test_cdc_contract_simulator)

---

## EXECUTIVE SUMMARY
- Pages auditées : 27+ routes principales
- **P0 (bloquants) : 6**
- **P1 (crédibilité) : 11**
- **P2 (polish) : 9**
- Score global : **5.5/10**

Le POC est fonctionnel et la majorité des pages chargent avec des données. Les problèmes critiques sont concentrés sur la **cohérence cross-module des KPIs compliance** et quelques **endpoints manquants ou incohérents**.

---

## P0 — BLOQUANTS (à corriger AVANT toute démo)

### P0-1 : Incohérence compliance tri-endpoint (3 vérités différentes)
- **Endpoints** :
  - `GET /api/compliance/summary` → sites_ok=0, sites_nok=2, sites_unknown=3, pct_ok=0%
  - `GET /api/compliance/portfolio/summary` → sites_blocked=0, sites_warning=0, sites_ok=5
  - `GET /api/cockpit` → compliance_score=57.2, sites_tertiaire_ko=3, sites_bacs_ko=5
- **Impact** : Un décideur voit 0% conforme sur une page et 100% ok sur une autre. Destruction immédiate de crédibilité.
- **Cause racine** :
  - `compliance/summary` utilise findings OK/NOK/UNKNOWN par réglementation (compliance_rules.py)
  - `compliance/portfolio/summary` utilise readiness gate BLOCKED/WARNING/OK (data completeness) via compliance_readiness_service.py
  - cockpit utilise RegAssessment score composite (cockpit.py:101-103)
- **Fichiers** :
  - `backend/services/compliance_readiness_service.py:491-509` (portfolio KPIs basés sur gate_status)
  - `backend/services/compliance_rules.py` (get_summary → findings-based)
  - `backend/routes/cockpit.py:98-103` (compliance_score_unified)
- **Fix** : Unifier la sémantique. Le `portfolio/summary` devrait utiliser les mêmes findings que `/summary`, pas juste la data readiness. Renommer les champs pour éviter la confusion (`gate_sites_ok` vs `compliance_sites_ok`).

### P0-2 : Divergence conso Cockpit vs Patrimoine (182k kWh, 6.2%)
- **Constat** :
  - Patrimoine (déclaré) : 2,947,000 kWh = 2,947 MWh (somme `conso_kwh_an` des 5 sites)
  - Cockpit (mesuré) : 2,765,196 kWh = 2,765 MWh (via `get_portfolio_consumption`, metered data 365j)
  - Delta : **181,804 kWh (6.2%)**
- **Impact** : Deux pages du même outil affichent des totaux conso différents. En démo, le client demandera pourquoi.
- **Fichiers** :
  - `backend/routes/cockpit.py:139-140` (utilise `get_portfolio_consumption`)
  - `backend/routes/patrimoine/_helpers.py:264` (utilise `site.annual_kwh_total` = valeur déclarée)
- **Fix** : Afficher la source ("mesuré" vs "déclaré") en label, ou unifier sur la même source. A minima, tooltip expliquant la source.

### P0-3 : KPI details labels manquants dans cockpit
- **Constat** : `GET /api/cockpit` retourne `kpi_details` avec label="?" pour les 3 KPIs
- **Impact** : Le frontend reçoit des labels "?" au lieu de noms lisibles
- **Fichier** : `backend/routes/cockpit.py:172-176` (appel `wrap_kpi_runtime`)
- **Fix** : Passer le label correct dans `wrap_kpi_runtime` : "Score conformité", "Risque financier", "Complétude données"

### P0-4 : 3 tests frontend en échec (garde-fous cassés)
- **Tests** :
  1. `actionsConsoleV1.test.js` — Cockpit.jsx contient `navigate('/actions')` hardcodé (lignes 509, 521) alors que le test exige zéro URL hardcodée
  2. `site360CockpitWC.test.js` — attend `getBenchmark(site.usage)` dans le source (le pattern a changé)
  3. `DemoJourneyGuard.test.js` — Cockpit.jsx contient "EUR" en commentaire (ligne 172: `// 45 EUR/MWh`)
- **Fichiers** :
  - `frontend/src/pages/Cockpit.jsx:172,509,521`
  - `frontend/src/pages/Site360.jsx:84,1541`
- **Fix** : 
  - Cockpit: remplacer `navigate('/actions')` par navigate via constante ; supprimer "EUR" du commentaire
  - Site360: aligner le pattern getBenchmark avec ce que le test vérifie

### P0-5 : get_co2 appelle get_optional_auth comme fonction au lieu de dependency injection
- **Fichier** : `backend/routes/cockpit.py:593-612`
- **Constat** : `get_optional_auth(request)` est appelé comme fonction normale, pas comme `Depends()`. Cela bypass le DI FastAPI — `token` reçoit l'objet Request, `db` est manquant → TypeError silencieux, `auth` reste None
- **Impact** : En mode non-demo, l'endpoint `/cockpit/co2` résout le mauvais org_id ou expose des données cross-tenant
- **Fix** : Ajouter `auth: Optional[AuthContext] = Depends(get_optional_auth)` dans la signature de la fonction

### P0-6 : Sites soft-deleted inclus dans compliance portfolio
- **Fichier** : `backend/services/compliance_readiness_service.py:451-458`
- **Constat** : `compute_portfolio_compliance_summary` construit `site_ids` sans filtre `deleted_at IS NULL` ni `not_deleted()`. Les sites supprimés sont comptés dans `sites_ok/sites_blocked`
- **Impact** : Totaux compliance gonflés, faussant le dashboard et les KPIs portfolio
- **Fix** : Ajouter `not_deleted()` sur la query site_ids (comme le font les autres services)

---

## P1 — CRÉDIBILITÉ (à corriger dans la semaine)

### P1-1 : Flex score site 1 "non trouvé" (404)
- **Endpoint** : `GET /api/flex/score/sites/1` → `{"code":"NOT_FOUND","message":"Site 1 non trouve"}`
- **Impact** : L'onglet Puissance ou Flex dans Site360 pourrait être vide
- **Fichier** : `backend/routes/flex_score.py`
- **Fix** : Le service flex_score cherche le site dans une table différente ou avec un filtre org. Vérifier la query dans le service.

### P1-2 : Backend test fail — test_cdc_contract_simulator
- **Test** : `tests/test_cdc_contract_simulator.py::test_returns_4_strategies` — SQLAlchemy error
- **Impact** : Stratégies d'achat potentiellement cassées
- **Fix** : Corriger le test ou le service sous-jacent

### P1-3 : 578 endpoints backend, seulement 43 avec response_model Pydantic
- **Constat** : 92.6% des endpoints n'ont pas de validation de réponse
- **Impact** : Risque de réponses incohérentes, pas de documentation OpenAPI complète
- **Fichiers** : Tous les fichiers dans `backend/routes/` — les plus critiques sans validation :
  - cockpit.py (0 response_model)
  - compliance.py (0 response_model)
  - monitoring.py (0 response_model)
- **Fix** : Ajouter response_model au minimum sur les endpoints cockpit et compliance

### P1-4 : 8 CTAs orphelins (navigate vers routes inexistantes)
- **CTAs pointant vers des routes non déclarées dans App.jsx** :
  - `/achat` (devrait être `/achat-energie`)
  - `/bill-intel?filter=anomalies` (le query param n'est pas géré)
  - `/conformite?tab=donnees` et `/conformite?tab=execution`
  - `/consommations/import` et `/consommations/kb`
  - `/consommations?filter=energivores`
  - `/patrimoine?filter=risque`
- **Impact** : Cliquer sur ces boutons mène vers une page sans le filtre attendu ou vers un 404
- **Fix** : Corriger les targets dans les composants sources, ou ajouter la gestion des query params

### P1-5 : Site360 manque l'onglet "Usages"
- **Constat** : `TABS` déclare 7 onglets (resume, conso, factures, reconciliation, conformite, actions, puissance) mais pas "usages"
- **Impact** : Les usages par bâtiment ne sont pas accessibles depuis la fiche site
- **Fichier** : `frontend/src/pages/Site360.jsx:102-110`
- **Fix** : Ajouter `{ id: 'usages', label: 'Usages' }` et le composant correspondant

### P1-6 : Filtre portfolio par modulo ID au lieu de portefeuille_id
- **Fichier** : `frontend/src/pages/Cockpit.jsx:265,287`
- **Constat** : `scopedSites.filter((s) => ((s.id - 1) % 5) + 1 === pf.id)` — filtre les sites par arithmétique modulo au lieu de `s.portefeuille_id === pf.id`
- **Impact** : Avec des IDs non séquentiels (suppressions, imports), les onglets portfolio affichent les mauvais sites
- **Fix** : Remplacer par `s.portefeuille_id === pf.id`

### P1-7 : Conversion EUR→kWh avec constante magique 0.068
- **Fichier** : `backend/routes/cockpit.py:497`
- **Constat** : `_savings_kwh = sum(...estimated_gain_eur...) / 0.068` — divise des euros par un prix fixe de 6.8 c€/kWh pour obtenir des kWh
- **Impact** : Projection trajectoire kWh fausse si le prix contractuel diffère de 6.8 c€/kWh
- **Fix** : Utiliser `estimated_gain_kwh` si disponible, ou le prix contractuel du site

### P1-8 : Invoice coverage sous-estime les factures multi-mois
- **Fichier** : `backend/services/consumption_unified_service.py:109-118`
- **Constat** : `months_with_invoices` compte uniquement `period_start` — une facture nov→déc ne compte que novembre
- **Impact** : `billed_coverage` systématiquement sous-estimé → le service préfère "metered" même quand les factures couvrent la période. Contribue à la divergence conso cockpit vs patrimoine
- **Fix** : Compter les mois entre `period_start` et `period_end`

### P1-9 : func.strftime SQLite-only dans consumption_unified_service
- **Fichier** : `backend/services/consumption_unified_service.py:111`
- **Constat** : `func.strftime("%Y-%m", ...)` est spécifique SQLite — cassera si migration PostgreSQL
- **Impact** : Bloquant pour le passage à PostgreSQL (prévu docker-compose)
- **Fix** : Utiliser `extract` ou `func.date_trunc` portable

### P1-10 : datetime.utcnow() deprecated (Python 3.12+)
- **Constat** : `compliance_rules.py:759` utilise `datetime.utcnow()` qui est deprecated
- **Impact** : Warning en production, suppression future dans Python 3.14
- **Fix** : Remplacer par `datetime.now(datetime.UTC)`

### P1-11 : 18 pages sans ScopeContext (scope switcher ignoré)
- **Pages métier sans scope** : ActionCenterPage, ActionPlan, AdminAssignmentsPage, AdminAuditLogPage, AperPage, CompliancePage, CompliancePipelinePage, ConnectorsPage, ConsommationsPage, KBExplorerPage, PaymentRulesPage, PortfolioReconciliationPage, RegOps, SegmentationPage, SiteCompliancePage, WatchersPage
- **Pages admin sans scope** (acceptable) : AdminRolesPage, AdminUsersPage
- **Pages légitimement sans scope** : LoginPage, NotFound, StatusPage
- **Impact** : Changer d'org/site dans le scope switcher ne filtre pas les données sur **16 pages métier**
- **Fix** : Ajouter `useScope()` et filtrer les données par org_id sur les 16 pages métier

---

## P2 — POLISH (backlog priorisé)

### P2-1 : 19 console.log résiduels dans le frontend
- **Répartition** : 11 fichiers (logger.js, tracker.js, core.js, SitesMap, ActionCenterPage, etc.)
- **Fix** : Remplacer par le logger centralisé ou supprimer

### P2-2 : ~11 TODO/FIXME dans le code
- **Notables** :
  - `backend/services/kb_service.py:105,220` — "TODO: Extract if available"
  - `backend/services/tertiaire_proof_catalog.py:11` — "TODO vérification réglementaire"
  - `backend/models/market_models.py:14` — "TODO: DROP TABLE market_prices"
- **Fix** : Trier et résoudre ou convertir en issues GitHub

### P2-3 : "Données mensuelles à venir" dans CommandCenter
- **Fichier** : `frontend/src/pages/CommandCenter.jsx:408`
- **Impact** : Texte placeholder visible en démo
- **Fix** : Afficher les données réelles ou masquer la section

### P2-4 : Bundle maplibre > 1 MB (warning Vite)
- **Constat** : `maplibre-BXynEkEX.js` = 1,023 kB (gzip: 277 kB)
- **Impact** : Performance premier chargement
- **Fix** : Lazy import de la carte (`React.lazy()`)

### P2-5 : N+1 queries dans cockpit_v2 `_compute_data_briques`
- **Fichier** : `backend/routes/cockpit_v2.py:304-376`
- **Constat** : 3 queries SQL par site dans une boucle (EnergyContract, EnergyInvoice, Meter) → 3N+1 queries pour N sites
- **Impact** : Performance dégradée avec >10 sites (30+ queries au lieu de 3)
- **Fix** : Hoist les queries hors de la boucle avec `.filter(Model.site_id.in_(site_ids))`

### P2-6 : ConformitePage fetch intake questions pour un seul site
- **Fichier** : `frontend/src/pages/ConformitePage.jsx:192-197`
- **Constat** : `getIntakeQuestions(scopedSites[0].id)` — en scope multi-sites, seul le 1er site est interrogé
- **Impact** : Onglet "Données & Qualité" incomplet en vue portfolio
- **Fix** : Fetch pour tous les sites scopés ou afficher la limitation

### P2-7 : Timestamp synchro hardcodé `T08:42:00Z`
- **Fichier** : `backend/routes/cockpit_v2.py:257`
- **Constat** : `"synchro": today.isoformat() + "T08:42:00Z"` — heure fixe inventée
- **Impact** : Le frontend affiche "Dernière synchro" avec une heure fausse chaque jour
- **Fix** : Utiliser `datetime.now(UTC).isoformat()` ou supprimer le champ

### P2-8 : get_portfolio_consumption ne filtre pas deleted_at
- **Fichier** : `backend/services/consumption_unified_service.py:241-247`
- **Constat** : Filtre `Site.actif == True` mais pas `Site.deleted_at.is_(None)` — incohérent avec `not_deleted()`
- **Impact** : Sites supprimés mais encore actifs inclus dans les totaux conso
- **Fix** : Utiliser `not_deleted()` comme le reste du codebase

### P2-9 : Power profile intermittent (500 → 200)
- **Constat** : `/api/power/sites/1/profile` retournait 500 puis 200 après quelques secondes
- **Cause probable** : Cold start du service ou import lazy qui échoue la première fois
- **Fichier** : `backend/routes/power.py:42` (import inline `from services.power.power_profile_service`)
- **Fix** : Déplacer l'import au niveau module

---

## MATRICE CROSS-MODULE

| KPI | Cockpit | Patrimoine | Compliance/summary | Compliance/portfolio | Cohérent? |
|-----|---------|------------|-------------------|---------------------|-----------|
| Conso totale (kWh) | 2,765,196 (mesuré) | 2,947,000 (déclaré) | — | — | **NON** (Δ 6.2%) |
| Score conformité | 57.2 (composite) | — | 0% ok (findings) | 100% ok (readiness) | **NON** (3 métriques) |
| Risque € | 30,000 (réglementaire) | — | — | — | ✅ (unique source) |
| Risque total € | 44,867 (régl+billing) | — | — | — | ✅ |
| Sites tertiaire KO | 3 | — | 1 nok + 2 unknown | — | **NON** |
| Sites BACS KO | 5 | — | 1 nok + 1 unknown | — | **NON** |
| Actions | 15 (9 open, 4 in_progress, 2 done) | — | — | — | ✅ (unique source) |
| Billing total € | — | — | — | — | 306,972 ✅ |
| Factures | 36 | — | — | — | ✅ |
| Anomalies billing | 61 insights | — | — | — | ✅ |

---

## ÉTAT PAR PAGE (routes principales)

| # | Page | Route | Charge | Données | KPIs | Scope | Score |
|---|------|-------|--------|---------|------|-------|-------|
| 1 | Command Center | / | ✅ | ✅ | ✅ | ✅ | 5/6 |
| 2 | Cockpit | /cockpit | ✅ | ✅ | ⚠️ labels "?" | ✅ | 4/6 |
| 3 | Notifications | /notifications | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 4 | Conformité | /conformite | ✅ | ✅ | ⚠️ incohérent | ✅ | 4/6 |
| 5 | Actions | /actions | ✅ | ✅ 15 actions | ✅ | ✅ | 6/6 |
| 6 | Patrimoine | /patrimoine | ✅ | ✅ 5 sites | ✅ | ✅ | 6/6 |
| 7 | Consommations | /consommations | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 8 | Bill Intel | /bill-intel | ✅ | ✅ 61 insights | ✅ | ✅ | 6/6 |
| 9 | Achat Énergie | /achat-energie | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 10 | Billing | /billing | ✅ | ✅ 36 factures | ✅ | ✅ | 6/6 |
| 11 | Monitoring | /monitoring | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 12 | Segmentation | /segmentation | ✅ | ✅ | ✅ | ❌ no scope | 5/6 |
| 13 | Import | /import | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 14 | Connectors | /connectors | ✅ | ✅ | — | ❌ no scope | 5/6 |
| 15 | Watchers | /watchers | ✅ | ✅ | — | ❌ no scope | 5/6 |
| 16 | KB | /kb | ✅ | ✅ | — | ❌ no scope | 5/6 |
| 17 | Admin Users | /admin/users | ✅ | ✅ | — | ❌ (légitime) | 6/6 |
| 18 | Admin Roles | /admin/roles | ✅ | ✅ | — | ❌ (légitime) | 6/6 |
| 19 | RegOps | /regops/:id | ✅ | ✅ | ✅ | ❌ no scope | 5/6 |
| 20 | Diagnostic | /diagnostic-conso | ✅ | ✅ | ✅ | ✅ | 6/6 |
| 21 | Contrat Radar | /contracts-radar | ✅ | ✅ | ✅ | ✅ | 6/6 |

---

## SITE360 — ÉTAT DES ONGLETS

| Onglet | ID | Statut | Composant | Données API | Score |
|--------|-----|--------|-----------|-------------|-------|
| Résumé | resume | ✅ LIVE | TabResume | patrimoine + benchmark | 6/6 |
| Consommation | conso | ✅ LIVE | TabConsoSite | conso unified | 6/6 |
| Factures | factures | ✅ LIVE | SiteBillingMini | billing | 6/6 |
| Réconciliation | reconciliation | ✅ LIVE | TabReconciliation | reconciliation | 5/6 |
| Conformité | conformite | ✅ LIVE | TabConformite | compliance | 5/6 |
| Actions | actions | ✅ LIVE | TabActionsSite | actions | 6/6 |
| Puissance | puissance | ✅ LIVE | TabPuissance | power | 5/6 |
| **Usages** | **MANQUANT** | ❌ | — | — | 0/6 |

---

## CODE HYGIENE

| Check | Résultat | Severity |
|-------|----------|----------|
| TabStubs résiduels | 1 ("à venir" CommandCenter:408) | P2 |
| Calculs métier FE | **0** — clean | ✅ OK |
| Routes orphelines | 0 (beaucoup de redirects Navigate) | ✅ OK |
| Imports morts | Non vérifiable (grep -P unsupported) | — |
| Constantes divergentes | **0** (0.0569 = TURPE, pas CO2) | ✅ OK |
| Endpoints sans response_model | **535/578 (92.6%)** | P1 |
| URLs hardcodées | 0 hors tests | ✅ OK |
| Console.log résiduels | **19** (11 fichiers) | P2 |
| TODO/FIXME | **~11** | P2 |
| CTAs orphelins | **8** | P1 |
| Pages sans scope | **12** (hors login/404/status) | P1 |
| Site360 onglet manquant | **Usages** | P1 |
| datetime deprecated | 1 occurrence | P1 |

---

## TESTS BASELINE

| Suite | Total | Pass | Fail | Skip |
|-------|-------|------|------|------|
| Frontend (Vitest) | 3785 | 3780 | **3** | 2 |
| Backend (Pytest) | ~100+ | ~99+ | **1** | 0 |

### Tests en échec détaillés :
1. **FE** `actionsConsoleV1.test.js` — Cockpit.jsx: navigate('/actions') hardcodé
2. **FE** `site360CockpitWC.test.js` — getBenchmark(site.usage) pattern changed
3. **FE** `DemoJourneyGuard.test.js` — Cockpit.jsx: "EUR" in comment
4. **BE** `test_cdc_contract_simulator.py::test_returns_4_strategies` — SQLAlchemy error

---

## SEED HELIOS — DONNÉES DE RÉFÉRENCE

| Site | Conso (kWh/an) | Surface (m²) | Risque (€) |
|------|---------------|-------------|-----------|
| Siège HELIOS Paris | 595,000 | 3,500 | 7,500 |
| Bureau Régional Lyon | 204,000 | 1,200 | 3,750 |
| Entrepôt HELIOS Toulouse | 720,000 | 6,000 | 7,500 |
| Hôtel HELIOS Nice | 1,120,000 | 4,000 | 3,750 |
| École Jules Ferry Marseille | 308,000 | 2,800 | 7,500 |
| **TOTAL** | **2,947,000** | **17,500** | **30,000** |

---

## RECOMMANDATIONS — PLAN DE CORRECTION

### Sprint P0 (immédiat — avant toute démo)
1. **Fix get_co2 DI** : Ajouter `Depends(get_optional_auth)` dans la signature (sécurité cross-tenant)
2. **Fix soft-delete compliance** : Ajouter `not_deleted()` dans `compute_portfolio_compliance_summary`
3. **Unifier compliance** : Harmoniser les 3 endpoints pour utiliser la même sémantique (findings-based), renommer les champs ambigus
4. **Résoudre divergence conso** : Ajouter label source (mesuré/déclaré) ou unifier
5. **Fix KPI labels** : Passer les labels corrects dans `wrap_kpi_runtime`
6. **Fix 3 tests FE** : navigate('/actions') → `toActionsList()` ; supprimer "EUR" commentaire ; aligner pattern getBenchmark

### Sprint P1 (semaine suivante)
7. **Fix filtre portfolio modulo** : Remplacer `(id-1)%5+1` par `portefeuille_id` dans Cockpit.jsx
8. **Fix constante magique 0.068** : Utiliser `estimated_gain_kwh` ou prix contractuel
9. **Fix coverage factures multi-mois** : Compter les mois entre period_start et period_end
10. Fix flex score "site non trouvé"
11. Fix backend test CDC simulator
12. Ajouter onglet Usages dans Site360
13. Corriger 8 CTAs orphelins
14. Ajouter ScopeContext sur 16 pages métier
15. Ajouter response_model Pydantic sur cockpit + compliance
16. Fix datetime.utcnow() et func.strftime SQLite-only

### Backlog P2
17. Fix N+1 queries cockpit_v2 `_compute_data_briques`
18. Fix intake questions mono-site dans ConformitePage
19. Fix timestamp synchro hardcodé
20. Fix soft-delete dans `get_portfolio_consumption`
21. Supprimer 19 console.log
22. Traiter 11 TODO/FIXME
23. Remplacer texte "à venir" CommandCenter
24. Lazy load maplibre (bundle > 1MB)
25. Déplacer import inline power_profile_service

---

---

## PHASE 2 — ANALYSE VISUELLE SCREENSHOTS (27/27 capturés)

### Dossier : `artifacts/audits/captures/audit-global/2026-04-03-10-25/`

| # | Page | Fichier | Charge | Données | Labels FR | KPIs | Constats |
|---|------|---------|--------|---------|-----------|------|----------|
| 01 | Cockpit | 01-cockpit.png | ✅ | ✅ | ✅ | ⚠️ | "5.7%" readiness anormalement bas (attendu ~77%) |
| 02 | Actions | 02-actions.png | ✅ | ✅ 15 actions | ✅ | ✅ | 52k€ estimé, 20k€ actés, cohérent |
| 03 | Notifications | 03-notifications.png | ✅ | ✅ | ✅ | ✅ | — |
| 04 | Patrimoine | 04-patrimoine.png | ✅ | ✅ 5 sites | ✅ | ✅ | 2.9 GWh, 271k€, 100% qualité |
| 05 | Conformité | 05-conformite.png | ✅ | ✅ | ✅ | ✅ | Score 57, alertes BACS/APER visibles |
| 06 | Conf. Tertiaire | 06-conformite-tertiaire.png | ✅ | ✅ | ✅ | ✅ | — |
| 07 | Consommations | 07-consommations.png | ✅ | ✅ | ✅ | ✅ | — |
| 08 | Explorer | 08-explorer.png | ✅ | ✅ | ✅ | ✅ | — |
| 09 | Portfolio Conso | 09-portfolio-conso.png | ✅ | ✅ | ✅ | ✅ | — |
| 10 | Import Conso | 10-import-conso.png | ✅ | ✅ | ✅ | — | — |
| 11 | Diagnostic | 11-diagnostic.png | ✅ | ✅ | ✅ | ✅ | — |
| 12 | Monitoring | 12-monitoring.png | ✅ | ✅ | ✅ | ✅ | — |
| 13 | Usages Horaires | 13-usages-horaires.png | ✅ | ✅ | ✅ | ✅ | — |
| 14 | Bill Intel | 14-bill-intel.png | ✅ | ✅ | ✅ | ✅ | 8 anomalies, 64k€, 264.5 MWh |
| 15 | Billing Timeline | 15-billing-timeline.png | ✅ | ✅ | ✅ | ✅ | — |
| 16 | Achat Énergie | 16-achat-energie.png | ✅ | ✅ | ✅ | ✅ | — |
| 17 | Assistant Achat | 17-assistant-achat.png | ✅ | ✅ | ✅ | ✅ | — |
| 18 | Renouvellements | 18-renouvellements.png | ✅ | ✅ | ✅ | ✅ | — |
| 19 | Admin Users | 19-admin-users.png | ✅ | ✅ | ✅ | — | — |
| 20 | Onboarding | 20-onboarding.png | ✅ | ✅ | ✅ | — | — |
| 21 | Connectors | 21-connectors.png | ✅ | ✅ | ✅ | — | — |
| 22 | Activation | 22-activation.png | ✅ | ✅ | ✅ | — | — |
| 23 | Status | 23-status.png | ✅ | ✅ | ✅ | — | — |
| 24 | KB | 24-kb.png | ✅ | ✅ | ✅ | — | — |
| 25 | Segmentation | 25-segmentation.png | ✅ | ✅ | ✅ | ✅ | — |
| 26 | Command Center | 26-command-center.png | ✅ | ✅ | ✅ | ⚠️ | Affiche 2,763 MWh (mesuré) vs patrimoine 2,947 MWh |
| 27 | Energy Copilot | 27-energy-copilot.png | ✅ | ✅ | ✅ | ✅ | — |

**Bilan visuel** : 27/27 pages chargent, 0 page blanche, 0 NaN/undefined visible, labels FR corrects partout. Les 2 alertes sont la divergence conso (P0-2 confirmé visuellement) et le readiness score suspect.

---

*Audit réalisé en mode read-only. Zéro modification de code effectuée.*
*Outils utilisés : Grep, Read, Bash (curl API), Playwright audit-agent, analyse visuelle screenshots.*
*27 screenshots archivés dans `artifacts/audits/captures/audit-global/2026-04-03-10-25/`*
