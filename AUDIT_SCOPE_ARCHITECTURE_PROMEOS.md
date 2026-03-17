# AUDIT SCOPE & ARCHITECTURE — PROMEOS POC

**Date** : 17 mars 2026
**Version auditée** : V118
**Méthode** : Inspection complète du repo — lecture seule, zéro hypothèse non signalée
**Posture** : Architecte produit/tech préparant le passage de POC à leader marché B2B énergie France

---

## 1. Executive Summary

PROMEOS est un cockpit énergétique B2B post-ARENH réellement fonctionnel. Le repo contient **~155 000 LOC utiles** répartis entre un backend FastAPI (51 route modules, 85 services, 54 fichiers modèles, 111 tables ORM) et un frontend React/Vite (48+ pages, 48 composants réutilisables, 434 fonctions API). La chaîne métier **Patrimoine → Conformité → Facturation → Achat → Alertes → Actions** est implémentée bout en bout avec des liens réels entre domaines (site_id omniprésent sur 40 colonnes FK, org_id sur 18).

**Niveau de maturité** : POC avancé / pré-MVP. Solide pour une démo investisseur. Pas production-ready.

**Forces** :
- Couverture fonctionnelle exceptionnelle pour un POC (467 endpoints, 8 domaines métier complets)
- Chaîne patrimoine → conformité réellement liée (compliance scoring pondéré DT 45% + BACS 30% + APER 25%)
- Shadow billing V2 TURPE opérationnel avec reconciliation 3-voies
- Pipeline import CSV → staging → QA → activation production-grade
- 218 tests backend + 17 specs E2E Playwright — qualité inhabituelle pour un POC
- CI/CD Quality Gate opérationnel (lint + typecheck + test + build)

**Faiblesses critiques** :
- **Fichiers monolithiques** : `patrimoine.py` (3 129 LOC), `MonitoringPage.jsx` (3 112 LOC), `Patrimoine.jsx` (2 223 LOC) — dette structurelle majeure
- **Logique métier dispersée** : routes contiennent de la logique métier inline au lieu de déléguer aux services
- **2 connecteurs sur 4 sont des stubs** (Enedis DataConnect, Météo-France) — données réelles impossibles
- **Pas de DB réelle** : SQLite embarqué, aucune migration Alembic visible
- **Auth simplifiée** : JWT basique, PII en clair, IDOR historique (V23)
- **Pas de contrat de données formalisé** : pas de JSON Schema partagé, pas d'OpenAPI exporté consommé par le front

**Capacité à devenir leader marché** : le socle fonctionnel est là. La dette technique est gérable mais le passage à l'échelle nécessite un refactoring structurel des fichiers monolithiques, une vraie couche de persistance, et la finalisation des connecteurs externes. Estimé à 3-4 sprints de refactoring ciblé avant un MVP commercialisable.

---

## 2. Cartographie du repo

### Arborescence synthétique

```
promeos-poc/
├── backend/                          # FastAPI — Python 3.11
│   ├── main.py                       # Entrypoint (FastAPI app, CORS, 51 routers)
│   ├── routes/          (52 fichiers, 23 473 LOC)  # Endpoints API
│   ├── services/        (85 fichiers, 31 459 LOC)  # Logique métier
│   ├── models/          (54 fichiers,  6 325 LOC)  # SQLAlchemy ORM (111 tables)
│   ├── middleware/                    # RequestContext, auth, rate-limit
│   ├── ai_layer/                     # 5 agents IA (stub sans clé OpenAI)
│   ├── connectors/                   # 4 connecteurs (2 live, 2 stubs)
│   ├── watchers/                     # Veille réglementaire
│   ├── app/                          # Bill Intelligence, KB, référentiel
│   └── tests/           (218 fichiers, 60 049 LOC) # Pytest
├── frontend/                         # React 18 + Vite + TailwindCSS
│   └── src/
│       ├── App.jsx                   # Entrypoint routing (lazy-loaded)
│       ├── pages/       (48+ fichiers, 33 113 LOC)  # Pages métier
│       ├── components/  (48 fichiers, 14 479 LOC)   # Composants partagés
│       ├── layout/      (10 fichiers,  1 521 LOC)   # AppShell, Nav, Scope
│       ├── contexts/    (5 fichiers)                 # Auth, Demo, Scope, Expert
│       ├── services/    (api.js: 1 799 LOC)         # 434 fonctions API
│       └── ui/                       # Primitives UI (Skeleton, etc.)
├── e2e/                 (17 specs, 2 058 LOC)       # Playwright E2E
├── .github/workflows/                # Quality Gate CI (lint+test+build)
├── Makefile                          # dev, lint, test, ci, e2e, build
└── AUDIT_*.md           (15+ fichiers)              # Audits précédents
```

