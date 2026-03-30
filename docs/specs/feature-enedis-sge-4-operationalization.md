# SF4 — Enedis SGE Operational Ingestion Pipeline

> **Status**: Spec v7 — integre les decisions revue finale (garde MAX_RETRIES dans ingest_file, dry-run sans mutation, statut failed unique, IngestionRunStatus enum)
> **Plan d'implementation** : `docs/specs/plan-enedis-sge-4-implementation.md`
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion) — all complete on `feat/enedis-sge-ingestion`
> **Out of scope**: Promotion staging → production (SF5). Pas de matching PRM→Site, pas d'ecriture dans les tables fonctionnelles (`Consommation`, `MeterReading`), pas de deduplication des republications. Pas d'endpoint de force-retry pour PERMANENTLY_FAILED (futur).

## Decisions d'architecture

| Question | Decision | Justification |
|----------|----------|---------------|
| Historique d'erreurs | **Table separee** `enedis_flux_file_error` (FK vers `enedis_flux_file`) | Propre, extensible, requetable en SQL directement. Plus robuste qu'une colonne JSON |
| Compteur de tentatives | **Derive** de `len(flux_file.errors)` — pas de colonne `retry_count` | Pas de desynchronisation possible, source unique de verite (l'historique) |
| Retry automatique en batch | **Auto-retry avec garde `MAX_RETRIES`** (default 3) dans `ingest_directory()` | Un seul point d'entree fait tout. Les fichiers definitivement casses ne sont pas retentes indefiniment |
| Fichiers PERMANENTLY_FAILED | **Nouveau statut `FluxStatus.PERMANENTLY_FAILED`** quand `MAX_RETRIES` atteint | Un data manager identifie d'un coup d'oeil les fichiers bloques. Forcer un retry = futur endpoint dedie |
| Fichiers NEEDS_REVIEW | **Pas de retry automatique** — donnees deja chargees, en attente de review humaine | Traitement initial reussi, republication detectee. Pas un cas d'erreur |
| Suivi d'execution | **Table `IngestionRun`** avec **compteurs incrementaux** mis a jour fichier par fichier | Si le run crashe, les compteurs refletent le travail reel. Statut "failed" avec compteurs fiables |
| Statuts IngestionRun | **running / completed / failed** | "failed" = crash ou erreur apres creation du run. Les compteurs incrementaux refletent le travail effectue avant le crash |
| Session API | **`Depends(get_db)`** standard + `IngestionRun` pour tracabilite | Pipeline commits per-file (by design). Pas de session cachee, tout est tracable via `IngestionRun` |
| Concurrence | **Verrou simple** : refuser un nouveau run si un run est en status "running" | Evite les compteurs incoherents si deux runs traitent le meme repertoire en parallele |
| Validation pre-flight | **Verifier cles + repertoire AVANT de creer l'IngestionRun** | Fail fast : pas de run inutile dans l'historique si les conditions minimales ne sont pas remplies |
| Variable ENEDIS_FLUX_DIR | **Obligatoire** dans `.env` — pas de fallback | La clarte prime. Les chemins relatifs et fallbacks sont source d'erreurs |
| CLI scope | **Minimaliste** — sous-commande `ingest` uniquement (+ `--dry-run`) | Les stats restent cote API, evite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ulterieurement via `get_optional_auth` |
| Schemas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase — les schemas specifiques a un domaine sont co-localises avec le router |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) mis a jour | Coherence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Coherent avec les autres tests d'API (`test_bacs_api.py`, etc.) |
| Mesures dans IngestResponse | **Non** — IngestResponse retourne les compteurs fichiers uniquement | Les volumes de mesures sont des totaux staging (pas des deltas du run). Disponibles via GET /stats. Separation des responsabilites |
| Scripts ad-hoc | **Deprecation** en phase 1, suppression apres validation SF4 complete | Garder comme reference pendant la transition, supprimer en cleanup |

---

## Contexte

SF1-SF3 ont livre un pipeline d'ingestion complet : dechiffrement, parsing et stockage de fichiers flux Enedis reels (R4H, R4M, R4Q, R171, R50, R151) dans 5 tables staging. 221 tests passent, 91 fichiers reels ingeres avec 0 erreur, 123 846 mesures au total.

Deux scripts ad-hoc existent dans `backend/data_ingestion/enedis/scripts/` pour lancer l'ingestion manuellement.

