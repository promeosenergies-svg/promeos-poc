# AUDIT PROMEOS — ÉTAPE 0 : CADRAGE

> **Date** : 2026-03-23
> **Auditeur** : Claude Opus 4.6 (multi-agent, 3 explorateurs parallèles)
> **Repo** : `c:\Users\amine\promeos-poc\promeos-poc`
> **Méthode** : Lecture exhaustive du code source, vérification fichier par fichier, zero correction appliquée
> **Statut** : CADRAGE UNIQUEMENT — aucune modification du repo

---

## 1. Résumé exécutif

Le POC PROMEOS est **significativement plus avancé** que le premier audit ne le laissait croire.

L'audit initial (note 6.5/10) contenait **3 erreurs factuelles graves** sur les P0 :

- La trajectoire Décret Tertiaire EST implémentée (`operat_trajectory.py`)
- L'APER EST implémentée (`aper_service.py`, 251 lignes)
- Le data dictionary EXISTE (`docs/data-dictionary.md`, 1677 lignes)

Le **vrai risque** n'est pas l'absence de briques, mais les **déconnexions entre briques existantes** :

- Le KPI cockpit lit un champ plat (`Site.avancement_decret_pct`) au lieu d'appeler `validate_trajectory()`
- Les scénarios achat utilisent des facteurs prix fixes (1.05/0.95/0.88)
- La chaîne données→KPI→actions n'est pas automatique (tout est on-demand)
- Deux sources de prix par défaut coexistent (0.15 vs 0.18 EUR/kWh)

**Baseline corrigé : 7.0/10** (au lieu de 6.5)
**Note atteignable à 90 jours : 8.5/10** (inchangée)

---

## 2. Baseline retenu

### 2.1 Erreurs corrigées par rapport au premier audit

| Constat initial | Réalité vérifiée | Fichier preuve |
| --- | --- | --- |
| "P0-1 : Trajectoire DT non calculée" | **FAUX** — `validate_trajectory()` implémente baseline year + delta kwh + statut on_track/off_track + reliability warnings | `backend/services/operat_trajectory.py:172-280` |
| "P0-2 : APER = coquille vide (25% du score fictif)" | **FAUX** — Éligibilité réelle : parking >= 1500m² outdoor, toiture >= 500m², deadlines 2026/2028 de la loi n°2023-175 | `backend/services/aper_service.py:40-110` |
| "P1-3 : Pas de data dictionary" | **FAUX** — Existe, 1677 lignes | `docs/data-dictionary.md` |
| "Prix fallback 0.15 EUR/kWh" | **PARTIELLEMENT VRAI** — `billing_service.py:43` utilise 0.15 via env var, mais `config/default_prices.py:10` définit 0.18. Deux sources incohérentes | `billing_service.py:43` vs `config/default_prices.py:10` |

### 2.2 Constats RÉELLEMENT confirmés

| Constat initial | Confirmation | Fichier preuve |
| --- | --- | --- |
| "Scénarios achat = facteurs hardcodés" | **CONFIRMÉ** — `price_factor: 1.05/0.95/0.88`, identiques tous sites/périodes | `backend/services/purchase_scenarios_service.py:40,69,100` |
| "Pénalité financière hardcodée" | **CONFIRMÉ** — `BASE_PENALTY_EURO = 7_500` flat, non modulé | `backend/services/compliance_engine.py:57` |
| "Dual compliance engine" | **NUANCÉ** — Le `compliance_coordinator.py` orchestre les 2 chemins en séquence (legacy + RegOps + score A.2). C'est intentionnel, pas un oubli | `backend/services/compliance_coordinator.py:22-78` |
| "ACC/PMO hors scope" | **CONFIRMÉ** — Seul `PMO_ACC` dans enums.py, aucune logique opérationnelle | `backend/models/enums.py` |

### 2.3 Métriques structurelles vérifiées