### Entrypoints

| Composant | Fichier | Rôle |
|---|---|---|
| Backend API | `backend/main.py` | FastAPI app, CORS, 51 routers montés |
| Frontend SPA | `frontend/src/App.jsx` | React Router, lazy-load, 42 routes |
| Navigation | `frontend/src/layout/NavRegistry.js` | 5 modules nav (Pilotage, Patrimoine, Énergie, Achat, Admin) |
| API Client | `frontend/src/services/api.js` | 434 fonctions, cache GET 5s, dedup |
| CI/CD | `.github/workflows/*.yml` | Quality Gate : lint + mypy + pytest + vite build |

### Dépendances structurantes

**Backend** : FastAPI, SQLAlchemy (ORM), Pydantic (validation), uvicorn, python-jose (JWT)
**Frontend** : React 18, react-router-dom v6, axios, TailwindCSS, lucide-react, recharts
**Outillage** : Ruff (lint), Mypy (types), Pytest, Vitest, Playwright, Prettier, ESLint
**Pas de** : Alembic (migrations), Redis/Celery (async), Docker compose, OpenAPI codegen

---

## 3. Cartographie métier PROMEOS

| Domaine | État | Maturité | Fichiers clés backend | Fichiers clés frontend | Incohérences |
|---|---|---|---|---|---|
| **Patrimoine** | Complet (CRUD + import CSV + staging + QA + activation) | ★★★★★ | `routes/patrimoine.py` (3129L), `services/patrimoine_service.py` (1429L), `models/patrimoine.py`, `models/site.py`, `models/compteur.py`, `models/batiment.py` | `pages/Patrimoine.jsx` (2223L), `pages/Site360.jsx` (1612L), `pages/ImportPage.jsx` (676L) | `patrimoine.py` route est monolithique (3129L) — logique métier inline |
| **Conformité** | Complet multi-framework (DT, BACS, APER, CEE) | ★★★★☆ | `routes/compliance.py` (982L), `routes/bacs.py` (620L), `routes/tertiaire.py` (1051L), `services/compliance_engine.py` (1219L), `services/compliance_rules.py` (774L), `services/bacs_engine.py` (733L) | `pages/ConformitePage.jsx` (1560L), `pages/SiteCompliancePage.jsx` (729L), `pages/AperPage.jsx`, `pages/tertiaire/` (4 fichiers) | APER minimal (53 LOC route, scoring only). CEE : modèles OK, workflows UI limités |
| **Billing** | Complet (CSV + PDF import, shadow V2 TURPE, reconciliation) | ★★★★☆ | `routes/billing.py` (1822L), `services/billing_service.py` (926L), `services/billing_shadow_v2.py` (568L), `services/reconciliation_service.py` (806L), `models/billing_models.py` | `pages/BillIntelPage.jsx` (1219L), `pages/BillingPage.jsx` (709L), `pages/PaymentRulesPage.jsx`, `pages/PortfolioReconciliationPage.jsx` | `billing.py` route contient du calcul inline — devrait être dans le service |
| **Purchase** | Complet (scénarios, assistant 8 étapes, offres, reconciliation) | ★★★★☆ | `routes/purchase.py` (1251L), `models/purchase_models.py`, `services/` (purchase helpers dispersés) | `pages/PurchasePage.jsx` (2018L), `pages/PurchaseAssistantPage.jsx` (1823L), `pages/ContractRadarPage.jsx` (554L) | Pages front monolithiques (2018L + 1823L). Offres statiques (pas de feed marché live) |
| **Alertes / Actions** | Complet (lifecycle, evidence, ROI, anomaly linking, templates) | ★★★★★ | `routes/actions.py` (1312L), `routes/action_templates.py` (353L), `models/action_item.py`, `services/` (action helpers) | `pages/ActionsPage.jsx` (1579L), `pages/AnomaliesPage.jsx` (720L) | Pas de closure automatique par evidence. Bulk anomaly→action absent |
| **Cockpit / Portefeuille** | Complet (KPI portfolio, 2-min dashboard, site 360) | ★★★★☆ | `routes/dashboard_2min.py` (500L), `routes/portfolio.py` (420L), `routes/sites.py` (492L) | `pages/Cockpit.jsx` (887L), `pages/Site360.jsx` (1612L), `pages/ConsumptionPortfolioPage.jsx` (978L) | CommandCenter.jsx (445L) = dead code, route commentée |
| **Consommation** | Complet (diagnostic, contexte, usages, TOU, HP/HC, tunnel) | ★★★★☆ | `routes/consumption_diagnostic.py` (941L), `routes/consumption_context.py` (249L), `routes/ems.py` (1203L), `services/consumption_diagnostic.py` (930L) | `pages/ConsommationsPage.jsx`, `pages/ConsumptionDiagPage.jsx` (1173L), `pages/ConsumptionExplorerPage.jsx` (1006L), `pages/MonitoringPage.jsx` (3112L) | MonitoringPage.jsx est le plus gros fichier front (3112L) — monolithe |
| **Onboarding** | Fonctionnel (wizard 6 étapes, auto-détection) | ★★★☆☆ | `routes/onboarding_stepper.py` (257L), `routes/onboarding.py` (269L) | `pages/OnboardingPage.jsx` | Double route (legacy + stepper) — à consolider |
| **IA / Agents** | Stub (5 agents, fallback template sans clé OpenAI) | ★★☆☆☆ | `routes/ai_route.py` (91L), `ai_layer/` (5 agents) | Intégré dans pages existantes | Aucun agent réellement connecté à un LLM |

