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
> | Backend API (~150 endpoints) | Stable |
> | Frontend React (20+ pages) | Stable |
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
> | Suite de tests automatises | **2 138 passes, 0 echec** |

> **Disclaimer**
>
> Ce depot est un **proof-of-concept** (POC). Il n'est pas prevu pour la production :
> pas de rate-limiting, SQLite en mono-fichier, CORS ouvert.
> Authentification IAM implementee (JWT + scopes hierarchiques + 11 roles metier).
> Les donnees de demo sont synthetiques (120 sites fictifs, 10 personas IAM).

---

<a id="tldr"></a>
## TL;DR

- **Backend FastAPI** avec ~150 endpoints, 20+ modeles SQLAlchemy, 4 moteurs de regles reglementaires, 5 connecteurs de donnees, 4 watchers de veille, 5 agents IA (stub), module Patrimoine complet (import HELIOS, anomalies, impact reglementaire, cockpit portfolio V60-V63), module Facturation production-grade (org-scoping, PDF EDF/Engie, shadow billing V2 TURPE/CSPE/TICGN, 14 regles d'anomalie, bridge Action Center), timeline & couverture facturation (periods, coverage engine V67), Billing Unified (InvoiceNormalized, deep-links bidirectionnels, seed 36 mois HELIOS V68).
- **Frontend React 18 + Tailwind + Vite** avec 20+ pages : Dashboard, Cockpit Executif, Patrimoine (heatmap + portfolio), Detail Site, Plan d'action, RegOps, Conso & Usages, Tertiaire OPERAT, IAM Admin, Import, KB Explorer, Veille Reglementaire, Facturation (BillIntel deep-links site_id/month + BillingPage activeMonth highlight + BillingTimeline ring + SiteBillingMini), et plus.
- **2 138 tests passent, 0 echec** — pytest backend complet, seed de 120 sites + 10 personas IAM + 36 mois facturation HELIOS en une commande, demo operationnelle en 2 minutes.

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

- Ouvrir `http://localhost:8000/docs` pour explorer les 66 endpoints interactivement.

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
cd backend

# Creer le virtualenv (une seule fois)
python -m venv venv

# Activer le virtualenv
# Windows PowerShell :
.\venv\Scripts\Activate.ps1
# Windows CMD :
venv\Scripts\activate.bat
# Linux/macOS :
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt

# Copier la config (une seule fois)
copy .env.example .env
# Linux/macOS : cp .env.example .env

# Initialiser la DB + seed 120 sites
python scripts/init_database.py
python scripts/seed_data.py

# Lancer le serveur (port 8000)
python main.py
```

Le backend est pret quand vous voyez :
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Verifier : `http://localhost:8000/health` doit retourner `{"status":"healthy"}`.

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

Le proxy Vite redirige automatiquement `/api/*` vers `http://localhost:8000`.

### Variables d'environnement

Le fichier `backend/.env.example` contient toutes les variables :

| Variable | Defaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | `sqlite:///./data/promeos.db` | Chemin de la DB SQLite |
| `API_HOST` | `127.0.0.1` | Host du backend |
| `API_PORT` | `8000` | Port du backend |
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

Genere :
- 1 organisation + 1 entite juridique + 3 portefeuilles
- 120 sites (magasins, bureaux, usines) avec champs RegOps
- 120 batiments avec puissance CVC realiste
- ~240 obligations (Decret Tertiaire + BACS)
- ~600 evidences de conformite
- ~45 compteurs avec 7 jours de consommation horaire
- 20 alertes actives
- ~60 DataPoints (RTE CO2, PVGIS)
- 4 RegSourceEvents (veille reglementaire)
- 120 RegAssessments (evaluation RegOps par site)
- 4 jobs dans l'outbox

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
                          |  8 pages + Vite   |
                          +--------+----------+
                                   |
                            proxy /api/*
                                   |
                          +--------v----------+
                          |   FastAPI Backend  |
                          |  localhost:8000   |
                          |   66 endpoints    |
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
| Tests | pytest 7.4 |

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

~150 endpoints au total. Selection des plus importants :

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
| `GET` | `/health` | Health check |

Documentation Swagger complete : `http://localhost:8000/docs`

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
| `/monitoring` | Monitoring | Alertes actives, KPIs live, badges sidebar |
| `/purchase` | Achat Energie | Assistant achat multi-sites, note decision, RFP |
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
- **2 138 tests automatises (pytest), 0 echec**
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

### Port 8000 deja utilise

```bash
# Trouver le processus
netstat -ano | findstr :8000
# Tuer le processus
taskkill /PID <PID> /F
```

### Le frontend affiche des erreurs API

- Verifier que le backend tourne sur `localhost:8000`.
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
Resultat attendu : `2138 passed, 12 skipped`.

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