| Métrique | Valeur exacte |
| --- | --- |
| Fichiers Python backend | 3 326 |
| Modèles SQLAlchemy | 60 fichiers |
| Routes API | 60 fichiers, **462 endpoints** |
| Endpoints par méthode | GET: 262, POST: 153, PATCH: 21, DELETE: 14, PUT: 12 |
| Services backend | 142 fichiers |
| Schemas Pydantic | 11 fichiers |
| Pages frontend | 50 fichiers JSX (32 823 lignes) |
| Composants frontend | 68 fichiers |
| UI design system | 40 fichiers |
| Contexts React | 5 (Auth, Scope, Demo, ExpertMode, ActionDrawer) |
| Models frontend | 19 business logic files |
| Tests backend | 226 fichiers (~4 106 fonctions) |
| Tests frontend | 35 fichiers (Vitest) |
| Tests E2E | 24 specs Playwright |
| Routers montés (main.py) | 73 routers |
| Documentation | 45+ fichiers MD + 8 sous-dossiers |
| Base de données | SQLite 171 MB |
| CI/CD | GitHub Actions quality-gate.yml (lint + test + E2E) |

---

## 3. Périmètre réel du POC actuel

### 3.1 Briques métier — classification vérifiée

| # | Brique | Statut | Service principal | Preuve |
| --- | --- | --- | --- | --- |
| 1 | **Patrimoine / Onboarding** | IMPLÉMENTÉ | `patrimoine_service.py` (1429L), `onboarding_service.py` | CRUD complet, staging pipeline, quality gate, auto-provision bâtiments + obligations + recompute compliance |
| 2 | **Décret Tertiaire / OPERAT** | IMPLÉMENTÉ | `tertiaire_service.py` (912L), `operat_trajectory.py` | Baseline year (`is_reference=True`), `validate_trajectory()` avec delta kwh, statut on_track/off_track, reliability warnings, audit trail |
| 3 | **BACS** | IMPLÉMENTÉ | `bacs_engine.py` (733L) | Putile réel (cascade/réseau/indépendant), TRI exemption, deadlines YAML (290kW→2025, 70kW→2030), audit trace |
| 4 | **APER** | IMPLÉMENTÉ (partiel) | `aper_service.py` (251L) | Éligibilité réelle (parking >= 1500m² outdoor, toiture >= 500m², deadlines 2026/2028). **Manque** : évaluateur RegOps pour intégration dans scoring composite |
| 5 | **Bill Intelligence** | IMPLÉMENTÉ | `billing_service.py` (926L), `billing_engine/` | Shadow billing V2, TURPE 7 CRE réel (`catalog.py` avec taux CRE n°2025-78), 10 règles anomalie, reconstitution composant par composant |
| 6 | **Purchase / Achat** | IMPLÉMENTÉ (facteurs fixes) | `purchase_scenarios_service.py` (183L) | 3 scénarios déterministes (fixe/indexé/spot). Volume estimé depuis factures 12 mois. **price_factor hardcodé** (1.05/0.95/0.88) |
| 7 | **Cockpit / Exécutif** | IMPLÉMENTÉ | `kpi_service.py`, `Cockpit.jsx` (938L) | KPIs centralisés avec cache 5min, score conformité A.2, drill-down vers modules |
| 8 | **Actions / Alertes** | IMPLÉMENTÉ (sync manuelle) | `action_hub_service.py`, `action_workflow_service.py` | 4 sources (compliance, billing, conso, purchase), dedup SHA-256, priorité calculée. Sync via `POST /api/actions/sync` |
| 9 | **Conformité unifiée** | IMPLÉMENTÉ | `compliance_coordinator.py`, `compliance_score_service.py` | 3 étapes synchronisées : (1) legacy snapshots → (2) RegOps evaluate → (3) score unifié A.2 (DT 45% + BACS 30% + APER 25%) |
| 10 | **Flex / Évaluation** | PARTIEL | `flex_assessment_service.py` (229L) | Assessment réel par asset (controllability factors, 4 dimensions). Stockage/valorisation = NON IMPLÉMENTÉ |

### 3.2 Chaînes automatiques vérifiées

| Chaîne | Auto ? | Preuve |
| --- | --- | --- |
| Création site → obligations + compliance | **OUI** | `onboarding_service.py:203-217` → `compliance_coordinator.recompute_site_full()` |
| Import conso → recalcul KPI | **NON** | KPIs on-demand via API, pas de trigger |
| Changement compliance → actions | **NON** | Actions extraites seulement via `sync_actions()` explicite |
| Anomalie facture → action | **NON** | `build_actions_from_billing()` appelé seulement dans `sync_actions()` |
| Scénario achat → action | **NON** | `purchase_actions_engine.py` calcule des actions éphémères, non persistées sans sync |