---

## 4. Flux bout-en-bout réels

### Flux 1 : Création / Chargement patrimoine

| Aspect | Détail |
|---|---|
| **Déclencheur** | Upload CSV via `/import` ou seed démo via `/demo/load` |
| **Écrans** | `ImportPage.jsx` → `Patrimoine.jsx` (staging table) → `Site360.jsx` |
| **Endpoints** | `POST /patrimoine/staging/import` → `GET /patrimoine/staging/{batch}/summary` → `POST /patrimoine/staging/{batch}/validate` → `POST /patrimoine/staging/{batch}/fix/bulk` → `POST /patrimoine/staging/{batch}/activate` |
| **Modèles** | `StagingBatch`, `StagingSite`, `StagingCompteur`, `QualityFinding` → `Site`, `Compteur`, `Batiment`, `EnergyContract` |
| **État** | **OK** — Pipeline complet CSV → staging → QA → fix → activate |
| **Commentaire** | World-class pour un POC. Auto-fix, quality gate, diff plan, export rapport. |

### Flux 2 : Association sites / bâtiments / compteurs / contrats

| Aspect | Détail |
|---|---|
| **Déclencheur** | Post-activation ou CRUD manuel |
| **Écrans** | `Patrimoine.jsx` (liste) → `Site360.jsx` (détail avec tabs) |
| **Endpoints** | `GET /sites`, `GET /sites/{id}`, `GET /patrimoine/sites/{id}/meters/tree`, `CRUD /patrimoine/contracts` |
| **Modèles** | `Site` → `Batiment` (FK site_id) → `Compteur` (FK site_id) → `EnergyContract` (FK site_id) → `DeliveryPoint` |
| **État** | **OK** — Hiérarchie complète, arbre compteurs, contrats liés |
| **Commentaire** | FK site_id présente sur 40 colonnes cross-modèles. Chaînage solide. |

### Flux 3 : Conformité OPERAT / BACS / APER

| Aspect | Détail |
|---|---|
| **Déclencheur** | Navigation `/conformite` ou `/conformite/tertiaire` |
| **Écrans** | `ConformitePage.jsx` (tabs: obligations, données, preuves, tertiaire, BACS) → `TertiaireDashboardPage.jsx` → `TertiaireEfaDetailPage.jsx` → `SiteCompliancePage.jsx` |
| **Endpoints** | `GET /compliance/summary`, `POST /compliance/recompute`, `CRUD /tertiaire/efa`, `CRUD /bacs/site/{id}`, `GET /compliance/findings` |
| **Modèles** | `ComplianceFinding` (FK site_id), `TertiaireEfa` (FK site_id), `BacsAsset`, `BacsSystem`, `CeeDossier` |
| **État** | **OK pour DT + BACS, partiel pour CEE, minimal pour APER** |
| **Commentaire** | Score composite pondéré (DT 45% + BACS 30% + APER 25%). APER = 53 LOC route, scoring seulement. CEE = modèles présents, pas de workflow UI complet. |

### Flux 4 : Import facture / Shadow billing

| Aspect | Détail |
|---|---|
| **Déclencheur** | Upload CSV/PDF via `/bill-intel` ou import batch |
| **Écrans** | `BillIntelPage.jsx` (tabs: import, historique, anomalies, shadow, timeline) → `BillingPage.jsx` → `PortfolioReconciliationPage.jsx` |
| **Endpoints** | `POST /billing/import-csv`, `POST /billing/import-pdf`, `GET /billing/invoices`, `POST /billing/reconcile-all`, `GET /billing/insights/{id}` |
| **Modèles** | `EnergyInvoice` (FK site_id), `EnergyInvoiceLine`, `BillingInsight`, `BillingImportBatch`, `MarketPrice` |
| **État** | **OK** — Import CSV + PDF, shadow V2 TURPE, reconciliation 3-voies, explainability |
| **Commentaire** | Lien billing → site solide (FK). Lien billing → contrat via `EnergyContract`. Shadow TURPE V2 avec grilles CSPE/R13/R14. |

