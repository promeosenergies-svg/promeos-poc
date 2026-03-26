# SF4 — Enedis SGE Operational Ingestion Pipeline

> **Status**: Spec v4 — decisions validated, implementation plan ready
> **Plan d'implémentation** : `docs/specs/plan-enedis-sge-4-implementation.md`
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion) — all complete on `feat/enedis-sge-ingestion`
> **Out of scope**: Promotion staging → production (SF5). Pas de matching PRM→Site, pas d'écriture dans les tables fonctionnelles (`Consommation`, `MeterReading`), pas de déduplication des republications.

## Décisions d'architecture

| Question | Décision | Justification |
|----------|----------|---------------|
| Historique d'erreurs | **Table séparée** `enedis_flux_file_error` (FK vers `enedis_flux_file`) | Propre, extensible, requêtable en SQL directement. Plus robuste qu'une colonne JSON |
| CLI scope | **Minimaliste** — sous-commande `ingest` uniquement (+ `--dry-run`) | Les stats restent côté API, évite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ultérieurement via `get_optional_auth` |
| Schémas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase — les schémas spécifiques à un domaine sont co-localisés avec le router |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) mis à jour | Cohérence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Cohérent avec les autres tests d'API (`test_bacs_api.py`, etc.) — les tests HTTP vivent dans le répertoire de tests principal |

---

## Contexte

SF1-SF3 ont livré un pipeline d'ingestion complet : déchiffrement, parsing et stockage de fichiers flux Enedis réels (R4H, R4M, R4Q, R171, R50, R151) dans 5 tables staging. 221 tests passent, 91 fichiers réels ingérés avec 0 erreur, 123 846 mesures au total.

Deux scripts ad-hoc existent dans `backend/data_ingestion/enedis/scripts/` pour lancer l'ingestion manuellement.

**Problème :** Le pipeline n'a pas de point d'entrée opérationnel, pas de surface d'observabilité, et un bug qui détruit l'historique d'erreurs au retry. SF4 rend le pipeline staging brut **fiable, complet et auditable**.

## Scope SF4

SF4 livre 5 choses :

1. **CLI** — commande propre avec arguments, remplaçant les scripts ad-hoc
2. **API REST** — déclencher l'ingestion + consulter l'état et les stats (scaffolding pour future UX)
3. **Configuration** — variable d'environnement pour le répertoire de flux, plus de chemins hardcodés
4. **Correction de l'audit d'erreurs** — préserver l'historique des erreurs au retry au lieu de supprimer les enregistrements
5. **Wiring** — nouveau router enregistré dans l'application

**Hors scope :** intégration JobOutbox, frontend/UI, alerting/notifications, promotion vers tables de production (SF5).

---

## 1. CLI

### Objectif

Remplacer les scripts ad-hoc par une commande CLI propre avec arguments. Suit le pattern existant des autres commandes CLI du projet (`services.demo_seed`, `jobs.run`).

### Commandes

**Ingestion :**

```
python -m data_ingestion.enedis.cli ingest [OPTIONS]
```

| Option | Défaut | Description |
|--------|--------|-------------|
| `--dir PATH` | Variable d'env ou défaut projet | Répertoire source des fichiers .zip chiffrés |
| `--recursive` | Activé | Scanner les sous-répertoires |
| `--dry-run` | Désactivé | Scanner et classifier sans ingérer (rapport uniquement) |
| `--verbose` | Désactivé | Logging niveau DEBUG |

### Sorties attendues

**Mode normal** — rapport structuré résumant :
- Source, nombre de fichiers scannés
- Répartition par statut (parsed, skipped, error, needs_review)
- Détail des skips par type de flux (R172, X14, HDM)
- Volume de mesures par table staging (R4x, R171, R50, R151)
- Liste des erreurs éventuelles (filename + message)

**Mode dry-run** — rapport de ce qui *serait* fait :
- Nombre de fichiers nouveaux par type de flux
- Nombre de fichiers déjà traités
- Aucune modification en base

---

## 2. API REST

### Objectif

Exposer le déclenchement d'ingestion et la consultation d'état via REST. Doit fournir un scaffolding suffisant pour construire ultérieurement une feature UX complète de gestion des flux.

### Router

`/api/enedis` — cohérent avec le naming domaine-par-domaine du codebase.

### 2.1 Déclencher une ingestion

`POST /api/enedis/ingest`

