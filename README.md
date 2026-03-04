# PROMEOS POC

Pilotage reglementaire et energetique multi-sites B2B France -- conformite, usages, veille, en un seul outil.

---

## Table des matieres

1. [TL;DR](#tldr)
2. [Probleme client](#probleme-client)
3. [Ce que le POC demontre](#ce-que-le-poc-demontre)
4. [Demo en 2 minutes](#demo-en-2-minutes)
5. [Prerequis](#prerequis)
6. [Lancer le projet](#lancer-le-projet)
7. [Donnees de demo / Seed / Reset DB](#donnees-de-demo)
8. [Architecture](#architecture)
9. [Modele de donnees](#modele-de-donnees)
10. [API Quick View](#api-quick-view)
11. [Pages UI](#pages-ui)
12. [What's in / What's out](#whats-in--whats-out)
13. [Roadmap 30 jours](#roadmap-30-jours)
14. [Troubleshooting](#troubleshooting)
15. [Contributing / License / Disclaimer](#contributing)

---

> **Statut du POC**
>
> | Brique | Etat |
> |--------|------|
> | Backend API (~165 endpoints) | Stable |
> | Frontend React (42+ pages) | Stable |
> | Moteur conformite (Decret Tertiaire, BACS) | Stable |
> | RegOps 4 reglementations (Tertiaire, BACS, APER, CEE P6) | Stable |
> | Knowledge Base (12 items YAML + FTS5) | Stable |
> | Connecteurs externes (RTE, PVGIS live ; Enedis, Meteo stubs) | Partiel |
> | Watchers veille reglementaire (Legifrance, CRE, RTE RSS) | Stable |
> | Couche IA (5 agents, mode stub sans cle API) | Stable |
> | Authentification / IAM (JWT + 11 roles + scopes) | Stable |
> | Patrimoine (import HELIOS, anomalies, impact, cockpit portfolio) | Stable -- V58-V63 |
> | Facturation (org-scoping, PDF import, shadow billing, Action Center) | Stable -- V66 |
> | Timeline & couverture facturation (periods, coverage engine, /billing page) | Stable -- V67 |
> | Billing Unified (shadow V2 TURPE/CSPE, R13/R14, deep-links, seed 36 mois) | Stable -- V68 |
> | Actions Console (gestion centralisee, filtres, batch, detail drawer) | Stable -- V69 |
> | Performance V2 (4 sections, plan d'action, expert mode, route registry) | Stable -- V70 |
> | Demo Seed hardening (INSERT OR IGNORE, UniqueConstraint, 60 mois, 8 pytest) | Stable -- V71 |
> | Achat Energie V2 (scope lock, autosave, volume toggle, confidence badges, cockpit) | Stable -- V72 |
> | Achat Audit (scope unlock, skipSiteHeader, tab deep-link, assistant CTA) | Stable -- V73 |
> | Tarif Heures Solaires (blocs horaires, badges, effort score, cross-brique CTAs) | Stable -- V74-V82 |
> | Performance cross-brique (5 KPI cards, THS adoption/gain/risque, CTA Simuler) | Stable -- V79 |
> | Assistant Achat (8 etapes, deep-link step+offer, 6 offres demo, highlight) | Stable -- V81 |
> | Demo HELIOS canonique (Casino supprime, seed deterministe 5 sites/7 bat./60 mois) | Stable -- V83 |
> | Consumption Context V0 — Usages & Horaires (heatmap 7x24, profil, behavior_score) | Stable -- V84 |
> | ScheduleEditor interactif (edition horaires + recalcul anomalies inline) | Stable -- V84 |
> | Portfolio Behavior Summary (classement sites par score comportemental) | Stable -- V84 |
> | UX Overlays fixes (tooltips vides, ScopeSwitcher portal z-index) | Stable -- fix/ux-overlays |
> | Demo Seed V86 (730j horaire + 30j 15min + meteo 5 sites) | Stable -- V86 |
> | Demo Seed V87 (BACS assets, Consumption Targets, EMS Views, 60 invoices) | Stable -- V87 |
> | Quality Gate V88 — P0/P1/P2 (overlays, lint 0, memo, dead code) | Stable -- V88 |
> | Evidence Drawer V0 — "Pourquoi ce chiffre ?" (Cockpit + Explorer) | Stable -- V89 |
> | Action Engine universel + Evidence (drawer, close gate, evidence_required) | Stable -- V90 |
> | Dossier & Runbook (export HTML, week view, closeability badges) | Stable -- V90 |
> | Data Readiness Gate polish (popover, confiance, trend, snapshots) | Stable -- V90 |
> | Demo Coherence (donnees deterministes, 32 tests cross-file) | Stable -- V90 |
> | QA Audit V91 — Golden Contract HELIOS (4 statuts, single-source todos, 38 tests, fix Unicode) | Stable -- V91 |
> | Conformite UX Upgrade (Guided Mode 7 etapes, NBA hero card, Donnees KPIs, Expert mode) | Stable -- V92 |
> | V23 Sprint Analyse (auth guards, motor stability, tab extraction, double-fetch, UX refactor) | Stable -- V23 |
> | V23 Audit (2 passes, 60 issues, check_site_access IDOR fixes, CO2E centralized, a11y) | Stable -- V23 |
> | Audit Marche complet (195 issues, Number("") fix, stale closures, file size validation, parseInt radix) | Stable -- V93 |
> | Site Scope Filter global (ActionPlan, ActionsPage, Notifications, OPERAT Dashboard, API site_id) | Stable -- V93 |
> | Performance FR labels (10 snake_case ALERT_TYPE_LABELS, WASTE_TYPES fix, null guards) | Stable -- V93 |
> | V95 Patrimoine World-Class Closure (real API anomalies, import legacy+hidden, backend hardening) | Stable -- V95 |
> | V96 Patrimoine Unique Monde — Matrice Facture/Payeur/CC, Reconciliation 3 voies, Contrats achats-ready | Stable -- V96 |
> | V97 Resolution Engine — 1-click fix, audit trail, Portfolio Reconciliation triage, Evidence Pack CSV | Stable -- V97 |
> | V98 Grand Public Guidance Layer — Simple/Expert mode, FR translations, Next Best Action, Evidence 1-page | Stable -- V98 |
> | Contract Radar V99 — Tableau de bord renouvellements contrats, scoring risque, timeline echéances | Stable -- V99 |
> | Offer Pricing V100 — Moteur pricing offres fournisseurs, comparaison grilles, reconciliation factures | Stable -- V100 |
> | Segmentation V101 — Next Best Step moteur d'action, action creation depuis recommandations, onboarding pilote | Stable -- V101 |
> | V103-V106 Remediation (datetime TZ, rate limiting, Pydantic v2, DB health, lifespan) | Stable -- V106 |
> | V107 Demo World-Class Realism (meteo AR(1) par ville, conso ADEME, gaz DJU, 15-min 365j, anomalies diversifiees, usages) | Stable -- V107 |
> | V108 Demo Completeness (30 snapshots monitoring, 20 notifications, TOU HP/HC, PaymentRule, ReconciliationFixLog, 65 tests) | Stable -- V108 |
> | Suite de tests automatises | **4 257 frontend + 2 400+ backend, 0 regression** |

> **Disclaimer**
>
> Ce depot est un **proof-of-concept** (POC). Il n'est pas prevu pour la production :
> pas de rate-limiting, SQLite en mono-fichier, CORS ouvert.
> Authentification IAM implementee (JWT + scopes hierarchiques + 11 roles metier).
> Les donnees de demo sont synthetiques (5 sites HELIOS, 10 personas IAM).

---

<a id="tldr"></a>
## TL;DR

- **Backend FastAPI** avec ~150 endpoints, 20+ modeles SQLAlchemy, 4 moteurs de regles reglementaires, 5 connecteurs de donnees, 4 watchers de veille, 5 agents IA (stub), module Patrimoine complet (import HELIOS, anomalies, impact reglementaire, cockpit portfolio V60-V63), module Facturation production-grade (org-scoping, PDF EDF/Engie, shadow billing V2 TURPE/CSPE/TICGN, 14 regles d'anomalie, bridge Action Center), timeline & couverture facturation (periods, coverage engine V67), Billing Unified (InvoiceNormalized, deep-links bidirectionnels, seed 36 mois HELIOS V68), demo seed hardened (V71), moteur Achat Energie (4 strategies incluant Tarif Heures Solaires avec 6 blocs horaires, effort score, report_pct, green bonus V74-V75).
- **Frontend React 18 + Tailwind + Vite** avec 22+ pages : Dashboard, Cockpit Executif, Patrimoine (heatmap + portfolio), Detail Site, Plan d'action, RegOps, Conso & Usages, Usages & Horaires (Consumption Context V0 : heatmap 7x24, profil journee, behavior_score, ScheduleEditor inline V84), Tertiaire OPERAT, IAM Admin, Import, KB Explorer, Veille Reglementaire, Facturation (BillIntel deep-links + BillingTimeline + CoverageBar), Actions Console (V69), Performance V2 (5 KPI cards dont THS, expert mode, route registry V70-V79), Achat Energie V2 (4 strategies, "Option Tarif Heures Solaires" structuree avec badges Budget/Risque/Effort/Sans penalite, creneaux ete/hiver, 7 CTAs cross-briques, deep-link assistant V72-V82), Assistant Achat 8 etapes (deep-link step+offer, 6 offres demo, highlight V81).
- **Demo HELIOS canonique** : Groupe Casino supprime, demo unifiee Groupe HELIOS (3 entites, 5 sites, 7 batiments — bureaux, industrie, hotel, ecole, seed deterministe RNG=42, 60 mois de readings V83).
- **Demo Seed V86-V87** : 730 jours de lectures horaires + 30 jours 15min + meteo 5 sites (V86). BACS assets/systemes/assessments/inspections, ConsumptionTargets (yearly+monthly 2024-2026), EMS Explorer vues pre-configurees, 60 factures (V87).
- **Demo World-Class V107-V108** : Meteo realiste par ville (normales Meteo-France, AR(1) phi=0.7, 12 villes), consommation calibree ADEME (170 kWh/m2 bureau, 280 hotel, 120 entrepot, 110 ecole), gaz correle DJU, 365 jours 15-min avec cycling CVC, anomalies diversifiees (5 types par site), 30 usages, 30 snapshots monitoring mensuels, 20 notifications multi-sources, 5 grilles TOU HP/HC, 8 regles de paiement, 4 traces reconciliation. **65 tests, seed 41s.**
- **Quality Gate V88** — ESLint zero warnings (`--max-warnings=0`, 211→0), `React.memo` + `useMemo` sur charts lourds (HeatmapChart O(1) Map lookup, PortfolioPanel, ProfileHeatmapTab), shared `ui/Badge` dans SiteDetail/Site360, dead code supprime (Cockpit2MinPage), tooltips consolides (TooltipPortal + InfoTip), z-index normalise (Modal/Drawer z-200), `useActivationData` hook dedup.
- **Evidence Drawer V0 (V89)** — "Pourquoi ce chiffre ?" : modele Evidence (CONFIDENCE_CFG, SOURCE_KIND, buildEvidence), EvidenceDrawer generique (Drawer z-200, 5 sections : Sources/Methode/Hypotheses/Liens/Dernier calcul), 4 fixtures factory (conformite, risque, kWh, CO2e). Integration Cockpit (Conformite + Risque KPIs) et Explorer (kWh total + CO2e). 32 source-guard tests, 0 regression.
- **Action Engine universel V90** : `CreateActionDrawer.jsx` (drawer centralisé, evidence_required toggle, auto-deadline), `ActionDrawerContext.jsx` (`openActionDrawer()` depuis n'importe où), `HealthSummary.jsx` (CTA "+ Action" sur readiness reasons), close gate generique `evidence_required` backend. 13 tests.
- **Dossier & Runbook V90** : `dossierModel.js` (buildDossier, groupActionsByWeek, computeCloseabilityBadge), `DossierPrintView.jsx` (export HTML imprimable depuis 3 sources : OPERAT EFA, Conformite obligation, Billing anomalie), WeekView dans ActionsPage (4 buckets temporels + badges closeabilite). 23 tests.
- **Data Readiness Gate polish V90** : DataReadinessBadge popover premium (niveau + 3 raisons + CTA + trend), `computeDataConfidence` (Elevee/Moyenne/Faible) dans PurchasePage, snapshots scopes (org/pf/site) avec retention 14j, `computeReadinessTrend` (delta dimensions OK). 21 tests.
- **Demo Coherence V90** : donnees 100% deterministes (zero `Math.random`), mockTodos/Actions/Obligations alignes sur les 5 sites HELIOS reels, Toulouse `non_conforme` (couverture complete des 4 statuts), 32 tests de coherence cross-fichiers (`demoCoherence.test.js`).
- **Evidence Rules V90** : `evidenceRules.js` (computeEvidenceRequirement, buildSourceDeepLink, SOURCE_LABELS_FR), close errors structures, idempotency UX. 33 tests.
- **Billing Health V90** : `billingHealthModel.js` (buildBillingWatchlist, computeBillingHealthState, health trend snapshots). 15 tests.
- **QA Audit V91 — Golden Contract HELIOS** : Nice passe `a_risque` (4 statuts exerces : conforme/non_conforme/en_cours/a_risque), mockTodos derives via `SITE[id].nom` (zero noms hardcodes), fix Unicode `\u00e9` → `é` sur 6 fichiers (ActivationPage, ImpactDecisionPanel, ScheduleEditor, etc.), 6 tests single-source-of-truth (import `./sites`, no Math.random, no Date.now, todos derived). 38 tests demoCoherence pass.
- **Contract Radar V99** : tableau de bord renouvellements contrats (scoring risque, timeline echeances, 4 statuts contrat, alertes expiration 90j), endpoint `/api/contracts-radar/dashboard`, 12 tests.
- **Offer Pricing V100** : moteur pricing offres fournisseurs (comparaison grilles tarifaires, simulation gain/perte, reconciliation factures/offres), endpoint `/api/offer-pricing/*`, 8 tests.
- **Segmentation V101** : Next Best Step moteur d'action deterministe (cascade priorite : confidence < 50 → questions, contrats expirants → renouvellement, reconciliation fail → debloquer), creation actions depuis recommandations (idempotent, SHA-256), 3 endpoints (`/api/segmentation/next-step`, `/actions/from-recommendation`, `/actions/from-next-step`), SegmentationWidget V101 (Next Step card + top 2 recs + CTA modal/route), onboarding pilote (PatrimoineWizard → recomputeSegmentation, ContractRadarPage nudge banner). 17 tests V101 + 8 bug fixes V100.
- **3 975 frontend + 2 400+ backend = 6 375+ tests, 0 regression** — pytest backend + vitest frontend, seed HELIOS 5 sites + 60 mois + 10 personas IAM en une commande, demo operationnelle en 2 minutes.

---

<a id="probleme-client"></a>
## Probleme client

Un gestionnaire B2B multi-sites en France (retail, bureaux, industrie) doit :

1. **Suivre la conformite** de chaque site sur 4 cadres reglementaires simultanement (Decret Tertiaire / OPERAT, BACS, APER, CEE P6) avec des echeances, preuves, et sanctions financieres.
2. **Comprendre les usages energetiques** de chaque site (profils, anomalies nuit/week-end, ratios kWh/m2) a partir de donnees de comptage.
3. **Reagir aux evolutions reglementaires** (textes Legifrance, decisions CRE, publications RTE) sans veille manuelle.
4. **Consolider le portefeuille** en un cockpit executif : score global, sites a risque, prochaines echeances, plan d'action priorise.

PROMEOS POC demontre une reponse technique a ces 4 besoins.

---

<a id="ce-que-le-poc-demontre"></a>
## Ce que le POC demontre

| Brique | Contenu repo | Endpoints cles |
|--------|-------------|----------------|
| **Conformite deterministe** | 4 moteurs de regles YAML (`backend/regops/rules/`) evaluant 120 sites | `GET /api/regops/site/{id}` |
| **RegAssessment cache** | Evaluations persistees + scoring composite (severite x urgence x confiance) | `GET /api/regops/dashboard` |
| **Knowledge Base** | 12 items YAML (archetypes, regles anomalie, recommendations) + SQLite FTS5 | `POST /api/kb/search`, `POST /api/kb/apply` |
| **Usages & Analytics** | Detection d'anomalies, recommendations ICE-scored | `POST /api/energy/analysis/run` |
| **Connecteurs** | RTE eCO2mix et PVGIS fonctionnels (API publiques, sans cle) | `POST /api/connectors/{name}/test` |
| **Veille reglementaire** | 3 watchers RSS (Legifrance, CRE, RTE) + deduplication hash | `GET /api/watchers/events` |
| **IA guardee** | 5 agents (explainer, recommender, data quality, exec brief, reg change) en mode stub | `GET /api/ai/site/{id}/explain` |
| **Job queue async** | `JobOutbox` + worker avec cascade (compteur -> site -> entite -> org) | `POST /api/regops/recompute` |
| **Cockpit executif** | KPIs portefeuille, worst-sites, prochaines echeances | `GET /api/cockpit` |
| **Mode demo** | Activation/desactivation avec donnees masquees | `POST /api/demo/enable` |

---

<a id="demo-en-2-minutes"></a>
## Demo en 2 minutes

> Prerequis : backend et frontend demarres (voir [Lancer le projet](#lancer-le-projet)).

### Etape 1 -- Dashboard (30s)

1. Ouvrir `http://localhost:5173/`
2. Le **Dashboard** affiche 120 sites avec statuts conformite (conforme / a risque / non conforme).
3. Cliquer sur un site pour voir son **detail** : obligations, evidences, score.

### Etape 2 -- Cockpit Executif (30s)

1. Cliquer **Cockpit Executif** dans la navbar.
2. KPIs portefeuille : score moyen, nombre de sites non conformes, risque financier total, prochaine echeance.
3. Repartition par statut (graphique Recharts).

### Etape 3 -- RegOps d'un site (30s)

1. Depuis le Dashboard, cliquer un site, puis dans l'URL remplacer `/sites/1` par `/regops/1`.
2. L'ecran **RegOps** affiche :
   - Findings deterministes (Tertiaire, BACS, APER, CEE P6) avec severite, deadline, confiance.
   - Score composite.
   - Actions recommandees avec priorite.

### Etape 4 -- Conso & Usages (15s)

1. Cliquer **Conso & Usages** dans la navbar.
2. Profils de consommation, detection d'anomalies, recommendations ICE-scored.

### Etape 5 -- Veille Reglementaire (15s)

1. Cliquer **Veille Reglementaire** dans la navbar.
2. 4 evenements reglementaires affiches (issus du seed), avec titre, source, date, snippet.
3. Possibilite de marquer un evenement comme "revu".

### API Swagger

- Ouvrir `http://localhost:8001/docs` pour explorer les ~160 endpoints interactivement.

---

<a id="prerequis"></a>
## Prerequis

| Outil | Version testee | Notes |
|-------|----------------|-------|
| Python | 3.12+ | 3.14 utilise en dev |
| Node.js | 18+ | npm inclus |
| Git | 2.x | |
| OS | Windows 10/11 | Developpe sur Windows (PowerShell / Git Bash) |

---

<a id="lancer-le-projet"></a>
## Lancer le projet

### Backend

```bash
# Depuis la racine du projet

# Creer le virtualenv a la racine (une seule fois)
python -m venv .venv

# Activer le virtualenv
# Windows PowerShell :
.\.venv\Scripts\Activate.ps1
# Windows CMD :
.venv\Scripts\activate.bat
# Linux/macOS :
source .venv/bin/activate

# Installer les dependances
pip install -r backend/requirements.txt

# Copier la config (une seule fois)
cd backend
copy .env.example .env
# Linux/macOS : cp .env.example .env

# Initialiser la DB + seed 120 sites
python scripts/init_database.py
python scripts/seed_data.py

# Lancer le serveur (port 8001)
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Le backend est pret quand vous voyez :

```
INFO:     Uvicorn running on http://127.0.0.1:8001
```

Verifier : `http://localhost:8001/api/health` doit retourner `{"ok":true}`.

### Frontend

```bash
# Depuis la racine du projet (nouveau terminal)
cd frontend

# Installer les dependances (une seule fois)
npm install

# Lancer le dev server (port 5173)
npm run dev
```

Le frontend est pret quand vous voyez :
```
VITE v5.x.x  ready in XXXms
Local: http://localhost:5173/
```

Le proxy Vite redirige automatiquement `/api/*` vers `http://localhost:8001`.

### Variables d'environnement

Le fichier `backend/.env.example` contient toutes les variables :

| Variable | Defaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | `sqlite:///./data/promeos.db` | Chemin de la DB SQLite |
| `API_HOST` | `127.0.0.1` | Host du backend |
| `API_PORT` | `8001` | Port du backend |
| `FRONTEND_URL` | `http://localhost:5173` | URL du frontend (CORS) |
| `SEED_NB_SITES` | `120` | Nombre de sites generes par le seed |
| `DEBUG` | `True` | Mode debug |
| `SECRET_KEY` | `your-secret-key...` | Cle JWT legacy |
| `PROMEOS_DEMO_MODE` | `true` | Mode demo (auth optionnelle). `false` = JWT requis |
| `PROMEOS_JWT_SECRET` | `dev-secret-change-me` | Secret HMAC pour signer les JWT |

Pour activer l'IA (optionnel) : ajouter `AI_API_KEY=sk-ant-...` dans `.env`.
Sans cle, les agents IA fonctionnent en **mode stub** (reponse generique).

---

<a id="donnees-de-demo"></a>
## Donnees de demo / Seed / Reset DB

### Seed complet

```bash
cd backend
python scripts/seed_data.py
```

Genere (pack HELIOS) :
- 1 organisation + 3 entites juridiques + 3 portefeuilles
- 5 sites (bureaux Paris 3500m2, bureau Lyon 1200m2, entrepot Toulouse 6000m2, hotel Nice 4000m2, ecole Marseille 2800m2)
- 7 batiments avec puissance CVC realiste
- 8 compteurs (5 elec + 3 gaz)
- ~87 500 lectures horaires elec (730j x 5 sites x 24h) calibrees ADEME
- ~131 400 lectures 15min (365j x 5 sites x 72 slots) avec cycling CVC
- ~2 190 lectures gaz journalieres (730j x 3 sites) correlees DJU
- ~300 lectures mensuelles (60 mois x 5 sites)
- 3 650 releves meteo realistes (730j x 5 villes, normales Meteo-France, AR(1))
- 30 usages par batiment (CVC, eclairage, IT, process, autres)
- Anomalies diversifiees (CVC drift, eclairage oublie, pic canicule, panne, transition saison)
- 30 snapshots monitoring (6 mensuels x 5 sites) + 21 alertes + 91 insights
- 20 notifications (4 sources : billing, consumption, compliance, action_hub)
- 5 grilles TOU HP/HC (EDF standard TURPE)
- 8 regles de paiement (portefeuille + site) + 4 traces reconciliation
- 5 BacsAssets + 9 BacsCvcSystems + 5 BacsAssessments + 3 BacsInspections
- 195 ConsumptionTargets (5 sites x 3 ans x 13 = yearly+12 monthly)
- 4 EmsSavedViews + 2 EmsCollections pre-configurees
- 8 contrats energie + 60 factures + lignes + insights anomalies
- 15 actions (compliance, consumption, billing)

### Reset DB

```bash
cd backend
# Le seed drop + recreate toutes les tables automatiquement
python scripts/seed_data.py
```

### Seed Knowledge Base (DB separee)

```bash
cd backend
python scripts/kb_seed_import.py
# Importe les 12 items YAML dans backend/data/kb.db
```

### Valider la KB

```bash
cd backend
python scripts/kb_validate.py --strict
# Verifie les 12 items YAML contre la taxonomie
```

### Smoke test complet

```bash
cd backend
python scripts/kb_smoke.py
# 14 tests : YAML, DB schema, FTS index, apply engine, golden contexts
```

---

<a id="architecture"></a>
## Architecture

```
                          +-------------------+
                          |   Frontend React  |
                          |  localhost:5173   |
                          | 39+ pages + Vite  |
                          +--------+----------+
                                   |
                            proxy /api/*
                                   |
                          +--------v----------+
                          |   FastAPI Backend  |
                          |  localhost:8001   |
                          |  ~160 endpoints   |
                          +--------+----------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
     +--------v------+   +--------v------+   +--------v--------+
     |  RegOps Core  |   |  KB Engine    |   |  Connectors     |
     |  4 regles     |   |  FTS5 search  |   |  RTE, PVGIS,    |
     |  YAML config  |   |  apply()      |   |  Enedis (stub)  |
     +--------+------+   +--------+------+   +--------+--------+
              |                    |                    |
     +--------v------+   +--------v------+   +--------v--------+
     |  SQLAlchemy   |   |  SQLite kb.db |   |  Watchers       |
     |  20+ modeles  |   |  12 items     |   |  Legifrance,    |
     |  promeos.db   |   |               |   |  CRE, RTE RSS   |
     +---------------+   +---------------+   +-----------------+
              |
     +--------v--------+
     |  AI Layer       |
     |  5 agents       |
     |  mode stub/live |
     +-----------------+
```

### Stack technique

| Couche | Technologie |
|--------|-------------|
| Frontend | React 18.2 + Tailwind CSS 4 + Vite 5 + Recharts 3 |
| Backend | FastAPI 0.104 + Uvicorn 0.24 |
| ORM | SQLAlchemy 2.0 |
| DB principale | SQLite (promeos.db) |
| DB Knowledge Base | SQLite + FTS5 (kb.db) |
| Validation | Pydantic 2.5 |
| Tests | pytest 7.4 + vitest 4.0 |

---

<a id="modele-de-donnees"></a>
## Modele de donnees

Objets principaux (SQLAlchemy, fichier `backend/models/`) :

```
Organisation (1)
  +-- EntiteJuridique (1)
        +-- Portefeuille (3)
              +-- Site (120)
                    |-- Batiment (cvc_power_kw, surface_m2)
                    |-- Compteur (meter_id, energy_vector)
                    |     +-- Consommation (timestamp, valeur, cout_euro)
                    |-- Obligation (type: DECRET_TERTIAIRE | BACS | APER)
                    |-- Evidence (type: AUDIT | CERTIFICAT | ATTESTATION_BACS | ...)
                    |-- Alerte (severite: INFO | WARNING | CRITICAL)
                    |-- RegAssessment (compliance_score, findings_json, top_actions_json)
                    +-- Usage (type: BUREAUX | PROCESS | FROID | CVC | ...)

DataPoint         -- Donnees externes horodatees (CO2, meteo, PV)
RegSourceEvent    -- Evenements de veille reglementaire (hash dedup)
JobOutbox         -- File d'attente async (recompute, sync, watcher, IA)
AiInsight         -- Sorties des agents IA (EXPLAIN | SUGGEST | EXEC_BRIEF | ...)
ActionItem        -- Actions centralisees (source: MANUAL | INSIGHT | BILLING | COMPLIANCE)

EnergyContract    -- Contrat fournisseur energie (site, type, dates, prix ref)
EnergyInvoice     -- Facture energie (CSV ou PDF, status, raw_json evidence)
  +-- EnergyInvoiceLine  -- Lignes HT/TVA/TAXES/ENERGY
BillingInsight    -- Anomalie de facturation (type, severity, estimated_loss_eur)
BillingImportBatch -- Batch d'import (CSV ou PDF, statut, nb lignes)
```

Champs cles du Site :
- `tertiaire_area_m2`, `parking_area_m2`, `parking_type`, `roof_area_m2` (APER)
- `operat_status` (NOT_STARTED | IN_PROGRESS | SUBMITTED | VERIFIED)
- `annual_kwh_total`, `is_multi_occupied`
- `statut_decret_tertiaire`, `statut_bacs` (snapshots calcules)

---

<a id="api-quick-view"></a>
## API Quick View

~160 endpoints au total. Selection des plus importants :

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/sites` | Liste des 120 sites avec statuts conformite |
| `GET` | `/api/sites/{id}/compliance` | Detail conformite d'un site |
| `GET` | `/api/cockpit` | KPIs portefeuille (score, repartition, risque) |
| `GET` | `/api/regops/site/{id}` | Evaluation RegOps live (4 reglementations) |
| `GET` | `/api/regops/dashboard` | Dashboard RegOps agreges |
| `POST` | `/api/kb/search` | Recherche full-text dans la Knowledge Base |
| `POST` | `/api/kb/apply` | Appliquer les regles KB a un contexte site |
| `POST` | `/api/energy/analysis/run` | Lancer une analyse d'usages energetiques |
| `GET` | `/api/connectors/list` | Liste des connecteurs et leur statut |
| `GET` | `/api/watchers/events` | Evenements de veille reglementaire |
| `GET` | `/api/ai/site/{id}/explain` | Brief IA sur un site (stub sans API key) |
| `GET` | `/api/patrimoine/sites` | Liste sites patrimoine (anomalies, score, framework) |
| `GET` | `/api/patrimoine/portfolio-summary` | Cockpit portfolio : risque global, top sites, trend |
| `POST` | `/api/patrimoine/staging/upload` | Import HELIOS CSV/XLSX — pipeline staging |
| `POST` | `/api/patrimoine/staging/{id}/activate` | Activation staging → entites reelles |
| `GET` | `/api/billing/invoices` | Liste factures org-scopees |
| `GET` | `/api/billing/insights` | Anomalies de facturation org-scopees |
| `GET` | `/api/billing/summary` | KPIs facturation (total factures, pertes estimees) |
| `POST` | `/api/billing/import-csv` | Import factures CSV |
| `POST` | `/api/billing/import-pdf` | Import facture PDF EDF/Engie (pymupdf) |
| `GET` | `/api/billing/invoices/normalized` | Factures normalisees (ht/tva/fournisseur/energie calcules) |
| `POST` | `/api/billing/audit-all` | Lancer les 14 regles d'anomalie sur toutes les factures |
| `GET` | `/api/billing/site/{id}` | Facturation d'un site (factures + insights) |
| `GET` | `/api/billing/anomalies-scoped` | Anomalies billing au format Patrimoine (FACTURATION) |
| `GET` | `/api/billing/periods` | Timeline mensuelle paginee (coverage_status, ratio, total_ttc) |
| `GET` | `/api/billing/coverage-summary` | KPIs globaux : mois couverts/partiels/manquants, top sites |
| `GET` | `/api/billing/missing-periods` | Periodes manquantes/partielles paginées avec CTA import |
| `POST` | `/api/purchase/compute/{site_id}` | Calculer 4 strategies (Fixe/Indexe/Spot/THS) avec report_pct |
| `GET` | `/api/purchase/results/{site_id}` | Resultats scenarios d'un site |
| `GET` | `/api/purchase/results` | Resultats portfolio (tous les sites) |
| `GET` | `/api/purchase/history/{site_id}` | Historique des runs de calcul |
| `POST` | `/api/purchase/seed-demo` | Seed 2 sites demo avec 4 strategies |
| `POST` | `/api/purchase/seed-wow-happy` | Seed 15 sites (donnees propres) |
| `GET` | `/api/monitoring/kpis` | KPIs performance (off_hours_ratio, gaspillage, CO2e) |
| `GET` | `/api/consumption-context/site/{id}` | Contexte complet (profile + activity + anomalies + behavior_score) |
| `GET` | `/api/consumption-context/site/{id}/profile` | Heatmap 7x24, profil journee 24 pts, baseload/peak |
| `GET` | `/api/consumption-context/site/{id}/activity` | Schedule, archetype NAF, TOU schedule actif |
| `GET` | `/api/consumption-context/site/{id}/anomalies` | behavior_score 0-100, insights, weekend_active |
| `POST` | `/api/consumption-context/site/{id}/diagnose` | Refresh diagnostic + recalcul score |
| `GET` | `/api/consumption-context/portfolio/summary` | Classement sites par behavior_score (pires en premier) |
| `GET` | `/api/patrimoine/contracts` | Liste contrats energie org-scopes (V96: indexation, statut, granularite) |
| `GET` | `/api/patrimoine/payment-rules` | Liste regles paiement (portefeuille/site/contrat) |
| `POST` | `/api/patrimoine/payment-rules` | Creer/upsert regle paiement a tout niveau |
| `POST` | `/api/patrimoine/payment-rules/apply-bulk` | Appliquer regle a N sites atomiquement |
| `GET` | `/api/patrimoine/sites/{id}/payment-info` | Resolve regle effective (contrat>site>portefeuille) |
| `GET` | `/api/patrimoine/sites/{id}/reconciliation` | Reconciliation 3 voies : 6 checks, score, statut, fix_actions |
| `POST` | `/api/patrimoine/sites/{id}/reconciliation/fix` | V97: Appliquer un fix 1-click sur un check |
| `GET` | `/api/patrimoine/sites/{id}/reconciliation/history` | V97: Journal audit trail des corrections |
| `GET` | `/api/patrimoine/sites/{id}/reconciliation/evidence` | V97: Evidence pack JSON complet |
| `GET` | `/api/patrimoine/sites/{id}/reconciliation/evidence/csv` | V97: Evidence pack export CSV |
| `GET` | `/api/patrimoine/portfolio/reconciliation` | Reconciliation aggregee portfolio (ok/warn/fail par site) |
| `GET` | `/api/patrimoine/portfolio/reconciliation/evidence/csv` | V97: Export portfolio reconciliation CSV |
| `GET` | `/api/patrimoine/sites/{id}/reconciliation/evidence/summary` | V98: Evidence 1-page summary (score, key checks, NBA) |
| `GET` | `/health` | Health check |

Documentation Swagger complete : `http://localhost:8001/docs`

---

<a id="pages-ui"></a>
## Pages UI

| Route | Page | Intention |
|-------|------|-----------|
| `/` | Dashboard | Vue portefeuille : 120 sites, filtres, statuts conformite |
| `/cockpit` | Cockpit Executif | KPIs COMEX : score global, worst-sites, risque financier |
| `/patrimoine` | Patrimoine | Heatmap sites (risque/anomalies/framework) + cockpit portfolio |
| `/import` | Import HELIOS | Pipeline staging CSV/XLSX : upload, QA, validation, activation |
| `/sites/:id` | Detail Site | Fiche site : obligations, evidences, actions, score |
| `/regops/:id` | RegOps | Audit reglementaire : findings, severite, deadlines, actions |
| `/tertiaire` | Tertiaire OPERAT | Dashboard EFA, wizard OPERAT, anomalies, plan de preuves |
| `/action-plan` | Plan d'action | Actions priorisees cross-sites avec lien preuves OPERAT |
| `/consommations` | Conso & Usages | Profils energetiques, anomalies, recommendations |
| `/connectors` | Connecteurs | Statut des 5 connecteurs, test/sync manuels |
| `/watchers` | Veille Reglementaire | Evenements Legifrance/CRE/RTE, revue manuelle |
| `/kb` | KB Explorer | Knowledge Base : archetypes, regles anomalie, recommendations |
| `/bill-intel` | Bill Intelligence | Import CSV/PDF, shadow billing 12 regles, anomalies, "Creer action" CTA |
| `/billing` | Timeline Facturation | Vue mensuelle couverture (covered/partial/missing), CoverageBar, filtres, pagination |
| `/monitoring` | Performance Electrique V2 | 5 KPI cards (dont THS adoption/gain/risque), plan d'action, expert mode, cross-brique Achats |
| `/actions` | Actions Console | Gestion centralisee, filtres, batch, detail drawer, **WeekView** (4 buckets + closeability badges) |
| `/achat-energie` | Achat Energie V2 | 4 strategies (Fixe/Indexe/Spot/THS), cockpit scenariel, "Option THS" structuree, 7 CTAs cross-briques |
| `/achat-assistant` | Assistant Achat | Wizard 8 etapes, 6 offres demo (dont HEURES_SOLAIRES), deep-link step+offer+site_id |
| `/usages-horaires` | Usages & Horaires | Heatmap 7x24, profil journee (24 pts), talon/peak, ScheduleEditor inline, behavior_score 0-100, anomalies off-hours + weekend |
| `/payment-rules` | Paiement & Refacturation | Matrice facture/payeur/centre de couts, exceptions site/contrat (V96) |
| `/portfolio-reconciliation` | Reconciliation Portefeuille | Triage reconciliation, filtres statut, export CSV, CTA resoudre (V97) |
| `/admin/users` | Admin Utilisateurs | Gestion users/roles/scopes, journal d'audit |
| `/login` | Authentification | Login JWT, switch org, impersonation |

---

<a id="iam"></a>
## IAM — Authentification & Autorisation

### Mode demo (defaut)

`PROMEOS_DEMO_MODE=true` — l'API fonctionne sans authentification (backward compatible).
Si un token JWT est fourni, le filtrage par scope s'applique.

### Mode authentifie

```bash
export PROMEOS_DEMO_MODE=false
export PROMEOS_JWT_SECRET="votre-secret-256-bits"
```

### Personas demo (10 users)

| Email               | Role             | Scope                        | Password |
|---------------------|------------------|------------------------------|----------|
| sophie@atlas.demo   | DG/Owner         | ORG (tout)                   | demo2024 |
| marc@atlas.demo     | DSI/Admin        | ORG (tout)                   | demo2024 |
| claire@atlas.demo   | DAF              | ORG (tout)                   | demo2024 |
| thomas@atlas.demo   | Acheteur         | ORG (tout)                   | demo2024 |
| nadia@atlas.demo    | Resp. Conformite | ORG (tout)                   | demo2024 |
| lucas@atlas.demo    | Energy Manager   | ORG (tout)                   | demo2024 |
| julie@atlas.demo    | Resp. Immobilier | ENTITE Atlas IDF             | demo2024 |
| pierre@atlas.demo   | Resp. Site       | SITE Tour Atlas              | demo2024 |
| karim@atlas.demo    | Prestataire      | SITE Tour Atlas + DC (J+90)  | demo2024 |
| emma@atlas.demo     | Auditeur         | ORG (lecture seule)          | demo2024 |

### Endpoints IAM

| Methode | Path                              | Description                 |
|---------|-----------------------------------|-----------------------------|
| POST    | /api/auth/login                   | Login → JWT                 |
| POST    | /api/auth/refresh                 | Refresh token               |
| GET     | /api/auth/me                      | Profil + role + scopes      |
| POST    | /api/auth/logout                  | Logout (audit)              |
| PUT     | /api/auth/password                | Changer mot de passe        |
| POST    | /api/auth/switch-org              | Changer d'organisation      |
| POST    | /api/auth/impersonate             | Impersonation (admin/demo)  |
| GET     | /api/auth/audit                   | Journal d'audit (admin)     |
| GET     | /api/admin/users                  | Liste utilisateurs          |
| POST    | /api/admin/users                  | Creer utilisateur           |
| PATCH   | /api/admin/users/{id}             | Modifier utilisateur        |
| PUT     | /api/admin/users/{id}/role        | Changer role                |
| PUT     | /api/admin/users/{id}/scopes      | Definir scopes              |
| DELETE  | /api/admin/users/{id}             | Desactiver (soft delete)    |
| GET     | /api/admin/roles                  | Matrice permissions         |
| GET     | /api/admin/users/{id}/effective-access | Acces effectif resolu  |

Pour plus de details : [Security Notes](docs/security_notes.md) | [Demo Script](docs/demo_script_2min.md)

---

<a id="whats-in--whats-out"></a>
## What's in / What's out

### Implemente et fonctionnel

- 4 moteurs de regles deterministes (Tertiaire/OPERAT, BACS, APER, CEE P6)
- Scoring composite (severite x urgence x confiance x completude)
- Cache `RegAssessment` avec invalidation par hash de version
- Knowledge Base avec lifecycle (draft / validated / deprecated) et guards
- 2 connecteurs live (RTE eCO2mix, PVGIS) sans authentification requise
- 3 watchers RSS avec deduplication par hash de contenu
- 5 agents IA en mode stub (fonctionnels sans cle API)
- Job queue async avec logique de cascade
- Mode demo avec masquage de donnees
- IAM complet : JWT, 11 roles metier, scopes hierarchiques (ORG/ENTITE/SITE), deny-by-default
- 10 personas demo avec scopes varies (DG, resp_site, prestataire expire, auditeur)
- Admin UI : gestion users/roles/scopes, acces effectif, journal d'audit
- Filtrage server-side centralise (iam_scope.py) sur 14+ endpoints
- **Module Patrimoine complet (V58-V63)** :
  - Import HELIOS : pipeline staging CSV/XLSX avec QA, mapping FR/EN, validation, activation transactionnelle
  - Anomalies P0 : 5 detecteurs (contrat expire, compteur orphelin, surface/compteur manquant, mismatch BACS, depassement tertiaire)
  - Impact reglementaire & business : estimation risque financier (EUR) par framework
  - HealthCard site : score composite + snapshot canonique
  - Cockpit Portfolio (V60) : risque global, top sites a risque, framework breakdown
  - Portfolio Health Bar enrichi (V61) : % sains/warning/critical, top 3 frameworks, trend
  - Portfolio Trend reel (V62) : cache in-memory par org_id, direction up/down/stable
  - Heatmap portefeuille (V63) : grille sites scalable top-15, risque x anomalies x framework
- **Module Facturation production-grade (V66)** :
  - Org-scoping sur 13 endpoints (`resolve_org_id` + join `site→portefeuille→entite_juridique→org`)
  - `response_model` Pydantic sur tous les endpoints GET (Swagger + validation outbound)
  - Import PDF EDF/Engie via pymupdf (fitz) — templates detectes, confiance >= 0.5
  - 12 regles d'anomalie : R1-R10 shadow billing + R11 TTC coherence + R12 expiry contrat
  - Bridge `ActionItem` : chaque anomalie billing cree un ActionItem idempotent (`source_type=BILLING`)
  - `SiteBillingMini` : KPIs facturation integres dans l'onglet Factures de Site360
  - `GET /anomalies-scoped` : anomalies billing visibles dans la page Anomalies (framework FACTURATION)
- **Timeline & Couverture Facturation (V67)** :
  - `billing_coverage.py` : moteur de couverture mensuelle (`COVERAGE_THRESHOLD=0.80`, SoT `period_start/end` → fallback `issue_date` mois entier, avoirs exclus via `total_eur <= 0`, `set()` de jours anti-double-comptage)
  - 4 index SQLAlchemy sur `EnergyInvoice` (`period_start`, `period_end`, `issue_date`, `(site_id, period_start)`)
  - Fix N+1 `anomalies-scoped` : batch `Site.id.in_(...)` au lieu de 1+N queries
  - 3 nouveaux endpoints pagines : `GET /billing/periods`, `/billing/coverage-summary`, `/billing/missing-periods`
  - `BillingPage.jsx` : page `/billing` avec filtres URL (`?site_id=`), KPIs (covered/partial/missing), CoverageBar, periodes manquantes, timeline paginee "charger plus"
  - `BillingTimeline.jsx` : liste mensuelle avec chips statut, totaux TTC, CTA Voir/Importer/Creer action
  - `CoverageBar.jsx` : barre proportionnelle verte|orange|rouge
  - Lien "Voir timeline complete" dans Site360 → `/billing?site_id=X`
  - 14 tests backend + 31 tests frontend source-guard
- **Billing Unified V68** :
  - `billing_normalization.py` : `InvoiceNormalized` Pydantic schema + `normalize_invoice()` (ht=ENERGY+NETWORK lines, tva=TAX lines, fournisseur/energie depuis contrat) + `GET /billing/invoices/normalized`
  - `billing_shadow_v2.py` : constantes TURPE/ATRD/ATRT/CSPE/TICGN + `shadow_billing_v2()` → 4 composantes (fourniture/reseau/taxes/tva) + deltas vs facture
  - R13 (`_rule_reseau_mismatch` : delta reseau > 10% medium, > 20% high) + R14 (`_rule_taxes_mismatch` : delta taxes > 5% medium) → BILLING_RULES 14 regles
  - Navigation bidirectionnelle : `BillingTimeline → /bill-intel?site_id=X&month=YYYY-MM` ; `BillIntelPage → /billing?site_id=X`
  - `BillIntelPage.jsx` : `useSearchParams` → `siteFilter`/`monthFilter` pre-remplis depuis URL, filtrage front `filteredInvoices`, bouton "Voir timeline" (CalendarRange)
  - `BillingPage.jsx` : lit `?month=YYYY-MM` → `activeMonth` state → passe a BillingTimeline
  - `BillingTimeline.jsx` : `activeMonth` prop → `ring-2 ring-amber-400` sur la ligne du mois actif
  - Seed 36 mois HELIOS : Jan 2023–Dec 2025 × 2 sites (site_a ELEC 9000 kWh, site_b GAZ 6000 kWh), 3 trous (2023-03, 2024-09, 2025-02), 2 partiels (2023-06 15j, 2024-01 20j), 3 anomalies controlees (2024-07 R1 shadow gap, 2024-11 R13 reseau, 2025-01 R14 taxes). Idempotent via `source="seed_36m"`, integre dans `seed_data.py`
  - 20 tests backend + 49 tests frontend source-guard
- **Actions Console V69** :
  - Page `/actions` : gestion centralisee des actions (MANUAL, INSIGHT, BILLING, COMPLIANCE)
  - Filtres multi-criteres : statut, priorite, source, site
  - Batch operations : resoudre/supprimer en masse
  - Detail drawer : contexte complet, timeline, liens source
- **Performance Electrique V2 (V70)** :
  - Restructuration en 4 sections : header-pilotage, a-retenir, plan-action, details
  - Route registry : zero URL hardcodee (`toConsoExplorer`, `toConsoDiag`, `toActionsList`, `toPatrimoine`)
  - Plan d'action : top 3 priorites par impact EUR/an avec CTA "Creer action"
  - Expert mode : metriques avancees (snapshots) gatees derriere `isExpert` accordion
  - "A retenir" : executive summary (risque, gaspillage, confiance, CO2e) avec CTAs "Comprendre"
  - Labels 100% francais : "Off-hours" → "Hors horaires", CTAs coherentes
  - 8 KPI cards en grille 4 colonnes (responsive 1/2/4 col) — Climat integre dans la grille
  - 39 tests vitest source-guard (sections, labels, CTA, route registry, expert mode)
- **Demo Seed Hardening (V71)** :
  - `UniqueConstraint(meter_id, timestamp)` sur le modele MeterReading
  - `INSERT OR IGNORE` comme filet de securite dans gen_readings (SQLite)
  - 60 mois de readings mensuelles (au-dessus du seuil 48 de l'Explorer)
  - Logging + rollback au lieu de swallowing silencieux dans `reset()`
  - 8 tests pytest de regression (unicite, idempotence, reset)
- **Achat Energie V2 (V72-V82)** :
  - Simulateur 4 strategies : Prix Fixe, Indexe, Spot, **Tarif Heures Solaires**
  - Backend : `compute_scenarios()` avec 6 blocs horaires ponderes, `effort_score`, `report_pct`, green bonus (+5 pour THS)
  - Cockpit scenariel : header dynamique "N strategies comparees", KPI strip (budget/risque/recommandation), grille 4 cartes responsive
  - "Option Tarif Heures Solaires" structuree : titre + 2 bullets grand public + badge "Sans penalite" proéminent + badges Budget/Risque/Effort + creneaux Ete/Hiver + blocs horaires collapsibles + delta vs Prix Fixe
  - 7 CTAs cross-briques : Voir preuves conso (date_from/date_to), Controler facture (month), Voir performance (site_id), Creer action (source_type=achat), Tester un THS, Tester dans l'Assistant, Assistant Achat
  - Onglets : Simulation, Portefeuille (top-lists THS, campagne multi-sites), Echeances, Historique
  - Scope lock/unlock, autosave, volume toggle, confidence badges, deep-link tab+site_id
  - Slider report expert-only (Decalage heures pleines → solaire)
  - Zéro URL hardcodée : routes registry (`toPurchase`, `toActionNew`, `toConsoExplorer`, `toBillIntel`, `toMonitoring`, `toPurchaseAssistant`)
- **Performance cross-brique THS (V79)** :
  - 5e KPI card "Tarif Heures Solaires" dans ExecutiveSummary : adoption % solaire, gain estime EUR, CTA "Simuler" → Achats, CTA "Creer action" (TARIF_HEURES_SOLAIRES)
  - Grille 5 colonnes (lg:grid-cols-5), data-testid="kpi-tarif-heures-solaires"
  - `toMonitoring()` route helper
- **Assistant Achat deep-link (V81)** :
  - `toPurchaseAssistant({ site_id, step, offer })` : deep-link vers etape + offre specifique
  - Parsing `useSearchParams` : `?step=offres&offer=HEURES_SOLAIRES&site_id=X`
  - Highlight offre ciblee (amber ring), saut automatique a l'etape Offres
  - 6 offres demo (dont HEURES_SOLAIRES avec solarSlots ete/hiver + "Aucune penalite")
- **Demo HELIOS canonique (V83)** :
  - Groupe Casino completement supprime (pack, seed, tests, templates)
  - Groupe HELIOS = seule demo : 3 entites, 5 sites, 7 batiments, seed deterministe RNG=42
  - `POST /api/dev/reset_db` reseed automatiquement HELIOS
  - Coherence scope : X-Org-Id resolu dynamiquement, zero org_id hardcode
- **Consumption Context V0 — Usages & Horaires (V84)** :
  - Page `/usages-horaires` : 2 tabs (Profil & Heatmap / Horaires & Anomalies)
  - Heatmap 7x24 heures : intensite couleur, labels HP/HC
  - Profil journee 24 points : AreaChart Recharts, bande min-max, baseload Q10 + peak P90
  - behavior_score 0-100 : transparent (4 penalites : hors-horaires, baseload, derive, weekend)
  - `get_consumption_profile()`, `get_activity_context()`, `get_anomalies_and_score()`, `get_full_context()`
  - 6 endpoints REST, 20 tests pytest, 44 tests vitest source-guard
- **ScheduleEditor interactif (ULTIMATE++ V84)** :
  - Edition des horaires d'activite : 7 jours toggle, heure debut/fin, mode 24/7
  - Bouton "Suggestion NAF" (pre-rempli depuis l'archetype)
  - Save → `PUT /api/site-config/{id}/schedule` puis recalcul anomalies via `POST /diagnose`
  - Rafraichissement automatique de la page apres sauvegarde
- **Portfolio Behavior Summary** :
  - `GET /api/consumption-context/portfolio/summary` : classement tous les sites par behavior_score ascending (pires en premier) avec `avg_behavior_score`, `worst_site`, `best_site`
- **UX Overlays (fix/ux-overlays)** :
  - `Tooltip.jsx` : early return si text vide → zero point noir invisible
  - `TooltipPortal.jsx` : guard dans `show()` → skip timer si text falsy
  - `InfoTooltip.jsx` : return null apres hooks si text vide
  - `ScopeSwitcher.jsx` : dropdown via `createPortal(…, document.body)` + `position:fixed z-[9990]` → corrige le clipping par `backdrop-blur-md` du header
- **Demo Seed V86 — Lectures haute resolution** :
  - 730 jours de lectures horaires (87 480 records) pour les 5 sites HELIOS
  - 30 jours de lectures 15min (10 800 records) pour monitoring temps reel
  - Profils realistes par type de batiment (bureau, hotel, ecole, entrepot) avec saisonnalite, week-end, heures creuses
  - Meteo alignee (3 650 records) : temperature, humidite, radiation solaire par ville
  - Filtre `_COMPATIBLE_FREQS` : exclusion des lectures MONTHLY dans l'agregation daily/hourly
- **Demo Seed V87 — Modules BACS, Objectifs, EMS Explorer, Facturation etendue** :
  - `gen_bacs.py` : 5 BacsAsset + 9 BacsCvcSystem (chauffage/clim) + 5 BacsAssessment + 3 BacsInspection, obligation BACS selon puissance CVC (>290kW, >70kW)
  - `gen_targets.py` : 195 ConsumptionTarget (5 sites x 3 ans x 13), trajectoire Decret Tertiaire -1.5%/an, distribution saisonniere mensuelle
  - `gen_ems_views.py` : 4 EmsSavedView (panorama annuel, monitoring 30j 15min, comparaison sites, signature 2 ans) + 2 EmsCollection (tous sites, tertiaires)
  - Facturation : 8 contrats (elec + gaz) + 60 factures avec lignes detaillees + insights anomalies (surfacturation 1/5)
- **Quality Gate V88 — P0 / P1 / P2** :
  - **P0 Overlays** : TooltipPortal wrapper (clipping fix), z-index standardise z-200 (Modal/Drawer), ScopeSwitcher portal
  - **P1 Qualite** : ScopeSummary dedup (source unique), tooltips consolides (TooltipPortal + InfoTip), `useActivationData` hook (dedupe fetches activation), ESLint 211→0 warnings (`--max-warnings=0`)
  - **P2 Perf & Hygiene** : `ui/Badge` partage dans SiteDetail + Site360, dead code supprime (`Cockpit2MinPage` 330 lignes + route), `React.memo` + `useMemo` sur HeatmapChart (Map O(1) vs .find() O(n)), PortfolioPanel (MiniSparkline + RankingTable memo), ProfileHeatmapTab (HeatmapGrid + DailyProfileChart memo), prop stability (setDrillDown direct)
  - Lazy-load : toutes les routes deja en `React.lazy` + `Suspense`
- **Evidence Drawer V0 — "Pourquoi ce chiffre ?" (V89)** :
  - Modele Evidence (`ui/evidence.js`) : JSDoc typedefs, `CONFIDENCE_CFG` (haute/moyenne/basse), `SOURCE_KIND` (enedis/invoice/manual/calc), `buildEvidence()` factory
  - `EvidenceDrawer.jsx` : drawer generique base sur `ui/Drawer` (z-200, focus trap, ESC close), 5 sections (Sources + ConfidencePill, Methode de calcul, Hypotheses, Liens navigation, Dernier calcul)
  - 4 fixtures factory (`evidenceConformite`, `evidenceRisque`, `evidenceKwhTotal`, `evidenceCO2e`) dans `evidence.fixtures.js`
  - Integration Cockpit : `ExecutiveKpiRow` HelpCircle button (conformite + risque), `Cockpit.jsx` evidenceMap + EvidenceDrawer
  - Integration Explorer : `ConsoKpiHeader` HelpCircle button (kWh total + CO2e), `ConsumptionExplorerPage` GenericEvidenceDrawer
  - 32 source-guard tests (6 describe blocks), barrel export `ui/index.js`
  - 2 tests pre-existants corriges (source-guard contractsV36 + dataActivationV37) → 100% green
- **Action Engine universel + Evidence (V90)** :
  - `CreateActionDrawer.jsx` : drawer centralise (remplace modal), evidence_required toggle, auto-deadline (critical→+7j, high→+14j)
  - `ActionDrawerContext.jsx` : context global `openActionDrawer(payload, {onSave})` appelable depuis ConformitePage, BillIntelPage, ActivationPage
  - `HealthSummary.jsx` : CTA "+ Action" sur chaque readiness reason → prefill drawer automatique
  - Backend : colonne `evidence_required` sur `ActionItem`, close gate generique dans `action_close_rules.py`
  - `ActionDetailDrawer.jsx` : indicateur "Preuve requise" + blocage cloture si evidence manquante
  - 13 tests action engine (prefill, auto-deadline, evidence toggle, idempotency keys, FR labels)
- **Dossier & Runbook (V90)** :
  - `dossierModel.js` : `buildDossier(source, actions, evidenceMap)` → structure { header, actions, evidence, missing, stats }
  - `groupActionsByWeek(actions)` → { overdue, today, week, later }
  - `computeCloseabilityBadge(action)` → Cloturee/Bloque/En retard/neutre
  - `DossierPrintView.jsx` : drawer HTML imprimable via `window.print()`, depuis 3 sources (OPERAT EFA, Conformite obligation, Billing anomalie)
  - Boutons "Dossier" sur ConformitePage, BillIntelPage, TertiaireEfaDetailPage
  - ActionsPage WeekView : 4 buckets temporels (Aujourd'hui, 7j, Plus tard, En retard) + badges closeabilite
  - 23 tests dossier/runbook (buildDossier, groupActionsByWeek, closeability, section labels, source tracing, FR invariant)
- **Data Readiness Gate polish (V90)** :
  - `DataReadinessBadge.jsx` : popover premium (titre colore par niveau, max 3 raisons avec navigation, CTA "Corriger maintenant", indicateur trend)
  - `computeDataConfidence(readinessState)` → Elevee/Moyenne/Faible dans PurchasePage subtitle
  - Snapshots scopes localStorage (`promeos.readiness.org-{id}.{scope}`) avec retention 14j + purge auto
  - `computeReadinessTrend(current, previous)` → delta +N dimensions OK / -N points
  - `SOFT_GATE_TOOLTIP_FR`, `LEVEL_BADGE_LABEL` (OK/Partiel/Incomplet), reasons cap 3
  - 21 tests data readiness gate (popover content, confidence, wording FR, trend, snapshots, source guards)
- **Evidence Rules & Source Tracing (V90)** :
  - `evidenceRules.js` : `computeEvidenceRequirement()`, `buildSourceDeepLink()`, `SOURCE_LABELS_FR`, `EVIDENCE_RULES`
  - `billingHealthModel.js` : `buildBillingWatchlist()`, `computeBillingHealthState()`, health trend snapshots
  - 33 + 15 tests evidence rules + billing health
- **Demo Coherence (V90)** :
  - Donnees 100% deterministes : zero `Math.random()` dans mockActions
  - mockTodos : 5 sites fantomes → 5 vrais sites HELIOS avec `site_id`
  - mockKpis : "12 sites" hardcode → calcul dynamique depuis mockSites
  - mockObligations : `sites_concernes` alignes sur 5 sites (DT→4, BACS→3, APER→2, DPE→5, Audit→5)
  - mockActions : 15 actions fixes couvrant 5 sites × 4 types × 4 statuts × 4 priorites
  - Toulouse `non_conforme` : couverture complete des 4 statuts conformite
  - 32 tests cross-fichiers (`demoCoherence.test.js`) : sites, KPIs, todos, actions, obligations, FR labels
- **QA Audit V91 — Golden Contract HELIOS** :
  - Nice (id:4) : `en_cours` → `a_risque` — les 4 statuts conformite exerces (conforme, non_conforme, en_cours, a_risque)
  - mockTodos : noms hardcodes → derives via `SITE[id].nom` depuis sites.js
  - Fix Unicode : `\u00e9`/`\u00e0` → caracteres UTF-8 reels sur 6 fichiers (ActivationPage, DataActivationPanel, ImpactDecisionPanel, ScheduleEditor, StickyFilterBar, scheduleValidation)
  - +6 tests single-source-of-truth : import `./sites`, no Math.random, no Date.now, todos derived, a_risque > 0
  - 38 tests demoCoherence pass (32 + 6 nouveaux)
- **3 975 frontend + 2 400+ backend = 6 375+ tests automatises, 0 regression**
- 12 items KB valides (archetypes, regles, recommendations)
- Smoke test "red button" (14 checks avant mise en pilote)

### Non implemente (hors scope POC)

- Multi-tenancy full (IAM multi-org presente mais pas de tenancy isolation DB)
- Connecteurs Enedis (OAuth DataConnect), Meteo-France (cle API requise)
- Base de donnees PostgreSQL (SQLite uniquement)
- CI/CD (fichiers GitHub Actions presents mais vides)
- Rate limiting / throttling
- Import de donnees reelles (releves compteurs Enedis)
- Notifications (email, webhook)

---

<a id="roadmap-30-jours"></a>
## Roadmap 30 jours

Basee sur le backlog existant (`docs/backlog/PROOF_BACKLOG.md`) et l'etat du repo.

### Sprint 1 (J1-J10) -- Securite & Stabilisation

- Implementer l'authentification JWT + roles (admin, manager, viewer)
- Remplir les GitHub Actions (backend-tests.yml, frontend-build.yml)
- Ajouter des tests d'integration API (auth, pagination, erreurs)
- Ecrire `scripts/setup.sh` et `scripts/dev.sh`

### Sprint 2 (J11-J20) -- Connecteurs & Donnees Reelles

- Activer le connecteur Enedis DataConnect (OAuth, sandbox GRDF)
- Ajouter un import CSV/XLSX pour les factures d'energie
- Enrichir la KB : passer de 12 a 40+ items (couverture 5 domaines x 5 segments)
- Activer les agents IA avec une cle Anthropic

### Sprint 3 (J21-J30) -- Pilote Client

- Tester sur un portefeuille reel (~10 sites) avec donnees anonymisees
- Migrer vers PostgreSQL pour le pilote
- Deployer sur un serveur (Docker Compose ou VPS)
- Produire le rapport de couverture KB (`scripts/kb_coverage_report.py`)

---

<a id="troubleshooting"></a>
## Troubleshooting

### Le backend ne demarre pas

```
ModuleNotFoundError: No module named 'fastapi'
```
Le virtualenv n'est pas active. Relancer :
```bash
cd backend
.\venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
```

### Port 8001 deja utilise

```bash
# Trouver le processus
netstat -ano | findstr :8001
# Tuer le processus
taskkill /PID <PID> /F
```

> **Note** : Le port 8000 peut etre occupe par des sockets fantomes Windows apres des redemarrages.
> Le backend utilise le port **8001** par defaut. Le proxy Vite (`frontend/vite.config.js`) est configure en consequence.

### Le frontend affiche des erreurs API

- Verifier que le backend tourne sur `localhost:8001`.
- Le proxy Vite redirige `/api/*` vers le backend (configure dans `frontend/vite.config.js`).
- CORS est ouvert dans le POC (`allow_origins=["*"]` dans `backend/main.py`).

### La DB est vide / pas de sites

```bash
cd backend
python scripts/seed_data.py
```
Le seed drop + recreate toutes les tables, puis genere 120 sites.

### `node_modules` corrompus

```bash
cd frontend
rm -rf node_modules
npm install
```

### Erreur `execution_policy` sur Windows PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Tests echouent

```bash
cd backend
python -m pytest tests/ -v --tb=short
```
Resultat attendu : `2400+ passed`.

### Tests IAM uniquement

```bash
cd backend
py -3.14 -m pytest tests/test_iam.py -v
```
Resultat attendu : `61 passed`.

---

<a id="contributing"></a>
## Contributing

1. Fork le repo
2. Creer une branche (`git checkout -b feature/ma-feature`)
3. Commiter (`git commit -m "feat: description"`)
4. Pousser (`git push origin feature/ma-feature`)
5. Ouvrir une Pull Request

Conventions :
- Commits : `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Backend : Python, formatte avec black
- Frontend : JS/JSX, formatte avec Prettier (config dans `.prettierrc`)

## License

MIT

## Disclaimer

Ce projet est un **proof-of-concept** destine a la demonstration technique.
Il ne doit pas etre deploye en production sans :
- Desactivation du mode demo (`PROMEOS_DEMO_MODE=false`) et definition d'un JWT secret fort
- Migration vers une base de donnees robuste (PostgreSQL)
- Audit de securite complet
- Suppression du mode CORS ouvert
- HTTPS obligatoire (le JWT transite en clair)

Les donnees incluses sont 100% synthetiques.