### Flux 5 : Scénarios achat énergie

| Aspect | Détail |
|---|---|
| **Déclencheur** | Navigation `/achat-energie` ou `/achat-assistant` |
| **Écrans** | `PurchasePage.jsx` → `PurchaseAssistantPage.jsx` (wizard 8 étapes) → `ContractRadarPage.jsx` |
| **Endpoints** | `GET /purchase/scenarios`, `CRUD /purchase/assumptions/{site_id}`, `POST /purchase/compute/{site_id}`, `POST /purchase/quote-offer`, `GET /purchase/results/{id}` |
| **Modèles** | `PurchaseAssumptionSet` (FK site_id), `PurchaseScenarioResult`, `OfferQuote`, `ContractRadarRecord` |
| **État** | **OK** — Scénarios multi-site, assistant IA, reconciliation offre vs facture |
| **Commentaire** | Lien purchase → consommation via volume_kwh calculé. Lien purchase → contrat via radar. Offres statiques (pas de feed marché temps réel). |

### Flux 6 : Alertes et création d'actions

| Aspect | Détail |
|---|---|
| **Déclencheur** | Anomalie détectée (billing, compliance, conso) ou création manuelle |
| **Écrans** | `AnomaliesPage.jsx` (inbox anomalies) → `ActionsPage.jsx` (lifecycle, evidence, comments) |
| **Endpoints** | `POST /actions/anomaly-links`, `POST /actions`, `PATCH /actions/{id}`, `POST /actions/{id}/evidence`, `GET /actions/{id}/closeability` |
| **Modèles** | `ActionItem` (FK site_id, source_type, source_id), `ActionItemEvidence`, `ActionItemProof`, `ActionItemComment` |
| **État** | **OK** — Lifecycle complet OPEN → IN_PROGRESS → COMPLETED, evidence, ROI, dedup |
| **Commentaire** | Dedup : unique constraint sur (org_id, source_type, source_id, source_key). Lien anomalie → action bidirectionnel. Pas de closure automatique. |

### Flux 7 : Vues exécutives / portefeuille / site

| Aspect | Détail |
|---|---|
| **Déclencheur** | Navigation `/cockpit` (défaut), `/consommations/portfolio`, `/sites/{id}` |
| **Écrans** | `Cockpit.jsx` (KPIs portfolio) → `ConsumptionPortfolioPage.jsx` → `Site360.jsx` (fiche site multi-tabs) |
| **Endpoints** | `GET /dashboard-2min/snapshot`, `GET /portfolio/summary`, `GET /sites/{id}`, `GET /compliance/summary` |
| **Modèles** | Agrégation cross-domaine : Sites + Consommation + Compliance + Billing + Actions |
| **État** | **OK** — Dashboard 2-min, portfolio KPIs, site 360 |
| **Commentaire** | Le Cockpit agrège réellement les données des 5 domaines. CommandCenter.jsx = dead code (route commentée dans App.jsx). |

---

## 5. Contrats de données et modèles canoniques

### Objets centraux et relations

```
Organisation (1)
  └── Portefeuille (N)
       └── Site (N)
            ├── Batiment (N)
            │    └── Compteur (N)
            ├── EnergyContract (N)
            ├── DeliveryPoint (N)
            ├── EnergyInvoice (N)
            ├── ComplianceFinding (N)
            ├── TertiaireEfa (N)
            ├── BacsAsset (N)
            ├── PurchaseAssumptionSet (N)
            ├── ActionItem (N)
            ├── Consommation (N)
            └── AiInsight (N, polymorphe via object_type/object_id)
```

**site_id est la clé de voûte** : présent sur 40 colonnes FK à travers tous les domaines. C'est le lien transversal qui fait tenir la chaîne PROMEOS.

### Vérité des liens cross-domaines

| Lien | Implémentation | Fichier preuve |
|---|---|---|
| Patrimoine → Conformité | `ComplianceFinding.site_id → sites.id` | `models/compliance_finding.py:22` |
| Patrimoine → Billing | `EnergyInvoice.site_id → sites.id` | `models/billing_models.py` |
| Patrimoine → Purchase | `PurchaseAssumptionSet.site_id → sites.id` | `models/purchase_models.py:24` |
| Patrimoine → Actions | `ActionItem.site_id → sites.id` | `models/action_item.py:52` |
| Billing → Contrat | `EnergyInvoice.contract_id` (implicite via site) | `models/billing_models.py` |
| Actions → Anomalies | `ActionItem.source_type + source_id` (polymorphe) | `models/action_item.py:37` |
| Compliance → Actions | Via `source_type='compliance'` sur ActionItem | `routes/actions.py` |
| Purchase → Consommation | Via `volume_kwh` calculé depuis données conso | `routes/purchase.py` |