**Probleme :** Le pipeline n'a pas de point d'entree operationnel, pas de surface d'observabilite, et un bug qui detruit l'historique d'erreurs au retry. SF4 rend le pipeline staging brut **fiable, complet et auditable**.

## Scope SF4

SF4 livre 5 choses :

1. **CLI** — commande propre avec arguments, remplacant les scripts ad-hoc
2. **API REST** — declencher l'ingestion + consulter l'etat et les stats (scaffolding pour future UX)
3. **Configuration** — variable d'environnement obligatoire pour le repertoire de flux, plus de chemins hardcodes
4. **Correction de l'audit d'erreurs** — preserver l'historique des erreurs au retry, nouveau statut `PERMANENTLY_FAILED` pour les fichiers ayant atteint `MAX_RETRIES`
5. **Wiring** — nouveau router enregistre dans l'application

**Hors scope :** integration JobOutbox, frontend/UI, alerting/notifications, promotion vers tables de production (SF5), endpoint de force-retry pour PERMANENTLY_FAILED.

---

## 1. CLI

### Objectif

Remplacer les scripts ad-hoc par une commande CLI propre avec arguments. Suit le pattern existant des autres commandes CLI du projet (`services.demo_seed`, `jobs.run`).

### Validation pre-flight

Avant de creer un IngestionRun, le CLI verifie :
1. Variable `ENEDIS_FLUX_DIR` configuree et repertoire existant — sinon erreur explicite et exit
2. Cles de dechiffrement disponibles (`load_keys_from_env()`) — sinon erreur explicite et exit
3. Pas de run concurrent en status "running" — sinon message d'avertissement et exit

### Commandes

**Ingestion :**

```
python -m data_ingestion.enedis.cli ingest [OPTIONS]
```

| Option | Defaut | Description |
|--------|--------|-------------|
| `--dir PATH` | Variable d'env `ENEDIS_FLUX_DIR` (obligatoire) | Repertoire source des fichiers .zip chiffres |
| `--recursive` | Active | Scanner les sous-repertoires |
| `--dry-run` | Desactive | Scanner et classifier sans ingerer (rapport uniquement) |
| `--verbose` | Desactive | Logging niveau DEBUG |

### Sorties attendues

**Mode normal** — rapport structure resumant :
- Source, numero de run, nombre de fichiers scannes
- Repartition par statut (parsed, skipped, error, needs_review, permanently_failed)
- Fichiers retentes (erreurs precedentes retraitees) et fichiers ayant atteint `MAX_RETRIES`
- Detail des skips par type de flux (R172, X14, HDM)
- Volume de mesures par table staging (R4x, R171, R50, R151) — requetes DB post-ingestion, pattern identique a `ingest_real_db.py`
- Liste des erreurs eventuelles (filename + message)
- Statut final du run (completed / failed)

**Mode dry-run** — rapport de ce qui *serait* fait :
- Nombre de fichiers nouveaux par type de flux
- Nombre de fichiers deja traites
- Nombre de fichiers en erreur eligibles au retry (< `MAX_RETRIES`)
- Nombre de fichiers PERMANENTLY_FAILED (ne seront pas retentes)
- Aucune modification sur les donnees d'ingestion (flux files, mesures). Un enregistrement `IngestionRun` avec `dry_run=True` est cree pour l'audit

Le dry-run utilise le parametre `dry_run=True` de `ingest_directory()` : meme logique de scan/classify/hash-check, mais sans commit ni processing.

---

## 2. API REST

### Objectif

Exposer le declenchement d'ingestion et la consultation d'etat via REST. Doit fournir un scaffolding suffisant pour construire ulterieurement une feature UX complete de gestion des flux.

### Router

`/api/enedis` — coherent avec le naming domaine-par-domaine du codebase.

### 2.1 Declencher une ingestion

`POST /api/enedis/ingest`

- Parametres optionnels : repertoire source (override), mode recursif, mode dry-run
- **Validation pre-flight** avant toute creation d'IngestionRun :
  - Cles de dechiffrement disponibles — sinon **422** avec message explicite
  - Repertoire source valide — sinon **422** avec message explicite
  - Pas de run concurrent en status "running" — sinon **409** avec `run_id` du run en cours