- Paramètres optionnels : répertoire source (override), mode récursif, mode dry-run
- Exécution synchrone (suffisant pour le volume POC ~100 fichiers, <10 secondes)
- Réponse : compteurs par statut, liste des erreurs, durée d'exécution
- Le mode dry-run retourne les mêmes compteurs sans effectuer de modification

### 2.2 Lister les fichiers flux

`GET /api/enedis/flux-files`

- Filtrage par statut et par type de flux
- Pagination (offset-based, cohérent avec les autres endpoints PROMEOS)
- Chaque item expose : filename, hash, type, statut, nombre de mesures, version, lien de supersession, message d'erreur, timestamps
- Extensible ultérieurement avec tri et recherche par nom sans casser le schéma

### 2.3 Statistiques d'ingestion

`GET /api/enedis/stats`

Retourne en un seul appel :
- **Fichiers** : total, répartition par statut, répartition par type de flux
- **Mesures** : total, répartition par table staging (r4x, r171, r50, r151)
- **PRMs** : nombre distinct et liste des identifiants PRM présents dans le staging (scaffolding pour le matching PRM→DeliveryPoint en SF5)
- **Dernière ingestion** : timestamp et nombre de fichiers traités

### 2.4 Détail d'un fichier flux

`GET /api/enedis/flux-files/{id}`

- Toutes les informations de la liste + header XML brut (JSON) + historique d'erreurs complet
- 404 si non trouvé

---

## 3. Configuration

### Variable d'environnement

`ENEDIS_FLUX_DIR` — chemin absolu vers le répertoire contenant les fichiers flux chiffrés.

- Ajouté dans `.env` et `.env.example`
- Valeur par défaut : `flux_enedis/` au niveau racine du projet Promeos
- Utilisé par le CLI et l'API comme répertoire par défaut
- Le paramètre API `directory` permet de l'overrider ponctuellement

---

## 4. Correction de l'audit d'erreurs

### Problème

Actuellement, quand un fichier en statut ERROR est re-traité, le pipeline **supprime** l'enregistrement existant et en crée un nouveau. Cela perd :
- La date de la première erreur
- Le message d'erreur original
- Le nombre de tentatives échouées

Ce comportement est non-auditable et empêche toute analyse statistique des erreurs d'ingestion.

### Comportement cible

- Au retry, l'erreur courante est **archivée** dans un historique (pas supprimée)
- Le fichier est re-traité **in-place** (même enregistrement, même ID) au lieu d'être supprimé/recréé
- L'historique complet des erreurs est consultable via l'API (endpoint détail 2.4)
- Le nombre de tentatives est dérivable de l'historique

---

## 5. Wiring applicatif

Le nouveau router Enedis est intégré dans l'application via le même pattern que tous les autres routers : déclaration dans `routes/`, enregistrement dans `main.py`.

---

## Inventaire des assets

| Asset | Path | Statut |
|-------|------|--------|
| Pipeline | `backend/data_ingestion/enedis/pipeline.py` | SF3 done |
| Models | `backend/data_ingestion/enedis/models.py` | SF3 done, à enrichir (error_history) |
| Parsers | `backend/data_ingestion/enedis/parsers/` | SF3 done |
| Decrypt | `backend/data_ingestion/enedis/decrypt.py` | SF1 done |
| Enums | `backend/data_ingestion/enedis/enums.py` | SF3 done |
| Scripts ad-hoc | `backend/data_ingestion/enedis/scripts/` | Supersédés par le CLI |
| Tests (221) | `backend/data_ingestion/enedis/tests/` | SF3 done |
| Fichiers flux réels | `flux_enedis/` (hors repo, 91 in-scope) | — |
| **Nouveau : CLI** | `backend/data_ingestion/enedis/cli.py` | **SF4** |
| **Nouveau : Config** | `backend/data_ingestion/enedis/config.py` | **SF4** |
| **Nouveau : Router** | `backend/routes/enedis.py` | **SF4** |

## Ce qui vient après SF4

- **SF5 — Promotion staging → production** : matching PRM→DeliveryPoint, normalisation des données (string→float/datetime), résolution des republications, écriture dans les tables fonctionnelles.
- **Feature UX** : page frontend de gestion des flux (liste de fichiers, tableau de bord stats, bouton de re-ingestion) — s'appuie sur le scaffolding API de SF4.