### Trous de modélisation

1. **Pas de modèle `Contrat` unifié** : `EnergyContract` (patrimoine) et `PurchaseScenarioResult` (achat) ne partagent pas de FK directe. Le lien contrat → offre acceptée est implicite.

2. **Pas d'entité `Périmètre de facturation`** : le shadow billing opère par site, mais un contrat peut couvrir N sites. Pas de modèle `ContractPerimeter` explicite.

3. **Consommation sans FK facture** : `Consommation` et `EnergyInvoice` partagent `site_id` mais pas de lien direct consommation ↔ ligne de facture. La reconciliation est calculée, pas modélisée.

4. **KPI sans formule explicite** : les KPIs du dashboard 2-min sont calculés inline dans `routes/dashboard_2min.py`. Pas de modèle `KpiDefinition` avec formule, unité, période, périmètre.

5. **Enums massifs non typés** : `models/enums.py` = 782 LOC, 75+ enums dans un seul fichier. Pas de groupement par domaine.

### Ambiguïtés de périmètre

- **Organisation vs EntitéJuridique** : les deux existent comme modèles séparés. La relation hiérarchique n'est pas toujours claire dans les routes.
- **Portefeuille** : utilisé comme scope de filtrage (ScopeContext) mais rarement comme entité métier avec ses propres attributs.
- **Unités** : kWh partout (borné 0 - 1e9 dans Pydantic), EUR pour coûts, gCO2/kWh pour carbone. Pas de modèle `UnitSystem` centralisé mais la cohérence est assurée par convention.

---

## 6. Top 20 fichiers les plus critiques

| # | Fichier | LOC | Rôle | Problème principal | Risque | Action |
|---|---|---|---|---|---|---|
| 1 | `backend/routes/patrimoine.py` | 3 129 | Import, staging, QA, activation patrimoine | **Monolithe** : logique métier inline, 35+ endpoints dans 1 fichier | **P0** | Découper en 4 sous-modules (staging, qa, crud, activation) |
| 2 | `frontend/src/pages/MonitoringPage.jsx` | 3 112 | Performance & monitoring multi-tabs | **Plus gros fichier front** : impossible à maintenir, tester, review | **P1** | Extraire en composants par tab |
| 3 | `frontend/src/pages/Patrimoine.jsx` | 2 223 | Liste sites, wizard création, staging | Monolithique, mélange CRUD + wizard + import | **P1** | Extraire wizard et staging |
| 4 | `frontend/src/pages/PurchasePage.jsx` | 2 018 | Scénarios d'achat, simulation | Page complexe sans découpage | **P1** | Extraire ScenarioBuilder, ResultsPanel |
| 5 | `frontend/src/pages/PurchaseAssistantPage.jsx` | 1 823 | Assistant achat 8 étapes | Wizard monolithique | **P1** | Un composant par étape |
| 6 | `backend/routes/billing.py` | 1 822 | Import, shadow, reconciliation factures | Logique shadow billing inline dans les routes | **P1** | Déléguer entièrement au service |
| 7 | `backend/services/patrimoine_service.py` | 1 429 | Service patrimoine central | Fichier service le plus gros, responsabilités multiples | **P1** | Découper par sous-domaine |
| 8 | `backend/routes/actions.py` | 1 312 | Actions lifecycle complet | 45 endpoints, certains avec logique inline | **P1** | Séparer CRUD, evidence, anomaly-links |
| 9 | `backend/routes/purchase.py` | 1 251 | Scénarios achat, offres, assistant | Calcul inline, devrait être dans service | **P1** | Extraire purchase_compute_service |
| 10 | `backend/services/compliance_engine.py` | 1 219 | Moteur scoring conformité | Gros mais cohérent — risque de régression si touché | **P2** | Tests de non-régression avant refacto |
| 11 | `frontend/src/pages/BillIntelPage.jsx` | 1 219 | Bill Intelligence multi-tabs | Page monolithique | **P1** | Extraire par tab |
| 12 | `backend/routes/ems.py` | 1 203 | Energy Monitoring System | 49 endpoints, domaine EMS entier dans 1 fichier | **P1** | Découper par sous-ressource |
| 13 | `frontend/src/pages/ConsumptionDiagPage.jsx` | 1 173 | Diagnostic consommation | Visualisations + logique mélangées | **P2** | Extraire composants chart |
| 14 | `frontend/src/services/api.js` | 1 799 | Couche API unique (434 fonctions) | **Fichier god-object** : toutes les API dans 1 fichier | **P0** | Découper par domaine (api/patrimoine.js, api/billing.js, etc.) |
| 15 | `backend/routes/tertiaire.py` | 1 051 | OPERAT / décret tertiaire | 50 endpoints, EFA lifecycle complet | **P1** | Découper EFA CRUD vs controls vs export |
| 16 | `backend/models/enums.py` | 782 | 75+ enums dans 1 fichier | Couplage maximal, pas de groupement par domaine | **P1** | 1 fichier enum par domaine |
| 17 | `frontend/src/pages/ActionsPage.jsx` | 1 579 | Actions lifecycle UI | Liste + détail + création + evidence dans 1 page | **P1** | Extraire ActionDetail, ActionCreate |
| 18 | `backend/services/billing_service.py` | 926 | Service facturation | Cohérent mais mélange import + insight + shadow | **P2** | Séparer billing_import_service |
| 19 | `frontend/src/pages/ConformitePage.jsx` | 1 560 | Conformité multi-tabs | 5 tabs dans 1 composant monolithique | **P1** | 1 composant par tab |
| 20 | `backend/services/reconciliation_service.py` | 806 | Reconciliation 3-voies | Service critique, bien isolé mais complexe | **P2** | Ajouter tests de non-régression |