- Execution synchrone (suffisant pour le volume POC ~100 fichiers, <10 secondes)
- Cree un enregistrement `IngestionRun` (`triggered_by='api'`) **apres** validation pre-flight reussie
- **Compteurs mis a jour incrementalement** pendant l'execution : si le run crashe, l'IngestionRun passe en status "failed" avec les compteurs refletant le travail effectue
- Reponse : `run_id`, compteurs par statut, liste des erreurs, duree d'execution, statut du run
- Le mode dry-run retourne les memes compteurs sans effectuer de modification sur les donnees

### 2.2 Lister les fichiers flux

`GET /api/enedis/flux-files`

- Filtrage par statut (incluant PERMANENTLY_FAILED) et par type de flux
- Pagination (offset-based, coherent avec les autres endpoints PROMEOS)
- Chaque item expose : filename, hash, type, statut, nombre de mesures, version, lien de supersession, message d'erreur, timestamps
- Extensible ulterieurement avec tri et recherche par nom sans casser le schema

### 2.3 Statistiques d'ingestion

`GET /api/enedis/stats`

Retourne en un seul appel :
- **Fichiers** : total, repartition par statut (incluant PERMANENTLY_FAILED), repartition par type de flux
- **Mesures** : total, repartition par table staging (r4x, r171, r50, r151)
- **PRMs** : nombre distinct et liste des identifiants PRM presents dans le staging (scaffolding pour le matching PRM→DeliveryPoint en SF5)
- **Derniere ingestion** : `IngestionRun` le plus recent avec `status=completed` et `dry_run=False` — timestamp de fin et nombre de fichiers traites

> **Note PRM scope** : Dans le POC, la liste PRM est globale (tous les PRM du staging). En production, cette API sera filtree par contrat/portefeuille en cours de visualisation. Le volume par contrat ne justifie pas de pagination pour le moment. Point d'attention pour la version production.

### 2.4 Detail d'un fichier flux

`GET /api/enedis/flux-files/{id}`

- Toutes les informations de la liste + header XML brut (JSON) + historique d'erreurs complet
- 404 si non trouve

---

## 3. Configuration

### Variable d'environnement

`ENEDIS_FLUX_DIR` — chemin absolu vers le repertoire contenant les fichiers flux chiffres.

- **Obligatoire** — pas de valeur par defaut ni de fallback. La clarte prime sur la commodite
- Ajoute dans `.env` et `.env.example` avec commentaire explicatif
- Utilise par le CLI et l'API comme repertoire par defaut
- Le parametre API `directory` et l'option CLI `--dir` permettent de l'overrider ponctuellement
- Si absente : erreur explicite `"ENEDIS_FLUX_DIR environment variable is required — set it in .env"`

### Constante `MAX_RETRIES`

Nombre maximum de retries sur un fichier en erreur (default 3, soit 4 tentatives au total : 1 initiale + 3 retries). Stocke dans `config.py`. Au-dela de cette limite, le fichier passe en statut `PERMANENTLY_FAILED` et n'est plus retente automatiquement.

---

## 4. Correction de l'audit d'erreurs

### Probleme

Actuellement, quand un fichier en statut ERROR est re-traite, le pipeline **supprime** l'enregistrement existant et en cree un nouveau. Cela perd :
- La date de la premiere erreur
- Le message d'erreur original
- Le nombre de tentatives echouees

Ce comportement est non-auditable et empeche toute analyse statistique des erreurs d'ingestion.

### Comportement cible

- Au retry, l'erreur courante est **archivee** dans un historique (pas supprimee)
- Le fichier est re-traite **in-place** (meme enregistrement, meme ID) au lieu d'etre supprime/recree
- L'historique complet des erreurs est consultable via l'API (endpoint detail 2.4)
- Le nombre de tentatives est derive de `len(flux_file.errors)` — pas de colonne dediee
- En mode batch (`ingest_directory()`), les fichiers ERROR sont **automatiquement retentes** si `len(errors) < MAX_RETRIES`. Au-dela, leur statut passe a `PERMANENTLY_FAILED`
- Les fichiers `NEEDS_REVIEW` ne sont **pas retentes** automatiquement : leurs donnees ont ete chargees avec succes, seule une analyse manuelle est requise (republication detectee)
- `ingest_file()` refuse de traiter un fichier `PERMANENTLY_FAILED` (skip silencieux, meme comportement que PARSED/SKIPPED)
- `ingest_file()` verifie `len(errors) >= MAX_RETRIES` avant de retenter un fichier ERROR — si la limite est atteinte, le fichier passe en `PERMANENTLY_FAILED` sans retry. Cette garde est necessaire pour les appels directs (futur endpoint UX de re-ingestion fichier par fichier)
- En mode `dry_run`, la transition ERROR → `PERMANENTLY_FAILED` n'est pas commitee : le dry-run compte les fichiers concernes sans les modifier