### 3.3 Sources de vérité identifiées

| Domaine | Source unique | Fichier |
| --- | --- | --- |
| Score conformité composite | `compliance_score_service.py` (lit RegAssessment, fallback snapshots) | `backend/services/compliance_score_service.py` |
| Orchestration conformité | `compliance_coordinator.py` (3 étapes séquentielles) | `backend/services/compliance_coordinator.py` |
| KPIs centralisés | `kpi_service.py` (cache 5min, scope-aware) | `backend/services/kpi_service.py` |
| Trajectoire OPERAT | `operat_trajectory.py` (baseline + delta + statut) | `backend/services/operat_trajectory.py` |
| BACS Putile | `bacs_engine.py` (formule déterministe) | `backend/services/bacs_engine.py` |
| APER éligibilité | `aper_service.py` (seuils surface + deadlines) | `backend/services/aper_service.py` |
| Shadow billing | `billing_service.py` + `billing_engine/` (reconstitution V2) | `backend/services/billing_service.py` |
| TURPE 7 taux | `billing_engine/catalog.py` (CRE n°2025-78) | `backend/services/billing_engine/catalog.py` |
| Scénarios achat | `purchase_scenarios_service.py` (3 scénarios, factors fixes) | `backend/services/purchase_scenarios_service.py` |
| Actions hub | `action_hub_service.py` (4 sources, sync idempotent) | `backend/services/action_hub_service.py` |
| Poids scoring | `regops/config/regs.yaml` (DT 45%, BACS 30%, APER 25%) | `backend/regops/config/regs.yaml` |

---

## 4. Hors scope bloquant actuel

| Brique | Statut | Preuve |
| --- | --- | --- |
| ACC / PMO / Settlement | HORS SCOPE | Seul `PMO_ACC` dans `models/enums.py`. Aucune logique opérationnelle |
| Clés de répartition | HORS SCOPE | NON TROUVÉ dans le repo |
| Valorisation stockage | HORS SCOPE | Référencé dans docs uniquement (`reference_etude_echos_stockage.md`), pas de code opérationnel |
| Prix négatifs / trading | HORS SCOPE | Mentionné dans scénario C texte, pas implémenté |
| Facturation participants | HORS SCOPE | NON TROUVÉ |
| Flexibilité avancée (pilotage, bidding) | HORS SCOPE | `FlexAsset`/`FlexAssessment` = assessment seulement, pas de pilotage |

**Règle** : ces briques ne doivent PAS être comptées comme défauts du POC actuel.

---

## 5. Sources canoniques retenues

### 5.1 Fichiers de référence backend

| Catégorie | Fichier | Lignes | Rôle |
| --- | --- | --- | --- |
| Patrimoine | `services/patrimoine_service.py` | 1429 | CRUD + staging + quality gate |
| Onboarding | `services/onboarding_service.py` | ~250 | Auto-provision + recompute |
| Tertiaire | `services/tertiaire_service.py` | 912 | EFA management, declarations |
| Trajectoire | `services/operat_trajectory.py` | ~280 | Baseline + delta + statut OPERAT |
| BACS | `services/bacs_engine.py` | 733 | Putile, TRI, deadlines |
| APER | `services/aper_service.py` | 251 | Éligibilité parking/toiture |
| Billing | `services/billing_service.py` | 926 | Shadow billing + 10 anomaly rules |
| Billing Engine V2 | `services/billing_engine/engine.py` | ~150 | Reconstitution composant par composant |
| TURPE 7 | `services/billing_engine/catalog.py` | 200+ | Taux CRE officiels |
| Purchase | `services/purchase_scenarios_service.py` | 183 | 3 scénarios, factors fixes |
| KPI | `services/kpi_service.py` | ~300 | Source unique KPIs |
| Compliance score | `services/compliance_score_service.py` | ~200 | Score A.2 unifié |
| Compliance coord. | `services/compliance_coordinator.py` | 78 | Orchestrateur 3 étapes |
| Actions hub | `services/action_hub_service.py` | ~300 | 4 sources sync |
| Compliance legacy | `services/compliance_engine.py` | 1224 | DÉPRÉCIÉ — snapshots Site |

### 5.2 Fichiers de référence frontend