---

## 7. Incohérences transverses

### 7.1 Architecture : Routes contiennent de la logique métier

**Constat** : Les fichiers `routes/*.py` ne sont pas de simples contrôleurs HTTP. Ils contiennent du calcul, de l'agrégation, des requêtes ORM complexes inline.

**Fichiers** : `patrimoine.py` (3129L), `billing.py` (1822L), `purchase.py` (1251L)

**Impact** : Impossible de réutiliser la logique sans passer par HTTP. Tests unitaires forcés de monter un serveur FastAPI.

**Verdict** : **P1 — Anti-pattern structurel** qui freine l'industrialisation.

### 7.2 Frontend : api.js god-object

**Constat** : 434 fonctions API dans un seul fichier `frontend/src/services/api.js` (1 799 LOC). Aucun découpage par domaine.

**Impact** : Merge conflicts systématiques. Impossible de tree-shake. Couplage maximal entre domaines côté client.

**Verdict** : **P0 — Bloque la collaboration multi-développeurs.**

### 7.3 Contrat ↔ Facture ↔ Achat : lien implicite

**Constat** : `EnergyContract` (patrimoine) n'a pas de FK directe vers `PurchaseScenarioResult` (achat). Le lien contrat → offre acceptée passe par convention (même site_id + période), pas par une relation explicite.

**Impact** : Pas de traçabilité : « cette facture correspond à quel contrat issu de quelle offre de quel scénario d'achat ? »

**Verdict** : **P1 — Rupture de traçabilité métier** sur la chaîne achat → contrat → facture.

### 7.4 KPIs sans modèle formel

**Constat** : Les KPIs du cockpit (dashboard_2min) sont calculés inline dans les routes. Pas de modèle `KpiDefinition` (formule, unité, période, source, périmètre).

**Fichier** : `routes/dashboard_2min.py` (500L) — calculs directs dans les endpoints.

**Impact** : Impossible de versionner/auditer les formules. Incohérence possible entre le KPI affiché au cockpit et celui calculé en compliance.

**Verdict** : **P1 — Risque de vérité métier divergente.**

### 7.5 Connecteurs stubs = données réelles impossibles

**Constat** : `connectors/enedis_dataconnect.py` et `connectors/meteofrance.py` retournent `[]`. Pas d'OAuth Enedis, pas d'appel API Météo-France.

**Impact** : En production, aucune donnée Linky ni météo réelle. Le demo seed compense avec des données synthétiques.

**Verdict** : **P0 pour MVP — Bloque la crédibilité auprès d'un client réel.**

### 7.6 Navigation masque des fonctionnalités

**Constat** : `NavRegistry.js` contient un array `HIDDEN_PAGES` avec 12 pages accessibles uniquement via CommandPalette (Ctrl+K) : diagnostic conso, usages horaires, tertiaire, APER, segmentation, connecteurs, etc.

**Impact** : Fonctionnalités développées mais invisibles pour l'utilisateur standard. Le mode Expert ne suffit pas — certaines pages sont carrément cachées.

**Verdict** : **P2 — Investissement perdu si personne ne trouve ces pages.**

### 7.7 Double système de navigation

