# SF4 — Enedis SGE Operational Ingestion Pipeline

> **Status**: Spec v5 — fully aligned with implementation plan v2
> **Plan d'implementation** : `docs/specs/plan-enedis-sge-4-implementation.md`
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion) — all complete on `feat/enedis-sge-ingestion`
> **Out of scope**: Promotion staging → production (SF5). Pas de matching PRM→Site, pas d'ecriture dans les tables fonctionnelles (`Consommation`, `MeterReading`), pas de deduplication des republications.

## Decisions d'architecture

| Question | Decision | Justification |
|----------|----------|---------------|
| Historique d'erreurs | **Table separee** `enedis_flux_file_error` (FK vers `enedis_flux_file`) | Propre, extensible, requetable en SQL directement. Plus robuste qu'une colonne JSON |
| Compteur de tentatives | **Derive** de `len(flux_file.errors)` — pas de colonne `retry_count` | Pas de desynchronisation possible, source unique de verite (l'historique) |
| Retry automatique en batch | **Auto-retry avec garde `MAX_RETRIES`** (default 3) dans `ingest_directory()` | Un seul point d'entree fait tout. Les fichiers definitivement casses ne sont pas retentes indefiniment |
| Suivi d'execution | **Table `IngestionRun`** (1 row par execution CLI/API) | Audit trail lisible pour un data manager, `LastIngestion` trivial a calculer |
| Session API | **`Depends(get_db)`** standard + `IngestionRun` pour tracabilite | Pipeline commits per-file (by design). Pas de session cachee, tout est tracable via `IngestionRun` |
| CLI scope | **Minimaliste** — sous-commande `ingest` uniquement (+ `--dry-run`) | Les stats restent cote API, evite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ulterieurement via `get_optional_auth` |
| Schemas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase — les schemas specifiques a un domaine sont co-localises avec le router |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) mis a jour | Coherence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Coherent avec les autres tests d'API (`test_bacs_api.py`, etc.) — les tests HTTP vivent dans le repertoire de tests principal |

---

## Contexte

SF1-SF3 ont livre un pipeline d'ingestion complet : dechiffrement, parsing et stockage de fichiers flux Enedis reels (R4H, R4M, R4Q, R171, R50, R151) dans 5 tables staging. 221 tests passent, 91 fichiers reels ingeres avec 0 erreur, 123 846 mesures au total.

Deux scripts ad-hoc existent dans `backend/data_ingestion/enedis/scripts/` pour lancer l'ingestion manuellement.

**Probleme :** Le pipeline n'a pas de point d'entree operationnel, pas de surface d'observabilite, et un bug qui detruit l'historique d'erreurs au retry. SF4 rend le pipeline staging brut **fiable, complet et auditable**.

## Scope SF4

SF4 livre 5 choses :

1. **CLI** — commande propre avec arguments, remplacant les scripts ad-hoc
2. **API REST** — declencher l'ingestion + consulter l'etat et les stats (scaffolding pour future UX)
3. **Configuration** — variable d'environnement pour le repertoire de flux, plus de chemins hardcodes
4. **Correction de l'audit d'erreurs** — preserver l'historique des erreurs au retry au lieu de supprimer les enregistrements
5. **Wiring** — nouveau router enregistre dans l'application

**Hors scope :** integration JobOutbox, frontend/UI, alerting/notifications, promotion vers tables de production (SF5).

---

## 1. CLI

### Objectif

Remplacer les scripts ad-hoc par une commande CLI propre avec arguments. Suit le pattern existant des autres commandes CLI du projet (`services.demo_seed`, `jobs.run`).

### Commandes

**Ingestion :**

```
python -m data_ingestion.enedis.cli ingest [OPTIONS]
```

| Option | Defaut | Description |
|--------|--------|-------------|
| `--dir PATH` | Variable d'env ou defaut projet | Repertoire source des fichiers .zip chiffres |
| `--recursive` | Active | Scanner les sous-repertoires |
| `--dry-run` | Desactive | Scanner et classifier sans ingerer (rapport uniquement) |
| `--verbose` | Desactive | Logging niveau DEBUG |

### Sorties attendues