| Catégorie | Fichier | Lignes | Rôle |
| --- | --- | --- | --- |
| Cockpit | `pages/Cockpit.jsx` | 938 | Vue exécutive, KPIs, drill-down |
| Patrimoine | `pages/Patrimoine.jsx` | 2243 | Portefeuille sites, wizard, filtres |
| Site 360 | `pages/Site360.jsx` | 1619 | Détail site mono, 5 onglets |
| Conformité | `pages/ConformitePage.jsx` | 828 | RegOps cockpit, 4 tabs |
| Bill Intel | `pages/BillIntelPage.jsx` | 1246 | Audit facture, anomalies |
| Purchase | `pages/PurchasePage.jsx` | 2024 | Simulateur achat, 5 scénarios |
| Purchase Assistant | `pages/PurchaseAssistantPage.jsx` | 1823 | Wizard 8 étapes |
| Monitoring | `pages/MonitoringPage.jsx` | 3112 | Performance, 4 graphes interactifs |
| Conso Explorer | `pages/ConsumptionExplorerPage.jsx` | 978 | Analyse temporelle, 8 panels |
| Actions | `pages/ActionsPage.jsx` | 1579 | Gestion actions, kanban |

### 5.3 Configuration réglementaire

| Fichier | Contenu |
| --- | --- |
| `regops/config/regs.yaml` | Poids scoring (DT 45%, BACS 30%, APER 25%), seuils, pénalités |
| `regops/rules/decret_tertiaire_operat_v1.yaml` | Règles DT (contrôles, seuils) |
| `regops/rules/decret_bacs_v1.yaml` | Règles BACS (Putile, deadlines) |
| `regops/rules/loi_aper_v1.yaml` | Règles APER (éligibilité) |
| `config/default_prices.py` | Prix fallback (elec 0.18, gaz 0.09 EUR/kWh) |
| `config/tarifs_reglementaires.yaml` | Tarifs réglementés |
| `config/emission_factors.py` | Facteurs CO2 ADEME 2024 |

---

## 6. Cartographie initiale du repo

```text
promeos-poc/
├── backend/                          # FastAPI, port 8001
│   ├── models/          (60 fichiers)     # SQLAlchemy + Enums (876L enums.py)
│   ├── routes/          (60 fichiers)     # 462 endpoints API
│   ├── services/        (142 fichiers)    # Logique métier
│   │   ├── billing_engine/  (6 fichiers)  #   V2 reconstitution TURPE
│   │   ├── demo_seed/       (21 fichiers) #   Pack HELIOS + orchestrateur
│   │   ├── electric_monitoring/ (8 fich.) #   Alertes, benchmark, KPI
│   │   └── ems/             (5 fichiers)  #   Signature, météo, timeseries
│   ├── schemas/         (11 fichiers)     # Pydantic validation
│   ├── regops/          (10 fichiers)     # Engine + YAML rules (3 frameworks)
│   ├── config/          (5 fichiers)      # Prix, émissions, tarifs
│   ├── app/                               # Plugins (bill_intelligence, kb, referential)
│   ├── middleware/                         # Auth JWT, error handler, rate limiting
│   ├── alembic/                           # Migrations (1 migration)
│   ├── tests/           (226 fichiers)    # ~4106 fonctions test
│   ├── data/            (promeos.db)      # SQLite 171 MB
│   └── main.py                            # 73 routers montés, startup events
├── frontend/                         # React + Vite, port 5173
│   └── src/
│       ├── pages/       (50 fichiers)     # 32 823 lignes JSX
│       ├── components/  (68 fichiers)     # Dont billing/, compliance/, conformite/, flex/
│       ├── ui/          (40 fichiers)     # Design system (Card, Badge, KpiCard, Table...)
│       ├── services/    (8 + api/)        # API clients
│       ├── contexts/    (5 fichiers)      # Auth, Scope, Demo, Expert, ActionDrawer
│       ├── models/      (19 fichiers)     # Business logic frontend
│       ├── hooks/       (9 fichiers)      # Custom hooks
│       ├── layout/                        # Shell, sidebar, breadcrumb
│       └── __tests__/   (35 fichiers)     # Vitest
├── e2e/                              # Playwright (24 specs)
│   ├── smoke.spec.js                      # Health checks
│   ├── e7-sprint1-chain.spec.js           # Core chain E2E
│   ├── golden-demo.spec.js                # Full demo journey
│   └── playwright.config.js               # 30s timeout, 1 retry
├── docs/                             # 45+ fichiers MD
│   ├── data-dictionary.md (1677L)         # KPIs, formules, sources
│   ├── api-contracts.md                   # Signatures API
│   ├── KPI_FORMELS.md                     # Formules KPI
│   └── audits/                            # ← ce fichier
├── tools/playwright/                # Scripts Playwright manuels et audits visuels
├── artifacts/audits/                # Captures et archives Playwright générées
└── .github/workflows/
    └── quality-gate.yml              # Lint + Test + E2E (3 étages)
```