**Constat** : `NavRegistry.js` contient à la fois `NAV_SECTIONS` (Rail + Panel architecture, 5 modules) et `NAV_MAIN_SECTIONS` (sidebar collapsible, 4 sections). Deux systèmes parallèles pour le même besoin.

**Impact** : Source de bugs si l'un est mis à jour sans l'autre.

**Verdict** : **P2 — Dette technique navigation.**

### 7.8 Dead code confirmé

**Constat** :
- `CommandCenter.jsx` (445 LOC) — route commentée dans `App.jsx`
- `EnergyCopilotPage.jsx` — route commentée, redirect vers `/`
- `CompliancePage` — déprécié, redirect vers `/conformite`

**Verdict** : **P2 — Nettoyage rapide.**

### 7.9 Pas de migration DB

**Constat** : Aucun dossier `alembic/`, aucun fichier de migration. SQLAlchemy avec `create_all()` probable.

**Impact** : Toute modification de schéma nécessite un reset complet. Impossible en production.

**Verdict** : **P0 pour production — Bloque tout déploiement sérieux.**

---

## 8. Risques majeurs

### P0 — Bloquent crédibilité / sécurité / vérité métier

| # | Risque | Détail | Fichier(s) |
|---|---|---|---|
| P0-1 | **Pas de migration DB** | SQLAlchemy sans Alembic. Impossible de faire évoluer le schéma en production | Aucun dossier `alembic/` |
| P0-2 | **api.js god-object** | 434 fonctions dans 1 fichier. Merge conflicts, couplage, impossible à scaler en équipe | `frontend/src/services/api.js` |
| P0-3 | **Connecteurs Enedis/Météo stubs** | Retournent `[]`. Aucune donnée réelle en production | `connectors/enedis_dataconnect.py`, `connectors/meteofrance.py` |
| P0-4 | **PII en clair** | Emails utilisateurs stockés sans chiffrement. RGPD non conforme | `models/iam.py` |
| P0-5 | **patrimoine.py = 3129 LOC** | Route monolithique avec logique métier inline. Risque de régression maximal | `routes/patrimoine.py` |

### P1 — Dégradent qualité produit / maintenance

| # | Risque | Détail |
|---|---|---|
| P1-1 | **7 pages front > 1500 LOC** | Monolithes impossibles à tester, review, maintenir |
| P1-2 | **Logique métier dans les routes** | Calculs inline dans billing.py, purchase.py, actions.py |
| P1-3 | **Lien contrat → achat implicite** | Pas de FK EnergyContract → PurchaseScenarioResult |
| P1-4 | **KPIs sans modèle formel** | Formules inline dans dashboard_2min.py |
| P1-5 | **enums.py = 782 LOC monolithe** | 75+ enums dans 1 fichier, couplage cross-domaine |
| P1-6 | **APER minimal** | 53 LOC route, scoring only, pas de workflow |
| P1-7 | **CEE workflow UI absent** | Modèles backend OK, pas de parcours front complet |
| P1-8 | **Auth simplifiée** | JWT basique, pas de refresh token rotation, IDOR historique |

### P2 — Améliorations premium / industrialisation

| # | Risque | Détail |
|---|---|---|
| P2-1 | Dead code (CommandCenter, EnergyCopilot, CompliancePage) |
| P2-2 | Double système navigation (NAV_SECTIONS + NAV_MAIN_SECTIONS) |
| P2-3 | 12 pages cachées dans HIDDEN_PAGES |
| P2-4 | Pas d'OpenAPI spec exportée/consommée par le front |
| P2-5 | Pas de Docker compose pour dev/staging |
| P2-6 | Pas de WebSocket (polling uniquement) |
| P2-7 | IA agents stub sans LLM réel |
| P2-8 | Pas de i18n (français hardcodé) |

---

## 9. Plan de transformation recommandé

### Architecture cible

```
promeos/
├── backend/
│   ├── domains/                    # Découpage par bounded context
│   │   ├── patrimoine/
│   │   │   ├── routes.py           # Contrôleur HTTP pur (validation + délégation)
│   │   │   ├── service.py          # Logique métier
│   │   │   ├── models.py           # ORM
│   │   │   ├── schemas.py          # Pydantic (input/output)
│   │   │   └── enums.py            # Enums du domaine
│   │   ├── compliance/
│   │   ├── billing/
│   │   ├── purchase/
│   │   ├── actions/
│   │   └── cockpit/
│   ├── shared/                     # Cross-cutting: auth, scope, base models
│   ├── connectors/                 # Intégrations externes
│   ├── migrations/                 # Alembic
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── domains/                # Miroir du backend
│   │   │   ├── patrimoine/
│   │   │   │   ├── api.js          # Appels API du domaine
│   │   │   │   ├── pages/          # Pages du domaine
│   │   │   │   └── components/     # Composants du domaine
│   │   │   ├── billing/
│   │   │   └── ...
│   │   ├── shared/                 # Layout, contexts, UI primitives
│   │   └── App.jsx
│   └── ...
└── e2e/
```