**Mode normal** — rapport structure resumant :
- Source, numero de run, nombre de fichiers scannes
- Repartition par statut (parsed, skipped, error, needs_review)
- Fichiers retentes (erreurs precedentes retraitees) et fichiers ayant atteint `MAX_RETRIES`
- Detail des skips par type de flux (R172, X14, HDM)
- Volume de mesures par table staging (R4x, R171, R50, R151) — requetes DB post-ingestion, pattern identique a `ingest_real_db.py`
- Liste des erreurs eventuelles (filename + message)

**Mode dry-run** — rapport de ce qui *serait* fait :
- Nombre de fichiers nouveaux par type de flux
- Nombre de fichiers deja traites
- Nombre de fichiers en erreur eligibles au retry (< `MAX_RETRIES`)
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
- Execution synchrone (suffisant pour le volume POC ~100 fichiers, <10 secondes)
- Cree un enregistrement `IngestionRun` (`triggered_by='api'`) avant l'execution, mis a jour avec les resultats apres
- Reponse : `run_id`, compteurs par statut, liste des erreurs, duree d'execution
- Le mode dry-run retourne les memes compteurs sans effectuer de modification sur les donnees

### 2.2 Lister les fichiers flux

`GET /api/enedis/flux-files`

- Filtrage par statut et par type de flux
- Pagination (offset-based, coherent avec les autres endpoints PROMEOS)
- Chaque item expose : filename, hash, type, statut, nombre de mesures, version, lien de supersession, message d'erreur, timestamps
- Extensible ulterieurement avec tri et recherche par nom sans casser le schema

### 2.3 Statistiques d'ingestion

`GET /api/enedis/stats`

Retourne en un seul appel :
- **Fichiers** : total, repartition par statut, repartition par type de flux
- **Mesures** : total, repartition par table staging (r4x, r171, r50, r151)
- **PRMs** : nombre distinct et liste des identifiants PRM presents dans le staging (scaffolding pour le matching PRM→DeliveryPoint en SF5)
- **Derniere ingestion** : `IngestionRun` le plus recent avec `status=completed` et `dry_run=False` — timestamp de fin et nombre de fichiers traites

### 2.4 Detail d'un fichier flux

`GET /api/enedis/flux-files/{id}`

- Toutes les informations de la liste + header XML brut (JSON) + historique d'erreurs complet
- 404 si non trouve

---

## 3. Configuration

### Variable d'environnement

`ENEDIS_FLUX_DIR` — chemin absolu vers le repertoire contenant les fichiers flux chiffres.

- Ajoute dans `.env` et `.env.example`
- Valeur par defaut : `flux_enedis/` au niveau racine du projet Promeos
- Utilise par le CLI et l'API comme repertoire par defaut
- Le parametre API `directory` permet de l'overrider ponctuellement

### Constante `MAX_RETRIES`

Nombre maximum de tentatives sur un fichier en erreur (default 3). Stocke dans `config.py`. Au-dela de cette limite, le fichier est ignore lors des executions batch et comptabilise comme `max_retries_reached`.

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
- En mode batch (`ingest_directory()`), les fichiers ERROR sont **automatiquement retentes** si `len(errors) < MAX_RETRIES`. Au-dela, ils sont comptabilises comme `max_retries_reached` et ignores

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
| Enums | `backend/data_ingestion/enedis/enums.py` | SF3 done |
| Scripts ad-hoc | `backend/data_ingestion/enedis/scripts/` | Supersedes par le CLI |
| Tests (221) | `backend/data_ingestion/enedis/tests/` | SF3 done |
| Fichiers flux reels | `flux_enedis/` (hors repo, 91 in-scope) | — |
| **Nouveau : CLI** | `backend/data_ingestion/enedis/cli.py` | **SF4** |
| **Nouveau : Config** | `backend/data_ingestion/enedis/config.py` | **SF4** |
| **Nouveau : Router** | `backend/routes/enedis.py` | **SF4** |

## Ce qui vient apres SF4

- **SF5 — Promotion staging → production** : matching PRM→DeliveryPoint, normalisation des donnees (string→float/datetime), resolution des republications, ecriture dans les tables fonctionnelles.
- **Feature UX** : page frontend de gestion des flux (liste de fichiers, tableau de bord stats, bouton de re-ingestion) — s'appuie sur le scaffolding API de SF4.