---

## 7. Risques majeurs RÉELLEMENT confirmés

### P0 — Bloquant crédibilité

| # | Risque | Sévérité | Fichier preuve | Impact |
| --- | --- | --- | --- | --- |
| R1 | **Déconnexion KPI cockpit ↔ trajectoire OPERAT** | P0 | `kpi_service.py:218` lit `AVG(Site.avancement_decret_pct)` au lieu d'appeler `operat_trajectory.validate_trajectory()` | Un expert OPERAT verra que le KPI cockpit ne reflète pas la trajectoire réelle calculée par EFA |

### P1 — Crédibilité marché

| # | Risque | Sévérité | Fichier preuve | Impact |
| --- | --- | --- | --- | --- |
| R2 | **Scénarios achat = price_factor fixe** | P1 | `purchase_scenarios_service.py:160` — 1.05/0.95/0.88 | Écart fixe→indexé TOUJOURS 10%. Un DAF détecte immédiatement |
| R3 | **APER sans évaluateur RegOps** | P1 | `aper_service.py` non intégré dans `regops/engine.py` | APER pèse 25% du score composite mais le scoring APER n'est pas dans l'évaluateur RegOps |
| R4 | **Double source prix par défaut** | P1 | `billing_service.py:43` (0.15 via env) vs `config/default_prices.py:10` (0.18) | Shadow billing incohérent selon le chemin de code emprunté |
| R5 | **Chaîne données→KPI non automatique** | P1 | Import conso ≠ trigger recalcul KPI. `kpi_service.py` = on-demand | KPI cockpit peut être stale après import sans navigation |
| R6 | **Chaîne achat→actions non automatique** | P1 | `purchase_actions_engine.py` produit des actions éphémères | Recommandations achat jamais tracées dans le centre d'actions sans sync explicite |

### P2 — Premium / différenciation

| # | Risque | Sévérité | Fichier preuve | Impact |
| --- | --- | --- | --- | --- |
| R7 | **Pénalité financière = constante 7500 EUR** | P2 | `compliance_engine.py:57` | Non modulé surface/type, label "risque théorique maximum" absent |
| R8 | **Legacy compliance_engine toujours actif** | P2 | `compliance_coordinator.py:37-39` | Étape 1 du coordinateur, pas un oubli mais dette technique intentionnelle |

---

## 8. Ordre recommandé des audits détaillés

| Étape | Audit | Périmètre | Pourquoi dans cet ordre |
| --- | --- | --- | --- |
| **1** | **Fil conducteur** | patrimoine → données → KPI → conformité → facture → achat → actions | Le risque #1 = déconnexions. Doit être audité en premier |
| **2** | **Règles métier & conformité** | DT/OPERAT trajectory, BACS Putile, APER éligibilité, scoring A.2, pénalités | Vérifier que les formules réelles sont justes |
| **3** | **Bill Intelligence & Achat** | Shadow billing V2, TURPE 7 catalog, 10 anomaly rules, scénarios, prix | Crédibilité des chiffres financiers |
| **4** | **UX/UI sévère** | Cockpit, patrimoine, conformité, facture, achat, actions, multi-site | Playwright agent + analyse visuelle |
| **5** | **Front technique** | Composants, design system, états, duplication, responsive, performance | Code quality, robustesse |
| **6** | **Back/API technique** | Validation, erreurs, contrats, pagination, sécurité minimale | Solidité technique |
| **7** | **Données & modèle** | Hiérarchie, unités, périodes, agrégations, data dictionary | Cohérence modèle de données |
| **8** | **Tests & QA** | Couverture, qualité, E2E chains, régression | Fiabilité base de tests |