### Nouveau statut : PERMANENTLY_FAILED

Un fichier atteint `PERMANENTLY_FAILED` quand le nombre d'erreurs archivees atteint `MAX_RETRIES`. Ce statut signifie :
- Le fichier ne sera plus retente automatiquement par `ingest_directory()`
- Le data manager doit investiguer la cause (visible dans l'historique d'erreurs via API)
- Forcer un retry necessite un futur endpoint dedie (hors scope SF4)
- Le statut est visible dans l'API (liste, stats, detail) et dans le rapport CLI

### Suivi d'execution : IngestionRun avec compteurs incrementaux

Chaque execution (CLI ou API) cree un enregistrement `IngestionRun`. Les compteurs sont mis a jour **fichier par fichier** pendant l'execution (pas uniquement a la fin). Ce design a trois consequences :

1. **Si le run crashe** : les compteurs refletent le travail reel effectue. Le statut passe a `failed`. Les fichiers traites avant le crash sont bien en base (commits per-file).
2. **Run suivant** : les fichiers deja traites sont vus comme `already_processed`. Seuls les fichiers restants sont traites. Pas de reprocessing inutile grace a l'idempotence SHA256.
3. **Audit** : on peut analyser sur la duree les patterns d'execution partielle pour identifier des problemes recurrents (timeout, memoire, fichier corrompu specifique).

Statuts possibles d'un `IngestionRun` :
- `running` — en cours d'execution
- `completed` — tous les fichiers traites avec succes (certains peuvent etre en erreur, mais le run lui-meme a termine)
- `failed` — interruption ou erreur apres creation du run. Les compteurs incrementaux refletent le travail effectue avant le crash

---

## 5. Wiring applicatif

Le nouveau router Enedis est integre dans l'application via le meme pattern que tous les autres routers : declaration dans `routes/`, enregistrement dans `main.py`.

---

## Inventaire des assets

| Asset | Path | Statut |
|-------|------|--------|
| Pipeline | `backend/data_ingestion/enedis/pipeline.py` | SF3 done |
| Models | `backend/data_ingestion/enedis/models.py` | SF3 done, a enrichir (EnedisFluxFileError, IngestionRun) |
| Parsers | `backend/data_ingestion/enedis/parsers/` | SF3 done |
| Decrypt | `backend/data_ingestion/enedis/decrypt.py` | SF1 done |
| Enums | `backend/data_ingestion/enedis/enums.py` | SF3 done, a enrichir (PERMANENTLY_FAILED) |
| Scripts ad-hoc | `backend/data_ingestion/enedis/scripts/` | **Depreces** — remplaces par le CLI. Suppression apres validation SF4 complete |
| Tests (221) | `backend/data_ingestion/enedis/tests/` | SF3 done |
| Fichiers flux reels | `flux_enedis/` (hors repo, 91 in-scope) | — |
| **Nouveau : CLI** | `backend/data_ingestion/enedis/cli.py` | **SF4** |
| **Nouveau : Config** | `backend/data_ingestion/enedis/config.py` | **SF4** |
| **Nouveau : Router** | `backend/routes/enedis.py` | **SF4** |

## Ce qui vient apres SF4

- **SF5 — Promotion staging → production** : matching PRM→DeliveryPoint, normalisation des donnees (string→float/datetime), resolution des republications, ecriture dans les tables fonctionnelles.
- **Feature UX** : page frontend de gestion des flux (liste de fichiers, tableau de bord stats, bouton de re-ingestion) — s'appuie sur le scaffolding API de SF4.
- **Endpoint force-retry** : permettre au data manager de remettre un fichier PERMANENTLY_FAILED en ERROR pour forcer un nouveau cycle de retry.
- **Filtrage PRM par contrat** : adapter GET /stats pour filtrer les PRMs par portefeuille/contrat en cours de visualisation.
- **Suppression scripts ad-hoc** : cleanup de `backend/data_ingestion/enedis/scripts/` une fois SF4 valide.
- **Cleanup conftest.py** : remplacer `_FLUX_DIR` hardcode dans `conftest.py` par `get_flux_dir()` de `config.py`.