### Quick wins (< 1 sprint)

| Action | Impact | Effort |
|---|---|---|
| Découper `api.js` en `api/patrimoine.js`, `api/billing.js`, etc. | Débloque collaboration | 1 jour |
| Supprimer dead code (CommandCenter, EnergyCopilot, legacy redirects) | Clarté | 2 heures |
| Découper `enums.py` par domaine | Réduit couplage | 1 jour |
| Unifier NAV_SECTIONS / NAV_MAIN_SECTIONS | Supprime bug source | 1 jour |
| Ajouter Alembic + migration initiale | Débloque production | 1 jour |

### Chantiers structurants (2-4 sprints)

| Chantier | Description | Priorité |
|---|---|---|
| **Refacto patrimoine.py** | Découper en 4 sous-modules (staging, qa, crud, activation). Extraire logique dans services. | Sprint 1 |
| **Refacto pages front monolithiques** | Les 7 pages > 1500 LOC : extraire composants par tab/section | Sprint 1-2 |
| **Contrat de données formel** | Créer modèle `ContractLifecycle` liant Offre → Contrat → Facture | Sprint 2 |
| **Modèle KPI** | Table `KpiDefinition` (formule, unité, période, source) consommée par cockpit | Sprint 2 |
| **Connecteur Enedis OAuth** | Implémenter le flow OAuth DataConnect pour données Linky réelles | Sprint 2-3 |
| **Connecteur Météo-France** | Appels API réels pour DJU et normalisation climatique | Sprint 3 |
| **Chiffrement PII** | Chiffrement au repos des champs email/nom via SQLAlchemy TypeDecorator | Sprint 3 |
| **Routes → Services** | Extraire toute logique métier des routes billing, purchase, actions | Sprint 3-4 |

### Ordre de refacto recommandé

1. **api.js** → découpage par domaine (quick win, débloque tout)
2. **Alembic** → migrations DB (prérequis production)
3. **patrimoine.py** → refacto route monolithique
4. **Pages front** → MonitoringPage, Patrimoine, PurchasePage, PurchaseAssistant
5. **Contrat de données** → FK explicites achat → contrat → facture
6. **Connecteurs** → Enedis puis Météo-France
7. **APER + CEE** → workflows complets

---

## 10. Ce qu'il faut montrer ensuite pour audit approfondi

### Shortlist des 10 fichiers à auditer en priorité

| # | Fichier | Pourquoi |
|---|---|---|
| 1 | `backend/routes/patrimoine.py` | Plus gros fichier route (3129L), logique métier inline, cœur du flux |
| 2 | `backend/services/compliance_engine.py` | Moteur de scoring (1219L), formules de pondération DT/BACS/APER |
| 3 | `backend/services/billing_shadow_v2.py` | Shadow billing TURPE V2 (568L), vérité du calcul facturation |
| 4 | `backend/services/reconciliation_service.py` | Reconciliation 3-voies (806L), cœur de la vérité billing |
| 5 | `frontend/src/services/api.js` | God-object API (1799L), 434 fonctions, contrat front-back |
| 6 | `frontend/src/layout/NavRegistry.js` | Registre navigation complet, architecture d'information produit |
| 7 | `backend/models/enums.py` | 75+ enums (782L), tous les états/types/statuts du système |
| 8 | `backend/routes/billing.py` | Import + shadow + reconciliation (1822L), logique inline |
| 9 | `backend/services/patrimoine_service.py` | Service patrimoine central (1429L), le plus gros service |
| 10 | `backend/main.py` | Entrypoint — 51 routers montés, middleware stack, config CORS |

### Questions à poser lors de l'audit approfondi

1. Les formules du `compliance_engine.py` sont-elles conformes aux textes réglementaires (décret tertiaire, BACS EN 15232) ?
2. Les grilles TURPE V2 dans `billing_shadow_v2.py` sont-elles à jour CRE 2025/2026 ?
3. La reconciliation 3-voies dans `reconciliation_service.py` gère-t-elle les cas limites (factures rectificatives, avoirs, prorata temporis) ?
4. Le modèle `ActionItem.source_type` polymorphe est-il suffisant ou faut-il des tables de liaison explicites ?
5. Le scoring compliance (DT 45% + BACS 30% + APER 25%) est-il validé par un juriste énergie ?

---

*Rapport généré le 17 mars 2026 — Audit lecture seule, aucun fichier modifié.*