---

## 9. Agents / outils / MCP recommandés

| Agent | Rôle | Étapes concernées |
| --- | --- | --- |
| **Explore (subagent)** | Cartographie code, trace data flows, vérifie implémentations | 1, 2, 3, 6, 7 |
| **Playwright MCP** | Screenshots UI, audit visuel, boutons morts, responsive | 4 |
| **Grep/Read (directs)** | Vérification fichier par fichier des formules, constantes, fallbacks | 2, 3, 6 |
| **Plan (subagent)** | Synthèse et priorisation par étape | Toutes |
| **Audit-agent.mjs** | Script Playwright existant (27 pages, 8 interactions) | 4 |
| **context7 MCP** | Documentation libs externes si nécessaire | 5, 6 |

### Outils du repo existants à exploiter

| Outil | Fichier | Usage |
| --- | --- | --- |
| Agent Playwright d'audit | `tools/playwright/audit-agent.mjs` | 27 pages canoniques, capture auto |
| Quality gate CI | `.github/workflows/quality-gate.yml` | Lint + test + E2E automatisés |
| Seed démo | `python -m services.demo_seed --pack helios --size S --reset` | Données réalistes pour tests |
| Tests backend | `cd backend && python -m pytest tests/ -v` | 226 fichiers, ~4106 fonctions |
| Tests frontend | `cd frontend && npx vitest run` | 35 fichiers Vitest |
| E2E | `cd e2e && npx playwright test` | 24 specs Playwright |

---

## 10. Convention de preuve et de traçabilité

### Format de constat

Chaque constat d'audit DOIT contenir :

```text
[ID]     : R1, R2, R3...
[Fichier]: chemin exact (ex: backend/services/kpi_service.py:218)
[Code]   : extrait du code source si pertinent
[Verdict]: IMPLÉMENTÉ | PARTIEL | COSMÉTIQUE | PLACEHOLDER | NON TROUVÉ | HORS SCOPE
[Impact] : utilisateur | métier | technique | réglementaire
[Sévérité]: P0 (bloquant) | P1 (crédibilité) | P2 (premium)
```

### Classification des constats

| Tag | Signification |
| --- | --- |
| **NON TROUVÉ** | Aucune trace dans le repo |
| **IMPLICITE MAIS NON FIABILISÉ** | Code existe mais non testé, documenté ou relié |
| **COSMÉTIQUE SEULEMENT** | UI affiche mais pas de logique backend réelle |
| **PLACEHOLDER** | Structure existe mais valeurs hardcodées/mockées |
| **HORS SCOPE ACTUEL** | Brique future, pas un défaut du POC |
| **À RISQUE CRÉDIBILITÉ** | Fonctionnel mais un expert détecterait la faiblesse |
| **À RISQUE RÉGLEMENTAIRE** | Calcul ou règle potentiellement faux |
| **À RISQUE UX** | Utilisateur peut être induit en erreur |

### Règle d'or

> Chaque constat négatif doit être **prouvé par un fichier et une ligne**.
> Chaque constat positif doit être **prouvé par un fichier et une ligne**.
> Aucun jugement "d'impression" n'est accepté.

---

## 11. Definition of Done de l'étape 0

| Critère | Statut |
| --- | --- |
| Cartographie structurelle avec comptages exacts | FAIT |
| Vérification fichier par fichier des 10 briques métier | FAIT |
| Correction des erreurs factuelles du baseline initial | FAIT (3 P0 corrigés) |
| Classification IMPLÉMENTÉ/PARTIEL/COSMÉTIQUE/PLACEHOLDER/HORS SCOPE | FAIT |
| Identification des risques RÉELLEMENT confirmés | FAIT (1 P0, 5 P1, 2 P2) |
| Identification des déconnexions entre briques | FAIT (5 chaînes vérifiées) |
| Sources canoniques listées avec fichiers | FAIT |
| Hors scope bloquant explicitement défini | FAIT (6 briques) |
| Ordre des audits détaillés défini | FAIT (8 étapes) |
| Convention de preuve formalisée | FAIT |
| Aucune modification du repo appliquée | FAIT |

---

*Cadrage établi le 2026-03-23. Prêt pour l'étape 1 : audit du fil conducteur.*
